"""Rebuildable, local-only session index. Originals remain read-only."""
from __future__ import annotations
import contextlib, hashlib, json, os, re, shutil, sqlite3, subprocess, time
from pathlib import Path
from urllib.parse import unquote, urlparse

BASE = Path(__file__).resolve().parents[2]
HOME = Path.home()
DB = BASE / 'data' / 'index.sqlite3'
CONFIG = BASE / 'data' / 'sources.local.json'

def redact(text):
    text=str(text or '')
    text=re.sub(r'(?i)((?:access_?token|api_?key|token|password|secret)=)[^\s&\)\]<>]+', r'\1[已隐藏]', text)
    text=re.sub(r'\b(?:sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9_]{20,}|eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+)', '[凭据已隐藏]', text)
    return text

def short_title(text):
    text=redact(text)
    text=re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    text=re.sub(r'https?://\S+', '链接', text)
    text=re.sub(r'\s+', ' ', text).strip()
    return text[:87]+'…' if len(text)>90 else text

def stamp():
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())

def config():
    defaults = {
        'codexHome': str(HOME / '.codex'), 'claudeHome': str(HOME / '.claude'),
        'workbuddyHome': str(HOME / '.workbuddy'),
        'mirasimCommand': str(HOME / '.mirasim/bin/mirasim'),
        'cohubCommand': str(HOME / '.codex/skills/cohub/scripts/cohub-local.sh'),
        'demo': True, 'localEnabled': False, 'workbuddyEnabled': False, 'cohubEnabled': False, 'mirasimEnabled': False, 'cohubSpaces': [],
        'cohubDetailBatch': 12, 'mirasimDetailBatch': 12,
    }
    if CONFIG.exists():
        defaults.update(json.loads(CONFIG.read_text()))
    return defaults

def connect(path=None):
    p = Path(path or DB); p.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(p, timeout=30); c.row_factory = sqlite3.Row
    c.execute('PRAGMA journal_mode=WAL'); c.execute('PRAGMA foreign_keys=ON')
    c.executescript('''
    CREATE TABLE IF NOT EXISTS sessions(
      id TEXT PRIMARY KEY, engine TEXT, title TEXT, workspace TEXT, updated TEXT,
      native_status TEXT, archived INTEGER DEFAULT 0, uri TEXT, path TEXT,
      summary TEXT DEFAULT '', coverage TEXT DEFAULT '目录', parent TEXT DEFAULT '');
    CREATE TABLE IF NOT EXISTS origins(
      session_id TEXT REFERENCES sessions(id), source TEXT, native_id TEXT,
      uri TEXT, data TEXT, PRIMARY KEY(session_id,source));
    CREATE TABLE IF NOT EXISTS messages(
      session_id TEXT REFERENCES sessions(id), seq INTEGER, role TEXT, ts TEXT,
      text TEXT, PRIMARY KEY(session_id,seq));
    CREATE TABLE IF NOT EXISTS artifacts(
      id TEXT PRIMARY KEY, title TEXT, target TEXT, kind TEXT, source TEXT,
      evidence TEXT, available TEXT, updated TEXT);
    CREATE TABLE IF NOT EXISTS relations(
      session_id TEXT REFERENCES sessions(id), artifact_id TEXT REFERENCES artifacts(id),
      evidence TEXT, PRIMARY KEY(session_id,artifact_id));
    CREATE TABLE IF NOT EXISTS checkpoints(key TEXT PRIMARY KEY,value TEXT);
    CREATE TABLE IF NOT EXISTS sources(
      name TEXT PRIMARY KEY, status TEXT, detail TEXT, synced TEXT);
    CREATE INDEX IF NOT EXISTS messages_session ON messages(session_id);
    CREATE INDEX IF NOT EXISTS sessions_updated ON sessions(updated DESC);
    CREATE VIRTUAL TABLE IF NOT EXISTS search USING fts5(session_id UNINDEXED,text,tokenize='unicode61');
    ''')
    try: os.chmod(p, 0o600)
    except OSError: pass
    return c

