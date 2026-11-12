"""HTTP integration for the local index; read-only connectors, explicit opening."""
import json, subprocess, threading, urllib.parse, time
from pathlib import Path
from . import indexdb

JOB={'running':False,'message':'尚未刷新','error':'','started':''}
LOCK=threading.Lock()
CANCEL=threading.Event()

def start_job(sid=None,deep=False,reconcile=False):
    with LOCK:
        if JOB['running']: return dict(JOB)
        CANCEL.clear()
        JOB.update(running=True,message='正在准备',error='',started=indexdb.stamp())
    def work():
        try:
            if sid:
                with indexdb.connect() as c: indexdb.enrich(c,indexdb.config(),sid,force=True)
            else:
                def report(msg):
                    if CANCEL.is_set(): raise RuntimeError('已停止；已完成部分保留，再次刷新可续接')
                    JOB.update(message=msg)
                result=indexdb.refresh(report,deep=deep,reconcile=reconcile)
                if not result.get('ok'): raise RuntimeError(result.get('error','刷新失败'))
                write_today()
            JOB.update(message='刷新完成；覆盖范围见来源状态')
        except Exception as e: JOB.update(error=str(e) if isinstance(e,(RuntimeError,ValueError)) else type(e).__name__,message='刷新未完成；保留上次索引')
        finally: JOB['running']=False
    threading.Thread(target=work,daemon=True).start()
    return dict(JOB)

def cover_candidate(artifact):
    """Conservative metadata rules, not a visual classifier. Never changes the index."""
    import re
    target = urllib.parse.unquote(artifact.get("target", "")).lower()
    # Bundled synthetic examples remain usable even when a ZIP is unpacked under /tmp.
    try:
        from .paths import ROOT
        sample = Path(target).resolve().relative_to((ROOT/'samples').resolve())
        target = '/samples/' + str(sample)
    except ValueError: pass
    title = artifact.get("title", "").lower()
    name = urllib.parse.urlsplit(target).path.rsplit("/", 1)[-1]
    text = title + " " + name
    blocked = (
        r"二维码|预览码|登录|截图|截屏|屏幕快照|验收|调试|过程图|参考图|草稿|缩略图|拼版预览|界面",
        r"screenshot|screen.?shot|screen.?capture|qrcode|qr.?code",
        r"(?:^|[^a-z0-9])(?:qr|login|screen|debug|draft|preview|thumbnail|thumb|capture)(?:[^a-z0-9]|$)",
    )
    if any(re.search(pattern, text) for pattern in blocked):
        return False
    if re.search(r"/(?:tmp|temp|screenshots?|research|sources|references?|inputs?)/", target):
        return False
    # A publish folder alone can contain arbitrary screenshots: require a named deliverable.
    return bool(re.search(r"成品|终稿|最终版|封面|海报|壁纸|头像|表情包", text)
                or re.search(r"(?:^|[^a-z0-9])(?:cover|final|poster|wallpaper|avatar)(?:[^a-z0-9]|$)", text)
                or "/图片产物/" in target
                or "正式交付" in (artifact.get("evidence") or ""))


def cover_snapshot(c):
    for row in c.execute("SELECT * FROM artifacts WHERE kind='image' ORDER BY updated DESC,id ASC"):
        artifact = dict(row)
        if cover_candidate(artifact):
            return {"item": artifact, "rule": "finished-image-v1"}
    return {"item": None, "rule": "finished-image-v1"}


