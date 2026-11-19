"""四端纸卡：来源、规范身份与协作证据分开。普通查看只读本机。"""
import copy,hashlib,json,re,sqlite3,threading,time
from contextlib import closing
from datetime import datetime,timezone,timedelta
from pathlib import Path
from urllib.parse import quote
from . import bridge, observations, governance

from desk.paths import DATA
HERE=DATA/'fusion'
from desk import indexdb
DB=indexdb.DB
CACHE=HERE/'observations.json'
LOCK=threading.Lock()
HOT_DAYS=7
STALE_MS=30*60*1000
LABELS={'codex':'Codex','claude':'Claude Code','cohub':'Cohub 云端'}

def ms(value):
    if isinstance(value,(int,float)):return int(value if value>1e12 else value*1000)
    try:return int(datetime.fromisoformat(str(value).replace('Z','+00:00')).timestamp()*1000)
    except (ValueError,TypeError):return 0

def classify(s,last,turn,obs,body_current,now):
    host=obs.get('hostState');host_age=now-ms(obs.get('hostAt'))
    if host=='running':
        if host_age<=STALE_MS:return 'ai','本机宿主记录正在执行；截至宿主最近更新时间'
        return 'unknown','宿主运行记录已过期，当前状态待核实'
    if host in ('failed','incomplete'):return 'stuck','本机宿主记录：'+host
    event=obs.get('lifecycle') or {};kind=event.get('type');age=now-ms(event.get('at'))
    if kind=='task_started':
        if now-obs.get('fileModifiedAt',0)<=120000 and age<24*3600000:return 'ai','原日志 task_started，未见结束；截至本次读取'
        return 'unknown','原日志有开始记录，当前运行状态未核实'
    if kind in ('turn_aborted','error') or event.get('error'):return 'stuck','原日志记录中断或错误'
    if kind in ('task_complete','task_completed'):
        return ('me','原日志本轮已返回；事项尚未验收') if event.get('hasReply') else ('unknown','本轮结束，但没有可核对的助手回复')
    native=s.get('native_status','unknown')
    if not body_current:return 'unknown','目录比正文新或尚未补齐，保留未知'
    state=(turn or {}).get('status')
    if state in ('awaiting_user_input','waiting_for_input','needs_input'):return 'wait','源轮次明确等待用户输入'
    if state in ('running','pending','in_progress'):return 'ai','Cohub 最新已索引轮次状态：'+state
    if state in ('failed','interrupted','cancelled','canceled'):return 'stuck','Cohub 最新已索引轮次状态：'+state
    if state in ('completed','merged') and last:return 'me','最新轮次已有助手回复；事项尚未验收'
    if native in ('failed','incomplete','error'):return 'stuck','源运行状态：'+native
    if last and native in ('completed','有回复'):return 'me','源记录已有回复；事项尚未验收'
    return 'unknown','源记录不足；active、归档和文件存在均不等于事项完成'

def connect(path):
    c=sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True,timeout=3);c.row_factory=sqlite3.Row;return c

def display_title(title):
    # 只裁掉已知的转发尾注；原端标题和正文仍保留在索引里。
    return re.split(r'\s+—+\s+From #',str(title),maxsplit=1)[0].strip()

def canonical_sessions(c,rows,registry):
    groups={}
    for row in rows:
        s=dict(row);s['_origins']=[dict(r) for r in c.execute('SELECT * FROM origins WHERE session_id=?',(s['id'],))]
        groups.setdefault(registry.canonical(s['id'],s['_origins']),[]).append(s)
    chosen=[]
    for key,items in groups.items():
        s=max(items,key=lambda x:(bool(x.get('path')),any(o['source']==x['engine'] for o in x['_origins']),x['updated']))
        s['_aliases']=sorted(set('session:'+x['id'] for x in items)|set('session:'+k for k in registry.ids_for(s['id'])))
        s['_identity']=key;chosen.append(s)
    return sorted(chosen,key=lambda s:s['updated'],reverse=True),len(rows)-len(chosen)

def freshness(out,source_rows,now):
    checked=out.get('checkedAt') or out.get('fetchedAt')
    items=[{'id':'space','label':'空间事项','capturedAt':out.get('fetchedAt'),'checkedAt':checked,'ageSeconds':max(0,int((now-checked)/1000)) if checked else None,'stale':bool(out.get('stale') or not checked or now-checked>STALE_MS),'action':'对话内核对空间快照'}]
    for engine in ('codex','claude','cohub'):
        row=next((r for r in source_rows if r['name']==engine),{})
        at=ms(row.get('synced'))
        items.append({'id':engine,'label':LABELS[engine]+'会话','checkedAt':at,'ageSeconds':max(0,int((now-at)/1000)) if at else None,'stale':not at or now-at>STALE_MS,'action':'手动更新本机索引'})
    return items