def checkpoint(c, key, value=None):
    if value is None:
        r = c.execute('SELECT value FROM checkpoints WHERE key=?',(key,)).fetchone()
        return r[0] if r else None
    c.execute('INSERT OR REPLACE INTO checkpoints VALUES(?,?)',(key,str(value)))

def source_status(c, name, status, detail):
    c.execute('INSERT OR REPLACE INTO sources VALUES(?,?,?,?)',(name,status,detail,stamp())); c.commit()

def upsert(c, sid, engine, title='', workspace='', updated='', native_status='unknown',
           archived=0, uri='', path='', summary='', coverage='目录', parent='', source=None, native_id=None, data=None):
    updated=ts_epoch(updated)
    old = c.execute('SELECT * FROM sessions WHERE id=?',(sid,)).fetchone()
    title=short_title(title)
    summary=redact(summary)
    vals = dict(id=sid,engine=engine,title=title,workspace=workspace,updated=updated,
                native_status=native_status,archived=int(bool(archived)),uri=uri,path=path,
                summary=summary,coverage=coverage,parent=parent)
    if old:
        for k in ('title','workspace','updated','uri','path','summary','parent'):
            if not vals[k]: vals[k]=old[k]
        if coverage == '目录' and old['coverage'] != '目录': vals['coverage']=old['coverage']
        vals['updated']=max(updated or '',old['updated'] or '')
    c.execute('INSERT INTO sessions VALUES(:id,:engine,:title,:workspace,:updated,:native_status,:archived,:uri,:path,:summary,:coverage,:parent) '
              'ON CONFLICT(id) DO UPDATE SET title=excluded.title,workspace=excluded.workspace,updated=excluded.updated,'
              'native_status=excluded.native_status,archived=excluded.archived,uri=excluded.uri,path=excluded.path,'
              'summary=excluded.summary,coverage=excluded.coverage,parent=excluded.parent',vals)
    c.execute('INSERT OR REPLACE INTO origins VALUES(?,?,?,?,?)',
              (sid,source or engine,native_id or sid.split(':')[-1],uri,json.dumps(data or {},ensure_ascii=False)))

def artifact(c, title, target, source, evidence, updated='', sid=None, kind=None):
    target=unquote(str(target)).strip()
    if redact(target)!=target: return
    if not target or len(target)>4000: return
    if source=='cohub' and sid and target.startswith('/workspace/'):
        origin=c.execute("SELECT data FROM origins WHERE session_id=? AND source='cohub'",(sid,)).fetchone()
        if origin:
            space=json.loads(origin[0]).get('spaceId')
            target='cohub-file://'+space+'/'+target[len('/workspace/'):]
    u=urlparse(target)
    if u.scheme and u.scheme not in ('http','https','codex','file','cohub-file','cohub-app'): return
    if u.scheme == 'file': target=u.path; u=urlparse(target)
    if not u.scheme:
        p=Path(target).expanduser()
        if not p.is_absolute(): return
        # Never expose credential/config stores as deliverables.
        if any(x in p.parts for x in ('.ssh','.aws','.gnupg')) or p.name in ('.env','auth.json','setting.json'):
            return
        available='存在' if p.exists() else '路径已失效'
        kind=kind or ('folder' if p.is_dir() else p.suffix.lstrip('.') or 'file')
    else: available='远端未探测'; kind=kind or 'link'
    if Path(urlparse(target).path).suffix.lower() in ('.png','.jpg','.jpeg','.gif','.webp','.avif','.svg','.bmp','.tif','.tiff','.heic'):
        kind='image'
    aid=hashlib.sha256(target.encode()).hexdigest()[:24]
    c.execute('INSERT INTO artifacts VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET '
              'title=excluded.title,available=excluded.available,updated=max(artifacts.updated,excluded.updated),kind=CASE WHEN artifacts.kind=\'image\' THEN \'image\' ELSE excluded.kind END',
              (aid,title or Path(target).name,target,kind,source,evidence,available,updated or stamp()))
    if sid: c.execute('INSERT OR REPLACE INTO relations VALUES(?,?,?)',(sid,aid,evidence))
    return aid