def today_snapshot():
    from datetime import datetime,timezone,timedelta
    tz=timezone(timedelta(hours=8)); now=datetime.now(tz); day=now.strftime('%Y-%m-%d')
    start=now.replace(hour=0,minute=0,second=0,microsecond=0).astimezone(timezone.utc).isoformat().replace('+00:00','Z')
    end=(now.replace(hour=0,minute=0,second=0,microsecond=0)+timedelta(days=1)).astimezone(timezone.utc).isoformat().replace('+00:00','Z')
    items=[]; counts={k:0 for k in ('codex','claude','mirasim','cohub','workbuddy')}
    with indexdb.connect() as c:
        rows=c.execute("""SELECT s.*,(SELECT group_concat(source) FROM origins o WHERE o.session_id=s.id) AS sources
          FROM sessions s WHERE (s.updated>=? AND s.updated<?)
          OR EXISTS(SELECT 1 FROM messages m WHERE m.session_id=s.id AND m.ts>=? AND m.ts<?)
          ORDER BY s.updated DESC""",(start,end,start,end)).fetchall()
        for r in rows:
            sources=(r['sources'] or r['engine']).split(',')
            for source in sources:
                if source in counts: counts[source]+=1
            try: last=datetime.fromisoformat(r['updated'].replace('Z','+00:00')).astimezone(tz).strftime('%H:%M')
            except ValueError: last=''
            items.append({'id':r['id'],'source':r['engine'],'sources':sources,'space':r['workspace'],'session':r['title'],
                          'ask':r['summary'][:120],'asks':0,'first':'','last':last,'coverage':r['coverage'],
                          'status':'indexed','url':'/library.html?session='+urllib.parse.quote(r['id'])})
        source_status=[dict(r) for r in c.execute('SELECT * FROM sources')]
    return {'date':day,'generatedAt':indexdb.stamp(),'items':items,'counts':counts,'sources':source_status,
            'stats':{'running':0,'replied':0,'error':0,'cancelled':0,'spaces':len(set(x['space'] for x in items)),'auto':0}}

def write_today():
    from .paths import GEN,write_json
    from . import build
    write_json(GEN/'today.json',today_snapshot())
    build.build()

def opened(c,payload):
    kind=payload.get('kind'); key=payload.get('id','')
    if key.startswith('demo:') and kind=='session':
        return {'ok':True, 'url':'/library.html?session='+urllib.parse.quote(key), 'demo':True}
    if kind=='artifact':
        row=c.execute('SELECT target FROM artifacts WHERE id=?',(key,)).fetchone()
        if not row: raise ValueError('产物未登记')
        target=row[0]
    elif kind=='session':
        row=c.execute('SELECT * FROM sessions WHERE id=?',(key,)).fetchone()
        if not row: raise ValueError('会话未登记')
        host=c.execute("SELECT native_id FROM origins WHERE session_id=? AND source='mirasim'",(key,)).fetchone()
        if payload.get('source')=='mirasim' or (not payload.get('source') and host):
            o=c.execute("SELECT native_id FROM origins WHERE session_id=? AND source='mirasim'",(key,)).fetchone()
            if not o: raise ValueError('没有 Mirasim 入口')
            from .sessionopen import open_mirasim
            return open_mirasim(o[0])
        if row['engine']=='claude':
            from .sessionopen import open_claude
            return open_claude(c,row)
        target=row['uri']
        if not target: raise ValueError('此来源没有已验证深链；请在详情阅读，或复制恢复命令')
    elif kind=='app' and payload.get('source')=='workbuddy':
        row=c.execute("SELECT id FROM sessions WHERE id=? AND engine='workbuddy'",(key,)).fetchone()
        if not row: raise ValueError('WorkBuddy 会话未登记')
        target='workbuddy://home'
    elif kind=='folder':
        row=c.execute('SELECT workspace FROM sessions WHERE id=?',(key,)).fetchone()
        target=row[0] if row else ''
        if not Path(target).is_absolute() or not Path(target).is_dir(): raise ValueError('本机项目目录不存在')
    else: raise ValueError('不支持的打开动作')
    parsed=urllib.parse.urlparse(target)
    if parsed.scheme=='cohub-app':
        target='https://cohub.live/spaces/'+parsed.netloc
    if parsed.scheme=='cohub-file':
        remote=urllib.parse.unquote(parsed.path).lstrip('/')
        if '..' in Path(remote).parts or not parsed.netloc:
            raise ValueError('云端文件路径无效')
        cache=indexdb.BASE/'data'/'remote-cache'/key
        cache.mkdir(parents=True,exist_ok=True)
        dest=cache/Path(remote).name
        import tempfile
        temp=None
        try:
            with tempfile.NamedTemporaryFile(dir=cache,delete=False) as f:
                temp=Path(f.name)
                proc=subprocess.run([indexdb.config()['cohubCommand'],'-s',parsed.netloc,'spaces','files','cat',remote],
                                    stdout=f,stderr=subprocess.PIPE,timeout=120)
            if proc.returncode: raise RuntimeError('云端文件读取失败；可能已移动或当前账号无权访问')
            temp.replace(dest)
        finally:
            if temp and temp.exists(): temp.unlink()
        target=str(dest)
    scheme=urllib.parse.urlparse(target).scheme
    if scheme not in ('','http','https','codex') and not (kind=='app' and target=='workbuddy://home'): raise ValueError('不支持的链接类型')
    if not scheme and not Path(target).exists(): raise ValueError('原文件已移动或删除')
    cmd=['open',target]
    omia=Path.home()/'.codex/skills/open-in-omia/scripts/open_in_omia.sh'
    if not scheme and Path(target).suffix.lower() in ('.command','.sh','.py','.js','.mjs','.app','.exe','.dmg','.pkg','.workflow','.scpt','.applescript'):
        cmd=['open','-R',target]
    elif not scheme and Path(target).is_file() and omia.exists(): cmd=[str(omia),target]
    p=subprocess.run(cmd,capture_output=True,timeout=15)
    if p.returncode: raise RuntimeError('系统未能打开此入口')
    return {'ok':True}