def snapshot(days=7,pins=(),db=DB,cache=CACHE):
    started=time.monotonic();now=int(time.time()*1000);registry=governance.Registry()
    out=copy.deepcopy(bridge.state());base=out.get('board') or {'cards':[],'projects':[],'today':[],'day':datetime.now().date().isoformat(),'v':0}
    cards=base['cards'];projects=base['projects'];project_ids={p['id'] for p in projects};linked=set()
    for card in cards:
        card.update(source='mirasim',sources=['mirasim'],sourceLabel='Mirasim 空间',cardKind='事项',usage={'cost':None,'tokens':None,'note':'无数据'},observedAt=out.get('fetchedAt'))
        linked.update(str(out.get('spaceNodeId',''))+'|'+s for s in (card.get('sessions') or []))
        card['responsibility']=governance.role_for(card,registry=registry)
    metrics={'cloudCliCalls':0,'modelCalls':0,'codexBytesRead':0,'codexCacheHits':0,'codexFilesRead':0,'claudeBytesRead':0,'claudeCacheHits':0,'claudeFilesRead':0,'indexRows':0,'deduplicated':0}
    source_rows=[];errors=[];loaded=0;counts={}
    if Path(db).exists():
      with LOCK:
        observed=governance.load(cache,{})
        changed=False
        with closing(connect(db)) as c:
            source_rows=[dict(r) for r in c.execute("SELECT * FROM sources WHERE name IN ('codex','claude','cohub','mirasim')")]
            bound=now-days*86400000 if days else 0;date=datetime.fromtimestamp(bound/1000,timezone.utc).isoformat().replace('+00:00','Z')
            pin_ids=[]
            for pin in pins[:12]:
                if isinstance(pin,str) and pin.startswith('session:'):
                    pin_ids.extend([pin[8:],*registry.ids_for(pin[8:])])
            sql="SELECT * FROM sessions WHERE engine IN ('codex','claude','cohub') AND (updated>=?";params=[date]
            if pin_ids:sql+=' OR id IN ('+','.join('?'*len(pin_ids))+')';params+=pin_ids
            sql+=') ORDER BY updated DESC';rows=c.execute(sql,params).fetchall();metrics['indexRows']=len(rows)
            sessions,merged=canonical_sessions(c,rows,registry);metrics['deduplicated']+=merged
            native_usage={};native_db=Path(indexdb.config()['codexHome'])/'state_5.sqlite'
            if not indexdb.config().get('demo',True) and indexdb.config().get('localEnabled') and native_db.exists():
                try:
                    with closing(connect(native_db)) as n:native_usage={r['id']:r['tokens_used'] for r in n.execute('SELECT id,tokens_used FROM threads')}
                except sqlite3.Error:pass
            cohub_usage=governance.load(HERE/'cohub-usage.json',{})
            for s in sessions:
                origins=s['_origins'];sid=s['id'];engine=s['engine'];updated=ms(s['updated'])
                remote_keys=[governance.load_json(o.get('data')).get('spaceNodeId','')+'|'+o['native_id'] for o in origins]
                if s['_identity'] in linked or any(k in linked for k in remote_keys):metrics['deduplicated']+=1;continue
                if s['title'].startswith(("Requester's own words",'用户原话')):
                    first=c.execute("SELECT text FROM messages WHERE session_id=? AND role='user' AND text LIKE '%own words%' ORDER BY seq LIMIT 1",(sid,)).fetchone()
                    if first:
                        hit=re.search(r"own words[^\n]*:\s*\n(.+?)(?:\n\n|$)",first['text'],re.S)
                        if hit:s['title']=hit.group(1).strip()[:100]
                s['title']=display_title(s['title'])
                last=c.execute("SELECT text,ts FROM messages WHERE session_id=? AND role='assistant' ORDER BY seq DESC LIMIT 1",(sid,)).fetchone();turn=None
                if engine=='cohub':
                    try:
                        r=c.execute('SELECT status,updated FROM cloud_turns WHERE session_id=? ORDER BY sequence DESC LIMIT 1',(sid,)).fetchone();turn=dict(r) if r else None
                    except sqlite3.Error:pass
                detail=c.execute('SELECT value FROM checkpoints WHERE key=?',('detail:'+sid,)).fetchone();current=bool(detail and detail[0]==s['updated'])
                obs={};path=Path(s.get('path') or '')
                if not indexdb.config().get('demo',True) and indexdb.config().get('localEnabled') and engine in ('codex','claude') and s.get('path') and path.is_file() and updated>=now-HOT_DAYS*86400000:
                    try:
                        obs,n,cached=observations.read(path,observed.get(str(path)),engine)
                        obs['fileModifiedAt']=int(path.stat().st_mtime*1000);observed[str(path)]=obs
                        metrics[engine+'BytesRead']+=n;metrics[engine+'CacheHits']+=int(cached);metrics[engine+'FilesRead']+=int(not cached);changed|=not cached
                    except (OSError,ValueError):errors.append('部分'+LABELS[engine]+'日志不可读，保留未知')
                runtime=registry.runtime(sid,origins)
                if runtime:obs={**obs,'hostState':runtime.get('runState'),'hostAt':runtime.get('updatedAt')}
                state,why=classify(s,last,turn,obs,current,now)
                usage=copy.deepcopy(obs.get('usage') or {'tokens':None,'note':'无数据'})
                if not usage.get('tokens') and engine=='codex':
                    count=native_usage.get(sid.split(':',1)[1])
                    if isinstance(count,int) and count>0:usage={'tokens':{'total_tokens':count},'scope':'原库 tokens_used 字段','evidence':'Codex state_5.sqlite.threads.tokens_used','recordedAt':s['updated']}
                if engine=='cohub':usage=cohub_usage.get(sid,usage)
                usage['cost']=obs.get('cost')
                pid='session-project:'+hashlib.sha256((engine+'|'+s['workspace']).encode()).hexdigest()[:12]
                if pid not in project_ids:
                    name=Path(s['workspace']).name if engine in ('codex','claude') else s['workspace']
                    projects.append({'id':pid,'name':name or '未命名项目','color':'gray'});project_ids.add(pid)
                source_time=next((r['synced'] for r in source_rows if r['name']==engine),None)
                card={'id':'session:'+sid,'aliases':s['_aliases'],'no':None,'title':s['title'],'state':state,'why':why,'open':True,'who':LABELS[engine],'workspace':s['workspace'],'project':pid,'updatedAt':updated,'createdAt':updated,'closedAt':0,
                    'today':datetime.fromtimestamp(updated/1000).astimezone(timezone(timedelta(hours=8))).date()==datetime.now(timezone(timedelta(hours=8))).date() if updated else False,
                    'text':obs.get('reply') or (last['text'][:600] if last and current else ''),'todoNext':'','source':engine,'sources':[o['source'] for o in origins],'sourceLabel':LABELS[engine],'cardKind':'会话候选','nativeStatus':s['native_status'],
                    'sessionId':sid,'originUrl':'/library.html?session='+quote(sid,safe=''),'usage':usage,'observedAt':source_time,'evidence':why,'coverage':s['coverage']}
                card['responsibility']=governance.role_for(card,origins,registry);cards.append(card);loaded+=1;counts[engine]=counts.get(engine,0)+1
        if changed:
            Path(cache).parent.mkdir(parents=True,exist_ok=True);tmp=Path(cache).with_suffix('.tmp');tmp.write_text(json.dumps(observed,ensure_ascii=False));tmp.chmod(0o600);tmp.replace(cache)
    else:errors.append('四端索引尚未生成')
    metrics.update(elapsedMs=round((time.monotonic()-started)*1000,1),sessionCards=loaded)
    base.update(cards=cards,projects=projects);history=governance.load(HERE/'sync-ledger.json',[])
    out.update(ok=True,board=base,indexSources=source_rows,metrics=metrics,scopeDays=days,sessionCounts=counts,localErrors=list(set(errors)),lastIndexSync=history[-1] if history else None)
    out['freshness']=freshness(out,source_rows,now)
    out['roleSources']={'global':registry.role_source,'remoteCheckedAt':registry.context.get('checkedAt')}
    return out