def extract_artifacts(c, sid, text, source, cwd='', updated=''):
    # Explicit Markdown references are evidence of a reference, not proof of completion.
    for m in re.finditer(r'!?\[([^\]\n]{0,200})\]\((<[^>]+>|[^\s)]+)\)',text):
        title,target=m.group(1), (m.group(2) or '').strip('<>')
        target=re.sub(r':\d+(?::\d+)?$', '',target) if not urlparse(target).scheme else target
        if target.startswith('sandbox:'): continue
        if target and not urlparse(target).scheme and not target.startswith('/') and cwd:
            target=str(Path(cwd)/target)
        artifact(c,title,target,source,'助手正文引用',updated,sid,'image' if m.group(0).startswith('!') else None)
    for m in re.finditer(r'`(/[^`\n]+\.(?:html|md|pdf|png|jpg|webp|mp4|mp3|zip|csv|xlsx|pptx|docx))`',text):
        artifact(c,Path(m.group(1)).name,m.group(1),source,'助手正文路径',updated,sid)

def replace_messages(c, sid, messages, source, cwd=''):
    messages=[{**m,'text':redact(m['text'])} for m in messages]
    c.execute('DELETE FROM messages WHERE session_id=?',(sid,))
    c.executemany('INSERT INTO messages VALUES(?,?,?,?,?)',
                  [(sid,i,m['role'],m.get('ts',''),m['text']) for i,m in enumerate(messages)])
    c.execute('DELETE FROM search WHERE session_id=?',(sid,))
    row=c.execute('SELECT title,workspace FROM sessions WHERE id=?',(sid,)).fetchone()
    c.execute('INSERT INTO search VALUES(?,?)',(sid,'\n'.join([row['title'],row['workspace']]+[m['text'] for m in messages])))
    for m in messages:
        if m['role']=='assistant': extract_artifacts(c,sid,m['text'],source,cwd,m.get('ts',''))
    c.execute("UPDATE sessions SET coverage=?,summary=? WHERE id=?",
              ('正文已索引',next((m['text'][:300] for m in reversed(messages) if m['role']=='assistant'),''),sid))

def text_blocks(value):
    if isinstance(value,str): return value
    if not isinstance(value,list): return ''
    return '\n'.join(b.get('text','') for b in value if isinstance(b,dict) and b.get('type') in ('text','input_text','output_text'))

def human_text(t):
    t=t.strip()
    if t.startswith(('# AGENTS.md instructions','<environment_context>','<external_codex_apps_open_page>',
                     '<system-reminder>','<local-command','<command-name>','[Request interrupted')): return ''
    return t

@contextlib.contextmanager
def jsonl_stream(path):
    if str(path).endswith('.zst'):
        z=shutil.which('zstd')
        if not z: raise RuntimeError('压缩历史需要 zstd；可安装 brew install zstd')
        proc=subprocess.Popen([z,'-dc','--',str(path)],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,encoding='utf-8',errors='replace')
        try:
            yield proc.stdout
            if proc.wait()!=0: raise RuntimeError('zstd 解压失败')
        finally:
            if proc.stdout: proc.stdout.close()
            if proc.poll() is None: proc.terminate(); proc.wait()
    else:
        with Path(path).open(encoding='utf-8',errors='replace') as f: yield f

