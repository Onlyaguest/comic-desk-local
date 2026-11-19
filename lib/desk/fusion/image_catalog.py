"""图片目录与有界取图：目录不联网，缩略图不拉云图，失败显式保留。"""
import hashlib,io,json,mimetypes,os,re,sqlite3,subprocess,threading,time,urllib.parse,urllib.request
from pathlib import Path
from contextlib import closing
from desk import indexdb as db,imagepreview
try:
    from PIL import Image,ImageOps
except ImportError:Image=None

from desk.paths import DATA
HERE=DATA/'fusion'
ROOT=HERE/'images'
PREFS=HERE/'image-prefs.json'
FAILURES={};LOCKS={};GUARD=threading.Lock();NETWORK=threading.BoundedSemaphore(2)
STATS={'remoteReads':0,'cloudCliCalls':0,'modelCalls':0,'bytesFetched':0,'thumbnailBuilds':0,'cacheHits':0}
MAX=imagepreview.MAX_BYTES

def connection():
    c=sqlite3.connect(db.DB.resolve().as_uri()+'?mode=ro',uri=True);c.row_factory=sqlite3.Row;return c

def revision(row):return hashlib.sha256((row['target']+'|'+(row['updated'] or '')).encode()).hexdigest()[:20]

def own(row):return ROOT/row['id']/revision(row)/'original'

def source(row):
    dest=own(row)
    if dest.is_file():return dest,'cached'
    u=urllib.parse.urlparse(row['target'])
    if u.scheme in ('','file'):
        p=Path(urllib.parse.unquote(u.path))
        return (p,'local') if p.is_file() else (None,'missing')
    # 复用原版已成功的同版本缓存，不复制、不修改它。
    folder=db.BASE/'data/image-cache'/row['id']/revision(row)
    if folder.is_dir():
        for p in folder.iterdir():
            if p.is_file() and p.name.startswith(('image.','preview.')) and not p.name.endswith('.tmp'):return p,'cached'
    return None,'remote'

def records():
    with closing(connection()) as c:return [dict(r) for r in c.execute("SELECT * FROM artifacts WHERE kind='image' ORDER BY updated DESC,id")]

def inspect(row):
    p,kind=source(row);failure=FAILURES.get(row['id'])
    status='ready' if p else kind
    if failure and failure['revision']==revision(row) and time.time()-failure['at']<300:status='failed'
    return {'id':row['id'],'title':urllib.parse.unquote(row['title']),'source':row['source'],'updated':row['updated'],
        'status':status,'storage':kind,'reason':failure['reason'] if status=='failed' else '本地原图已移动或删除' if kind=='missing' else '需点选后读取远端' if kind=='remote' else '',
        'name':Path(urllib.parse.unquote(urllib.parse.urlparse(row['target']).path)).name,
        'thumb':'/api/desk/image?id='+urllib.parse.quote(row['id'])+'&mode=thumb',
        'original':'/api/desk/image?id='+urllib.parse.quote(row['id'])+'&mode=full'}

def catalog(q='',src='',status='',offset=0,limit=24):
    started=time.monotonic();items=[inspect(r) for r in records()];counts={k:sum(x['status']==k for x in items) for k in ('ready','remote','missing','failed')}
    needle=q.lower().strip();filtered=[x for x in items if (not src or x['source']==src) and (not status or x['status']==status) and (not needle or needle in (x['title']+' '+x['name']).lower())]
    offset=max(0,int(offset));limit=max(1,min(48,int(limit)))
    return {'ok':True,'items':filtered[offset:offset+limit],'total':len(filtered),'registered':len(items),'counts':counts,'offset':offset,'limit':limit,'hasMore':offset+limit<len(filtered),
        'metrics':{**STATS,'thisCatalogRemoteReads':0,'elapsedMs':round((time.monotonic()-started)*1000,1)},'coverage':'已有索引中登记的图片；不代表全电脑或全云端图片'}

def row_for(key):
    with closing(connection()) as c:r=c.execute("SELECT * FROM artifacts WHERE id=? AND kind='image'",(key,)).fetchone()
    if not r:raise ValueError('图片未登记')
    return dict(r)

def lock_for(key):
    with GUARD:return LOCKS.setdefault(key,threading.Lock())

def resolve(key,mode='thumb'):
    row=row_for(key)
    with lock_for(key):
        p,kind=source(row)
        if not p:raise ValueError('本地原图已失效' if kind=='missing' else '云端图片尚未读取，请点「读取这张云图」')
        if p.stat().st_size>MAX:raise ValueError('图片超过 60 MB，需在原位置打开')
        data=p.read_bytes();typ=imagepreview.mime(data)
        if not typ and re.search(br'<svg(?:\s|>)',data[:4096]):typ='image/svg+xml'
        if mode=='full' and typ:return data,typ
        # 本地文件修改后，缩略图版本随 mtime 和 size 变化。
        fp=hashlib.sha256((str(p)+'|'+str(p.stat().st_mtime_ns)+'|'+str(p.stat().st_size)).encode()).hexdigest()[:16]
        thumb=ROOT/row['id']/revision(row)/('thumb-'+fp+'.webp')
        if thumb.is_file():STATS['cacheHits']+=1;return thumb.read_bytes(),'image/webp'
        if typ=='image/svg+xml':return data,typ
        if Image:
            try:
                with Image.open(io.BytesIO(data)) as im:
                    im.draft('RGB',(960,960));im=ImageOps.exif_transpose(im);im.thumbnail((480,480));im=im.convert('RGBA' if 'A' in im.getbands() else 'RGB');buf=io.BytesIO();im.save(buf,format='WEBP',quality=80);content=buf.getvalue()
                thumb.parent.mkdir(parents=True,exist_ok=True);tmp=thumb.with_suffix('.tmp');tmp.write_bytes(content);tmp.replace(thumb);STATS['thumbnailBuilds']+=1
                return content,'image/webp'
            except Exception:
                raise ValueError('图片预览解码失败；可打开原件或单张重试')
        if typ:return data,typ
        raise ValueError('原件不是可识别的图片；可能是失效链接或不支持的格式')

