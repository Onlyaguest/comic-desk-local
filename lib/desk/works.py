"""Rule-based works catalog. Original artifacts stay intact; curation is local JSON."""
import hashlib, html, json, re, threading, urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from .paths import DATA

CLOUD = DATA / 'works-cloud.json'
STATE = DATA / 'works-state.json'
META = DATA / 'works-metadata.json'
LOCK = threading.RLock()
PREVIEWS = {}


def read(path):
    try: return json.loads(path.read_text())
    except FileNotFoundError: return {}


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2))
    tmp.replace(path)


def ingest_apps(apps):
    with LOCK:
        catalog = read(CLOUD)
        for app in apps:
            catalog[app['id']] = {k: app.get(k) for k in ('id','spaceId','slug','status','updatedAt','publicUrl','publishedUrl','url','meta','latestVersion')}
        save(CLOUD, catalog)


def category(title):
    if re.search(r'报告|分析|总结|清单|日报|周报|report', title, re.I): return '报告'
    if re.search(r'演示|课件|幻灯|slides|deck|presentation', title, re.I): return '演示'
    if re.search(r'工具|生成器|工作台|管理|计算|查询|tool|desk|studio|app', title, re.I): return '工具'
    return '其他'


def local_path(target):
    if target.startswith('file://'): target = urllib.parse.unquote(urllib.parse.urlsplit(target).path)
    if not target.startswith('/'): return None
    # References can include HTML fragments; real filenames are checked first.
    p = Path(target).expanduser()
    if not p.exists(): p = Path(target.split('#')[0].split('?')[0])
    return p.resolve() if p.suffix.lower() in ('.html','.htm') else None


def local_meta(path, cache):
    key = str(path)
    if not path.is_file(): return {'title': path.stem, 'missing': True, 'updated': ''}
    stat = path.stat(); fp = [stat.st_mtime_ns, stat.st_size]
    if cache.get(key, {}).get('fp') == fp: return cache[key]
    try:
        with path.open(encoding='utf-8', errors='replace') as stream:
            head = stream.read(65536)
        match = re.search(r'<title\b[^>]*>(.*?)</title>', head, re.I | re.S)
        title = html.unescape(re.sub(r'<[^>]+>', '', match[1])).strip() if match else path.stem
        cover = None
        for name in ('cover.jpg','cover.png','poster.jpg','poster.png'):
            if (path.parent / name).is_file(): cover = name; break
        result = {'fp': fp, 'title': title[:180] or path.stem, 'cover': cover,
                  'updated': datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat()}
    except OSError:
        result = {'fp': fp, 'title': path.stem, 'missing': True, 'updated': ''}
    cache[key] = result
    return result


def catalog(c):
    with LOCK:
        state, cache = read(STATE), read(META)
        old_cache = dict(cache)
        groups = {}
        for app in read(CLOUD).values():
            meta = app.get('meta') or {}
            target = app.get('publishedUrl') or app.get('publicUrl') or app.get('url') or ''
            published = app.get('status') == 'published' and target.startswith(('https://','http://'))
            key = 'cohub:' + app['id']; title = meta.get('title') or app.get('slug') or '未命名应用'
            cover = meta.get('image') or (meta.get('extracted') or {}).get('image')
            if not isinstance(cover,str) or not cover.startswith(('https://','http://')): cover = None
            groups[key] = {'id':key,'title':title,'source':'cohub','updated':app.get('updatedAt') or '',
                           'category':category(title),'cover':cover,'pending':not published,
                           'reason':'' if published else '未发布或缺少可用发布地址',
                           'project_url':'https://cohub.live/spaces/'+app['spaceId'],
                           'versions':[{'id':key,'title':title,'target':target if published else '',
                                        'updated':app.get('updatedAt') or '', 'version':app.get('latestVersion')}], 'sessions':[]}
        from . import indexdb
        if indexdb.config().get('demo', True) and indexdb.checkpoint(c, 'demo:seed:v1'):
            from .paths import ROOT
            key='cohub:demo-app'
            target=preview_url(ROOT/'samples/timer.html')
            groups[key]={'id':key,'title':'样例 · Cohub 专注应用（离线模拟）','source':'cohub',
                'updated':'','category':'工具','cover':None,'pending':False,'reason':'','project_url':'',
                'versions':[{'id':key,'title':'离线模拟应用','target':target,'updated':'','version':1}],'sessions':[]}
        # Only registered HTML references; no full-disk walk.
        for row in c.execute("SELECT * FROM artifacts WHERE lower(target) LIKE '%.htm%' ORDER BY updated DESC"):
            a = dict(row); p = local_path(a['target'])
            if not p: continue
            if any(part.lower() in ('node_modules','.git','.venv','vendor','__pycache__') for part in p.parts): continue
            m = local_meta(p, cache)
            stem = re.sub(r'[-_. ]v\d+(?:\.\d+)*$', '', p.stem, flags=re.I)
            group_id = 'local:' + hashlib.sha256(str(p.parent / stem).encode()).hexdigest()[:24]
            from .paths import ROOT
            rule_path = str(p.relative_to(ROOT/'samples')) if p.is_relative_to(ROOT/'samples') else str(p)
            pending = bool(m.get('missing') or re.search(r'(?:^|[/_.-])(test|tmp|temp|debug|preview|fixture|smoke)(?:[/_.-]|$)|验收|草稿|截图', rule_path, re.I))
            reason = '文件不存在或不可读' if m.get('missing') else ('可能是测试、草稿或临时页面' if pending else '')
            g = groups.setdefault(group_id, {'id':group_id,'title':m['title'],'source':'local','updated':'',
                'category':category(m['title']),'cover':None,'pending':pending,'reason':reason,'versions':[], 'sessions':[]})
            if any(v['target']==str(p) for v in g['versions']): continue
            v = {'id':a['id'],'title':m['title'],'target':str(p),'updated':m.get('updated') or a['updated'] or '',
                 'missing':bool(m.get('missing')),'cover_file':m.get('cover')}
            g['versions'].append(v)
            g['sessions'].extend(dict(r) for r in c.execute('SELECT s.id,s.title FROM sessions s JOIN relations r ON r.session_id=s.id WHERE r.artifact_id=?',(a['id'],)))
        result = []
        for key,g in groups.items():
            prefs = state.get(key,{})
            g['versions'].sort(key=lambda v:(v['updated'],v['id']),reverse=True)
            active = next((v for v in g['versions'] if v['id']==prefs.get('preferred')),g['versions'][0])
            g.update(title=prefs.get('title') or active['title'],category=prefs.get('category') or category(active['title']),
                     updated=max(v['updated'] for v in g['versions']),pinned=bool(prefs.get('pinned')),hidden=bool(prefs.get('hidden')),
                     preferred=active['id'],pin_order=prefs.get('pin_order',''))
            if active.get('missing'): g.update(pending=True,reason='文件不存在或不可读')
            if prefs.get('approved') and not active.get('missing'): g.update(pending=False,reason='')
            if g['source']=='local':
                g['href'] = '/api/index/work-view?id='+urllib.parse.quote(key) if not active.get('missing') else ''
                g['cover'] = '/api/index/work-cover?id='+urllib.parse.quote(key) if active.get('cover_file') else None
            else: g['href'] = active['target']
            g['sessions'] = list({s['id']:s for s in g['sessions']}.values())
            result.append(g)
        if cache != old_cache: save(META, cache)
        result.sort(key=lambda g:(g['updated'],g['id']),reverse=True)
        return {'items':result,'counts':{'cohub':sum(g['source']=='cohub' for g in result),'local':sum(g['source']=='local' for g in result)}}