def parse_transcript(path, engine):
    messages=[]; seen=set(); meta={}; fallback=[]; bad=0
    with jsonl_stream(path) as f:
        for line in f:
            try: o=json.loads(line)
            except (ValueError,TypeError): bad+=1; continue
            if not isinstance(o,dict): continue
            p=o.get('payload') or {}; typ=o.get('type'); ts=o.get('timestamp','')
            if engine=='codex':
                if typ=='session_meta': meta.update({k:p.get(k) for k in ('id','cwd','source')}); continue
                if typ=='event_msg' and p.get('type') in ('user_message','agent_message'):
                    fallback.append(dict(role='user' if p['type']=='user_message' else 'assistant',ts=ts,text=p.get('message','')))
                if typ!='response_item' or p.get('type')!='message': continue
                role=p.get('role'); t=text_blocks(p.get('content'))
                if role=='assistant' and p.get('phase') not in (None,'final_answer'): continue
            else:
                if o.get('sessionId'): meta['id']=o['sessionId']
                if o.get('cwd'): meta['cwd']=o['cwd']
                if o.get('isSidechain'): meta['sidechain']=True
                p=o.get('message') or {}; role=p.get('role'); t=text_blocks(p.get('content'))
                # Subagent files retain their own identity, not the parent sessionId.
                if 'subagents' in Path(path).parts: meta['parent']=meta.get('id',''); meta['id']=Path(path).stem
                uid=o.get('uuid')
                if uid and uid in seen: continue
                if uid: seen.add(uid)
            if role not in ('user','assistant'): continue
            t=human_text(t) if role=='user' else t.strip()
            if not t: continue
            messages.append(dict(role=role,text=t,ts=ts))
    if not messages: messages=[m for m in fallback if human_text(m['text'])]
    return meta,messages,bad

def ts_epoch(v):
    from datetime import datetime,timezone
    if isinstance(v,(int,float)):
        return time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime(v/1000 if v>1e12 else v))
    try:
        dt=datetime.fromisoformat(str(v).replace('Z','+00:00'))
        return dt.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    except (ValueError,TypeError): return str(v or '')

def sync_local(c, cfg, progress=lambda x:None):
    home=Path(cfg['codexHome']).expanduser(); metadata={}; paths={}; stats={'parsed':0,'cached':0,'errors':0}
    db=home/'state_5.sqlite'
    if db.exists():
        with sqlite3.connect(f'file:{db}?mode=ro',uri=True) as original:
            original.row_factory=sqlite3.Row
            for r in original.execute("SELECT id,coalesce(nullif(name,''),title) AS title,cwd,rollout_path,updated_at,archived FROM threads"):
                r=dict(r); metadata[r['id']]=r
                p=Path(r['rollout_path'])
                if not p.exists() and Path(str(p)+'.zst').exists(): p=Path(str(p)+'.zst')
                if p.exists(): paths[str(p)]=('codex',r)
                upsert(c,'codex:'+r['id'],'codex',r['title'],r['cwd'],ts_epoch(r['updated_at']),
                       archived=r['archived'],uri='codex://threads/'+r['id'],path=str(p) if p.exists() else '')
    for engine,roots in [('codex',[home/'sessions',home/'archived_sessions']),('claude',[Path(cfg['claudeHome']).expanduser()/'projects'])]:
        for root in roots:
            if not root.exists(): continue
            for p in root.rglob('*.jsonl*'):
                if p.name.endswith(('.jsonl','.jsonl.zst')): paths.setdefault(str(p),(engine,{}))
    c.commit()
    for i,(name,(engine,known)) in enumerate(paths.items()):
        p=Path(name); st=p.stat(); fp=f'{st.st_mtime_ns}:{st.st_size}'
        if checkpoint(c,'file:'+name)==fp: stats['cached']+=1; continue
        progress(f'本地记录 {i+1}/{len(paths)}')
        try:
            meta,msgs,bad=parse_transcript(p,engine)
            native=known.get('id') or meta.get('id') or p.name.removesuffix('.zst').removesuffix('.jsonl')
            sid=engine+':'+native
            title=known.get('title') or next((m['text'][:90] for m in msgs if m['role']=='user'),native)
            cwd=known.get('cwd') or meta.get('cwd') or ''
            upsert(c,sid,engine,title,cwd,max((m['ts'] for m in msgs),default=ts_epoch(st.st_mtime)),
                   '有回复' if msgs and msgs[-1]['role']=='assistant' else '未知',
                   known.get('archived',int('archived_sessions' in p.parts)),
                   'codex://threads/'+native if engine=='codex' else '',name,parent=meta.get('parent',''))
            replace_messages(c,sid,msgs,engine,cwd)
            if bad: c.execute("UPDATE sessions SET coverage=? WHERE id=?",(f'正文已索引；跳过 {bad} 行',sid))
            checkpoint(c,'file:'+name,fp); c.commit(); stats['parsed']+=1
        except Exception as e:
            c.rollback(); stats['errors']+=1
            progress(f'跳过无法读取的记录：{p.name} ({type(e).__name__})')
    for engine in ('codex','claude'):
        n=c.execute('SELECT count(*) FROM sessions WHERE engine=?',(engine,)).fetchone()[0]
        source_status(c,engine,'部分' if stats['errors'] else '可用',f'{n} 条会话；本轮解析 {stats["parsed"]}、复用 {stats["cached"]}、错误 {stats["errors"]}。元数据缺正文者保留目录。')
    source_status(c,'local','可用',f'本轮解析 {stats["parsed"]}、复用 {stats["cached"]}、错误 {stats["errors"]}。')
    return stats