def card_detail(key,db=DB,cache=CACHE):
    registry=governance.Registry();origins=[];text='';at=None
    if key.startswith('session:'):
        sid=key[8:];ids=list(set([sid,*registry.ids_for(sid)]))
        with closing(connect(db)) as c:
            rows=c.execute('SELECT * FROM sessions WHERE id IN ('+','.join('?'*len(ids))+')',ids).fetchall()
            if not rows:raise ValueError('会话未登记')
            rows,_=canonical_sessions(c,rows,registry);s=rows[0];origins=s['_origins']
            card={'id':'session:'+s['id'],'sessionId':s['id'],'source':s['engine'],'workspace':s['workspace'],'open':True}
            r=c.execute("SELECT text,ts FROM messages WHERE session_id=? AND role='assistant' ORDER BY seq DESC LIMIT 1",(s['id'],)).fetchone()
            if r:text,at=r['text'],r['ts']
            obs=governance.load(cache,{}).get(s.get('path'),{})
            if obs.get('finalTail') and ms(obs.get('finalAt'))>=ms(at):text,at=obs['finalTail'],obs['finalAt']
    else:
        card=next((c for c in (bridge.state().get('board') or {}).get('cards',[]) if c['id']==key),None)
        if not card:raise ValueError('事项未登记')
        card={**card,'source':'mirasim'}
        if card.get('open') and bridge.state().get('spaceNodeId'):
            with closing(connect(db)) as c:
                for session in (card.get('sessions') or [])[:12]:
                    r=c.execute("SELECT m.text,m.ts FROM messages m JOIN origins o ON o.session_id=m.session_id WHERE o.native_id=? AND json_extract(o.data,'$.spaceNodeId')=? AND m.role='assistant' ORDER BY m.seq DESC LIMIT 1",(session,bridge.state().get('spaceNodeId'))).fetchone()
                    if r:text,at=r['text'],r['ts'];break
    return {'ok':True,'id':card['id'],'collaboration':governance.details(card,origins,text,at,registry),'metrics':{'cloudCliCalls':0,'modelCalls':0}}