def update(c, payload):
    key = payload.get('id'); rows = catalog(c)['items']
    item = next((x for x in rows if x['id']==key),None)
    if not item: raise ValueError('作品不存在')
    changes = {}
    for field in ('pinned','hidden','approved'):
        if field in payload: changes[field] = bool(payload[field])
    if 'title' in payload: changes['title'] = str(payload['title']).strip()[:180]
    if 'category' in payload:
        if payload['category'] not in ('工具','报告','演示','其他'): raise ValueError('未知分类')
        changes['category'] = payload['category']
    if 'preferred' in payload:
        if payload['preferred'] not in [v['id'] for v in item['versions']]: raise ValueError('版本不属于此作品')
        changes['preferred'] = payload['preferred']
    with LOCK:
        state = read(STATE)
        if changes.get('pinned') and not state.get(key,{}).get('pinned'):
            changes['pin_order'] = datetime.now(timezone.utc).isoformat()
        state[key] = {**state.get(key,{}),**changes}; save(STATE,state)
    return {'ok':True}


def entry(c, key):
    item = next((x for x in catalog(c)['items'] if x['id']==key),None)
    if not item: raise ValueError('作品不存在')
    return item, next(v for v in item['versions'] if v['id']==item['preferred'])


def preview_url(path):
    """Separate loopback origin for each root, no directory listing or symlink escape."""
    root = path.parent.resolve()
    with LOCK:
        if str(root) not in PREVIEWS:
            class Handler(SimpleHTTPRequestHandler):
                def __init__(self,*a,**kw): super().__init__(*a,directory=str(root),**kw)
                def log_message(self,*a): pass
                def list_directory(self,path): self.send_error(403); return None
                def send_head(self):
                    if self.headers.get('Host','').split(':')[0] not in ('localhost','127.0.0.1'):
                        self.send_error(403); return None
                    candidate = Path(self.translate_path(self.path)).resolve()
                    try: candidate.relative_to(root)
                    except ValueError: self.send_error(403); return None
                    allowed = {'.html','.htm','.css','.js','.mjs','.json','.png','.jpg','.jpeg','.webp','.gif','.svg','.ico','.woff','.woff2','.ttf','.mp4','.mp3','.wav','.pdf','.wasm','.map','.txt','.csv'}
                    if any(p.startswith('.') for p in candidate.relative_to(root).parts) or candidate.suffix.lower() not in allowed:
                        self.send_error(403); return None
                    return super().send_head()
            server = ThreadingHTTPServer(('127.0.0.1',0),Handler)
            threading.Thread(target=server.serve_forever,daemon=True).start()
            PREVIEWS[str(root)] = server
        port = PREVIEWS[str(root)].server_port
    return 'http://127.0.0.1:'+str(port)+'/'+urllib.parse.quote(path.name)


def redirect(handler, c, key, cover=False):
    item,v = entry(c,key)
    if item['source']!='local': raise ValueError('不是本地页面')
    path = Path(v['target'])
    if cover:
        if not v.get('cover_file'): raise ValueError('没有封面')
        path = path.parent / v['cover_file']
    if not path.is_file(): raise ValueError('本地文件已不存在')
    handler.send_response(302); handler.send_header('Location',preview_url(path))
    handler.send_header('Cache-Control','no-store'); handler.end_headers()