def run_json(command, args, timeout=60):
    p=subprocess.run([command,*args],capture_output=True,text=True,timeout=timeout,env={**os.environ,'COHUB_CLI_AUTO_UPDATE':'0'})
    if p.returncode:
        # CLI stderr may contain configuration secrets; never persist raw errors.
        reason='命令失败'
        for word in ('unauthorized','forbidden','not logged','no local access token','ECONNREFUSED','timeout'):
            if word.lower() in p.stderr.lower(): reason=word; break
        raise RuntimeError(f'{Path(command).name}: {reason} (exit {p.returncode})')
    return json.loads(p.stdout)

def cohub_pages(cfg,args,key):
    cursor=None; seen=set()
    while True:
        d=run_json(cfg['cohubCommand'],[*args,*(['--cursor',cursor] if cursor else []),'--json'])
        yield d.get(key,[])
        info=d.get('pageInfo',{}); nxt=info.get('nextCursor')
        if not info.get('hasMore'): break
        if not nxt or nxt in seen: raise RuntimeError('分页未完成：服务未提供新游标')
        seen.add(nxt);cursor=nxt

def sync_cohub(c,cfg,progress=lambda x:None):
    if not cfg['cohubEnabled']: source_status(c,'cohub','关闭','配置中关闭'); return
    auth=run_json(cfg['cohubCommand'],['auth','whoami','--json'])
    account=(auth.get('user') or {}).get('uuid')
    if not account: raise RuntimeError('无法确认 Cohub 账号')
    checkpoint(c,'cohub:account',account)
    # Recent-first cursor pages, overlapping two unchanged pages. No historical body scan.
    n=changed=quiet=pages=0
    for page in cohub_pages(cfg,['me','sessions','--all','--limit','100'],'sessions'):
        pages+=1; page_changed=False
        for s in page:
            sid='cohub:'+account+':'+s['id']; space=s['spaceId']
            old=c.execute('SELECT updated,title,native_status,archived FROM sessions WHERE id=?',(sid,)).fetchone()
            version=hashlib.sha256(json.dumps({k:s.get(k) for k in
                ('updatedAt','lastMessageAt','lastMessageId','totalMessages','title','status','archivedAt')},sort_keys=True).encode()).hexdigest()
            previous=checkpoint(c,'version:'+sid)
            updated=ts_epoch(s.get('lastMessageAt') or s.get('updatedAt',''))
            dirty=(not old or (previous is not None and previous!=version) or
                   (old and (updated>old['updated'] or short_title(s.get('title') or s['id'])!=old['title']
                    or s.get('status','unknown')!=old['native_status'] or bool(s.get('archivedAt'))!=bool(old['archived']))))
            url=f'https://cohub.live/spaces/{space}/sessions/{s["id"]}'
            upsert(c,sid,'cohub',s.get('title') or s['id'],(s.get('space') or {}).get('name') or space,
                   updated,s.get('status','unknown'),s.get('archivedAt'),url,
                   source='cohub',native_id=s['id'],data={'spaceId':space,'account':account,'relation':'本人创建'})
            checkpoint(c,'version:'+sid,version)
            if dirty:
                c.execute('DELETE FROM checkpoints WHERE key=?',('detail:'+sid,))
                changed+=1;page_changed=True
            n+=1
        c.commit(); progress(f'Cohub 目录检查 {n} · 新增或变化 {changed}')
        quiet=0 if page_changed else quiet+1
        if quiet>=2 and not cfg.get('cohubReconcileCatalog'): break
    works=0; app_pages=0
    for page in cohub_pages(cfg,['apps','ls','--all','--filter','mine'],'items'):
        from .works import ingest_apps
        ingest_apps(page)
        app_pages+=1; unchanged=True
        for a in page:
            url=a.get('publishedUrl') or a.get('url') or a.get('publicUrl') or f'cohub-app://{a["spaceId"]}/{a["id"]}'
            title=(a.get('meta') or {}).get('title') or a.get('slug') or a['id']
            version=hashlib.sha256(json.dumps([title,url,a.get('updatedAt')]).encode()).hexdigest()
            key='app-version:'+account+':'+a['id']
            if checkpoint(c,key)!=version:
                unchanged=False
                artifact(c,title,url,'cohub','账号作品目录（未归属具体会话）',a.get('updatedAt',''),kind='app')
                checkpoint(c,key,version)
            works+=1
        c.commit()
        if unchanged and app_pages>=2 and not cfg.get('cohubReconcileCatalog'): break
    checkpoint(c,'cohub:last-catalog',stamp())
    checkpoint(c,'cohub:last-scan',json.dumps({'sessions_checked':n,'changed':changed,'pages':pages,'apps_checked':works}))
    total=c.execute("SELECT count(*) FROM origins WHERE source='cohub'").fetchone()[0]
    source_status(c,'cohub','可用',f'已收录 {total} 条本人创建的会话；本次检查最近 {n} 条目录、变化 {changed} 条，复用历史正文。账号作品检查 {works} 条。')