def handle(handler,method,path,q,send):
    if not path.startswith('/api/index/'): return False
    one=lambda k,default='': q.get(k,[default])[0]
    try:
        with indexdb.connect() as c:
            if method=='GET':
                if path.endswith('/work-view') or path.endswith('/work-cover'):
                    from . import works
                    works.redirect(handler,c,one('id'),cover=path.endswith('/work-cover'))
                    return True
                if path.endswith('/image'):
                    from . import imagepreview
                    imagepreview.serve(handler,c,one('id'))
                    return True
                if path.endswith('/status'):
                    data={**indexdb.stats(c),'job':dict(JOB),'demo':indexdb.config().get('demo',True)}
                    external=indexdb.checkpoint(c,'backfill:progress')
                    if external: data['backfill']=json.loads(external)
                    data['blocked_sessions']=[dict(r) for r in c.execute("SELECT id,title,uri,coverage FROM sessions WHERE engine='cohub' AND coverage LIKE '%文件目录无权访问%'")]
                    if not JOB['started'] and data['sessions']:
                        data['job']['message']='索引已就绪 · 点击刷新可读取新增记录'
                elif path.endswith('/sessions') or path.endswith('/artifacts'):
                    data=indexdb.query(c,path.split('/')[-1],one('q'),one('source'),one('offset',0),one('limit',50),one('from'),one('to'),one('images')=='1')
                elif path.endswith('/detail'): data=indexdb.detail(c,one('id'),one('offset',0),one('limit',100))
                elif path.endswith('/today'): data=today_snapshot()
                elif path.endswith('/cover'): data=cover_snapshot(c)
                elif path.endswith('/works'):
                    from . import works
                    data=works.catalog(c)
                else: raise ValueError('没有此接口')
            else:
                n=int(handler.headers.get('Content-Length','0'))
                if n>16384: raise ValueError('请求过大')
                body=json.loads(handler.rfile.read(n) or '{}')
                if path.endswith('/refresh'): data=start_job(deep=bool(body.get('deep')),reconcile=bool(body.get('reconcile')))
                elif path.endswith('/cancel'):
                    CANCEL.set(); JOB.update(message='将在当前读取结束后停止'); data={'ok':True}
                elif path.endswith('/enrich'): data=start_job(body.get('id'))
                elif path.endswith('/demo-message'):
                    from .demo import new_message
                    data=new_message(body.get('id'))
                elif path.endswith('/open'): data=opened(c,body)
                elif path.endswith('/works'):
                    from . import works
                    data=works.update(c,body)
                else: raise ValueError('没有此接口')
        send(handler,200,data)
    except Exception as e:
        send(handler,400,{'ok':False,'error':str(e) if isinstance(e,(ValueError,RuntimeError)) else type(e).__name__})
    return True