def fetch(key,retry=False):
    row=row_for(key)
    with lock_for(key):
      p,kind=source(row)
      if p and not (retry and key in FAILURES and kind=='cached'):return {'ok':True,'item':inspect(row),'reused':True,'remoteReads':0}
      if kind=='missing':return {'ok':False,'error':'本地原图已移动或删除，重试不能恢复它','remoteReads':0}
      if db.config().get('demo',True):return {'ok':False,'error':'离线样例模式不读取远端图片','remoteReads':0}
      failure=FAILURES.get(key)
      if failure and time.time()-failure['at']<300 and not retry:return {'ok':False,'error':failure['reason'],'remoteReads':0,'cooldown':True}
      dest=own(row);dest.parent.mkdir(parents=True,exist_ok=True);temp=dest.with_suffix('.tmp');u=urllib.parse.urlparse(row['target']);reads=0
      try:
        with NETWORK:
            STATS['remoteReads']+=1;reads=1
            if u.scheme in ('http','https'):
                req=urllib.request.Request(imagepreview.public_url(row['target']),headers={'User-Agent':'LocalDesk-ImagePreview/2.1'})
                with urllib.request.build_opener(imagepreview.PublicRedirect).open(req,timeout=20) as response, temp.open('wb') as f:
                    size=0
                    while True:
                        block=response.read(128*1024)
                        if not block:break
                        size+=len(block)
                        if size>MAX:raise ValueError('图片超过 60 MB')
                        f.write(block)
            elif u.scheme=='cohub-file':
                remote=urllib.parse.unquote(u.path).lstrip('/')
                if '..' in Path(remote).parts or not u.netloc:raise ValueError('云端图片路径无效')
                STATS['cloudCliCalls']+=1
                with temp.open('wb') as f:
                    p=subprocess.run([db.config()['cohubCommand'],'-s',u.netloc,'spaces','files','cat',remote],stdout=f,stderr=subprocess.PIPE,timeout=35,env={**os.environ,'COHUB_CLI_AUTO_UPDATE':'0'})
                if p.returncode:raise RuntimeError('云端文件读取失败：可能已删除、无权限或当前账号不可读')
            else:raise ValueError('不支持的图片来源')
            if not temp.is_file() or temp.stat().st_size>MAX:raise ValueError('图片大小无效或超过 60 MB')
            head=temp.read_bytes();typ=imagepreview.mime(head)
            if not typ and not re.search(br'<svg(?:\s|>)',head[:4096]):raise ValueError('远端返回的不是图片；未作为图片缓存')
            STATS['bytesFetched']+=len(head);temp.replace(dest);FAILURES.pop(key,None)
        return {'ok':True,'item':inspect(row),'remoteReads':reads}
      except Exception as e:
        if isinstance(e,urllib.error.HTTPError):reason='远端返回 HTTP '+str(e.code)
        elif isinstance(e,(RuntimeError,ValueError)):reason=str(e)[:150]
        elif isinstance(e,subprocess.TimeoutExpired):reason='取图超时，本次没有自动重试'
        else:reason='远端图片暂不可读：'+type(e).__name__
        FAILURES[key]={'reason':reason,'at':time.time(),'revision':revision(row)}
        return {'ok':False,'error':reason,'remoteReads':reads}
      finally:
        if temp.exists():temp.unlink()

def serve(handler,key,mode='thumb'):
    data,typ=resolve(key,mode)
    handler.send_response(200);handler.send_header('Content-Type',typ);handler.send_header('Content-Length',str(len(data)));handler.send_header('Cache-Control','private, max-age=300');handler.send_header('X-Content-Type-Options','nosniff');handler.send_header('Content-Security-Policy',"default-src 'none'; style-src 'unsafe-inline'; sandbox");handler.end_headers();handler.wfile.write(data)

def cover():
    rows=records()
    try:chosen=json.loads(PREFS.read_text()).get('cover')
    except (OSError,ValueError):chosen=None
    from desk.indexapi import cover_candidate
    candidates=sorted((r for r in rows if source(r)[0] and (r['id']==chosen or cover_candidate(r))),key=lambda r:r['id']!=chosen)[:8]
    for row in candidates:
        try:
            resolve(row['id'],'thumb')
            return {'item':row,'rule':'readable-user-picked' if row['id']==chosen else 'readable-finished-image'}
        except (OSError,ValueError):continue
    return {'item':None,'rule':'no-readable-cover'}

def set_cover(key):
    row=row_for(key)
    if not source(row)[0]:raise ValueError('请先读取这张图片，再设为封面')
    resolve(key,'thumb')
    PREFS.parent.mkdir(parents=True,exist_ok=True);PREFS.write_text(json.dumps({'cover':key}));return {'ok':True}