def mirasim_args(cfg):
    run=Path(cfg.get('mirasimHome',str(HOME/'.mirasim')))/'run'
    tokens=sorted(run.glob('local-*.token'),key=lambda p:p.stat().st_mtime,reverse=True)
    if not tokens: raise RuntimeError('Mirasim 未运行；请打开应用后刷新')
    port=cfg.get('mirasimPort') or int(tokens[0].stem.split('-')[-1])
    return ['ui-cli','--port',str(port)]

def sync_mirasim(c,cfg,progress=lambda x:None):
    if not cfg['mirasimEnabled']: source_status(c,'mirasim','关闭','配置中关闭'); return
    rows=run_json(cfg['mirasimCommand'],[*mirasim_args(cfg),'sessions','--scope','global','--limit','100000'],120)
    if not isinstance(rows,list): raise RuntimeError('Mirasim 会话返回格式变化')
    for s in rows:
        key=s['sessionKey']; engine=s.get('agent') or key.split(':')[0]
        sid=key if key.startswith(('codex:','claude:')) else 'mirasim:'+key
        upsert(c,sid,engine,s.get('title') or key,s.get('workdir',''),ts_epoch(s.get('updatedAt')),
               s.get('runState','unknown'),source='mirasim',native_id=key,
               data={'sessionKey':key})
    source_status(c,'mirasim','可用',f'{len(rows)} 条宿主会话；相同原生 ID 与 Codex/Claude 合并。产物按需读取。')

def enrich(c,cfg,sid,force=False):
    if cfg.get("demo", True): return {"ok":True,"demo":True}
    s=c.execute('SELECT * FROM sessions WHERE id=?',(sid,)).fetchone()
    if not s: raise ValueError('会话不存在')
    origins=[dict(r) for r in c.execute('SELECT * FROM origins WHERE session_id=?',(sid,))]
    for o in origins:
        data=json.loads(o['data'])
        if o['source']=='cohub':
            from . import cloudsync
            cloudsync.schema(c)
            snapshot={**dict(s),'_known_version':checkpoint(c,'version:'+sid)}
            result=cloudsync.fetch_session(cfg, snapshot, o, None if force else cloudsync.cursor_for(c,sid))
            cloudsync.save_session(c, snapshot, o, result)
            if result.get('file_error'): raise RuntimeError('正文已补齐；Cohub 拒绝文件目录访问，已保留待重试记录')
        elif o['source']=='mirasim':
            d=run_json(cfg['mirasimCommand'],[*mirasim_args(cfg),'call','listArtifacts','--args',json.dumps({'sessionKey':o['native_id']})])
            for frame in d.get('frames',[]):
                for a in frame.get('items',[]):
                    target=a.get('path') or a.get('filePath') or a.get('url')
                    if target: artifact(c,a.get('title') or a.get('name') or Path(target).name,target,'mirasim','宿主交付记录',sid=sid)
    if not any(o['source']=='cohub' for o in origins): checkpoint(c,'detail:'+sid,s['updated'])
    c.commit()
    return {'ok':True}

def refresh(progress=lambda x:None, deep=False, reconcile=False):
    import fcntl
    DB.parent.mkdir(parents=True,exist_ok=True)
    cfg=config()
    if cfg.get('demo', True):
        from .demo import seed
        seed()
        with connect() as c: return stats(c)
    if reconcile: cfg['cohubReconcileCatalog']=True
    with (DB.parent/'index.lock').open('a') as lock:
        try:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB); owns_lock=True
        except BlockingIOError: owns_lock=False
        with connect() as c:
            from .workbuddy import sync as sync_workbuddy
            for name,fn in [('local',sync_local),('workbuddy',sync_workbuddy),('mirasim',sync_mirasim),('cohub',sync_cohub)]:
                if name in ('local','workbuddy') and not cfg.get(name+'Enabled', False):
                    source_status(c,name,'关闭','需在配置中主动启用'); continue
                progress('正在刷新 '+name)
                try: fn(c,cfg,progress)
                except Exception as e:
                    c.rollback(); source_status(c,name,'暂不可用',str(e)[:180] if isinstance(e,RuntimeError) else type(e).__name__)
            from .indexapi import write_today
            write_today()
            if not owns_lock:
                progress('今日目录已更新；历史队列正在另一个任务中补齐')
                return stats(c)
            if cfg.get('cohubEnabled'):
                from . import cloudsync
                cloudsync.backfill(c,cfg,progress,limit=None if deep else cfg['cohubDetailBatch'],retry_blocked=deep)
            if cfg.get('mirasimEnabled'):
                pending=c.execute("SELECT s.id,s.updated FROM sessions s JOIN origins o ON s.id=o.session_id WHERE o.source='mirasim' ORDER BY s.updated DESC").fetchall()
                count=0
                for s in pending:
                    if checkpoint(c,'detail:'+s['id'])==s['updated']: continue
                    if not deep and count>=cfg['mirasimDetailBatch']: break
                    progress(f'读取 Mirasim 产物 {count+1}')
                    try: enrich(c,cfg,s['id']);count+=1
                    except Exception as e:
                        c.rollback(); source_status(c,'mirasim','部分',f'目录保留；产物读取失败：{type(e).__name__}')
            return stats(c)

def stats(c):
    return {'ok':True,
            'pending_bodies':c.execute("SELECT count(*) FROM sessions WHERE engine='cohub' AND coverage='目录'").fetchone()[0],
            'blocked_files':c.execute("SELECT count(*) FROM sessions WHERE engine='cohub' AND coverage LIKE '%文件目录无权访问%'").fetchone()[0],'sessions':c.execute('SELECT count(*) FROM sessions').fetchone()[0],
            'artifacts':c.execute('SELECT count(*) FROM artifacts').fetchone()[0],
            'messages':c.execute('SELECT count(*) FROM messages').fetchone()[0],
            'sources':[dict(r) for r in c.execute('SELECT * FROM sources')],
            'pending':c.execute("SELECT count(*) FROM sessions s JOIN origins o ON s.id=o.session_id LEFT JOIN checkpoints p ON p.key='detail:'||s.id WHERE o.source='cohub' AND (p.value IS NULL OR p.value<>s.updated)").fetchone()[0]}

def query(c,kind='sessions',q='',source='',offset=0,limit=50,date_from='',date_to='',images=False):
    limit=min(100,max(1,int(limit)));offset=max(0,int(offset));params=[];where=[]
    if kind=='artifacts':
        if images: where.append("kind='image'")
        if q: where.append('(title LIKE ? OR target LIKE ?)');params.extend(['%'+q+'%']*2)
        if source: where.append('source=?');params.append(source)
        table='artifacts';select='*'
    else:
        table='sessions s';select='s.*,(SELECT group_concat(source) FROM origins o WHERE o.session_id=s.id) AS sources,(SELECT count(*) FROM relations r WHERE r.session_id=s.id) AS artifact_count'
        if source: where.append('s.id IN (SELECT session_id FROM origins WHERE source=?)');params.append(source)
        if q:
            # LIKE fallback also supports Chinese substrings shorter than a tokenizer word.
            if q.isascii() and re.search(r'[A-Za-z0-9]',q):
                term=' AND '.join('\"'+w.replace('\"','\"\"')+'\"*' for w in q.split())
                where.append('(s.title LIKE ? OR s.workspace LIKE ? OR s.id IN (SELECT session_id FROM search WHERE search MATCH ?))')
                params.extend(['%'+q+'%','%'+q+'%',term])
            else:
                where.append('(s.title LIKE ? OR s.workspace LIKE ? OR s.id IN (SELECT session_id FROM search WHERE text LIKE ?))');params.extend(['%'+q+'%']*3)
    if date_from: where.append('updated>=?');params.append(ts_epoch(date_from+'T00:00:00+08:00'))
    if date_to:
        from datetime import datetime,timedelta
        end=(datetime.fromisoformat(date_to)+timedelta(days=1)).strftime('%Y-%m-%d')
        where.append('updated<?');params.append(ts_epoch(end+'T00:00:00+08:00'))
    suffix=' WHERE '+' AND '.join(where) if where else ''
    n=c.execute('SELECT count(*) FROM '+table+suffix,params).fetchone()[0]
    rows=c.execute('SELECT '+select+' FROM '+table+suffix+' ORDER BY updated DESC LIMIT ? OFFSET ?',params+[limit,offset])
    return {'items':[dict(r) for r in rows],'total':n,'offset':offset,'limit':limit}

def detail(c,sid,offset=0,limit=100):
    s=c.execute('SELECT * FROM sessions WHERE id=?',(sid,)).fetchone()
    if not s: raise ValueError('会话不存在')
    return {'session':dict(s),'origins':[dict(r) for r in c.execute('SELECT source,native_id,uri FROM origins WHERE session_id=?',(sid,))],
            'messages':[dict(r) for r in c.execute('SELECT * FROM messages WHERE session_id=? ORDER BY seq LIMIT ? OFFSET ?',(sid,min(200,int(limit)),int(offset)))],
            'message_count':c.execute('SELECT count(*) FROM messages WHERE session_id=?',(sid,)).fetchone()[0],
            'artifacts':[dict(r) for r in c.execute('SELECT a.*,r.evidence AS relation_evidence FROM artifacts a JOIN relations r ON a.id=r.artifact_id WHERE r.session_id=?',(sid,))]}
