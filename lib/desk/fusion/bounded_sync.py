"""手动索引增量：最多 1 身份 + 2 目录 + 2 正文 CLI，无文件/作品扫描。"""
import hashlib,json,threading,time,subprocess,os
from pathlib import Path
from desk import indexdb as db,cloudsync
from .observations import token_fields

from desk.paths import DATA
HERE=DATA/'fusion'
LOCK=threading.Lock()
LEDGER=HERE/'sync-ledger.json'
USAGE=HERE/'cohub-usage.json'

def load(path,default):
    try:return json.loads(path.read_text())
    except (OSError,ValueError):return default

def write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False));tmp.chmod(0o600);tmp.replace(path)

def cli_json(command,args,timeout=45):
    p=subprocess.run([command,*args],capture_output=True,text=True,timeout=timeout,env={**os.environ,'COHUB_CLI_AUTO_UPDATE':'0'})
    if p.returncode:
        reason='invalid cursor' if 'invalid cursor' in p.stderr.lower() else '读取失败（保留旧索引）'
        raise RuntimeError(reason)
    return json.loads(p.stdout)

def run(runner=None):
    if not LOCK.acquire(False):return {'ok':False,'error':'已有一次手动同步在执行，请稍后查看'}
    previous=load(LEDGER,[])
    if previous and previous[-1].get('ok'):
        from datetime import datetime
        age=time.time()-datetime.fromisoformat(previous[-1]['at'].replace('Z','+00:00')).timestamp()
        if age<30:
            LOCK.release()
            return {**previous[-1],'reused':True,'previousCloudCliCalls':previous[-1]['cloudCliCalls'],'cloudCliCalls':0}
    start=time.monotonic();metrics={'at':db.stamp(),'cloudCliCalls':0,'modelCalls':0,'catalogPages':0,'sessionsChecked':0,'detailCalls':0,'responseBytes':0,'directoryIncomplete':False,'errors':[]}
    runner=runner or cli_json
    def call(args):
        metrics['cloudCliCalls']+=1
        result=runner(cfg['cohubCommand'],args,timeout=45)
        metrics['responseBytes']+=len(json.dumps(result,ensure_ascii=False).encode())
        return result
    try:
        cfg=db.config()
        with db.connect() as c:
            metrics['local']=db.sync_local(c,cfg) if not cfg.get('demo',True) and cfg.get('localEnabled',False) else {'skipped':True}
            if not cfg.get('demo',True) and cfg.get('cohubEnabled'):
                auth=call(['auth','whoami','--json']);account=(auth.get('user') or {}).get('uuid')
                if not account:raise RuntimeError('Cohub 身份不可确认，保留原索引')
                previous=db.checkpoint(c,'cohub:account')
                if previous and previous!=account:raise RuntimeError('Cohub 当前账号与现有索引不同，未混入新账号')
                cursor=None;seen=set()
                for page_number in range(2):
                    args=['me','sessions','--all','--limit','100',*(['--cursor',cursor] if cursor else []),'--json']
                    page=call(args);metrics['catalogPages']+=1
                    for s in page.get('sessions',[]):
                        metrics['sessionsChecked']+=1;sid='cohub:'+account+':'+s['id'];space=s['spaceId']
                        version=hashlib.sha256(json.dumps({k:s.get(k) for k in ('updatedAt','lastMessageAt','lastMessageId','totalMessages','title','status','archivedAt')},sort_keys=True).encode()).hexdigest()
                        old=db.checkpoint(c,'version:'+sid)
                        db.upsert(c,sid,'cohub',s.get('title') or s['id'],(s.get('space') or {}).get('name') or space,
                            db.ts_epoch(s.get('lastMessageAt') or s.get('updatedAt','')),s.get('status','unknown'),s.get('archivedAt'),
                            f'https://cohub.live/spaces/{space}/sessions/{s["id"]}',source='cohub',native_id=s['id'],data={'spaceId':space,'account':account,'relation':'本人创建'})
                        if old!=version:c.execute('DELETE FROM checkpoints WHERE key=?',('detail:'+sid,))
                        db.checkpoint(c,'version:'+sid,version)
                    c.commit();info=page.get('pageInfo',{});nxt=info.get('nextCursor')
                    if not info.get('hasMore'):break
                    if not nxt or nxt in seen:raise RuntimeError('Cohub 目录游标未前进，已停止')
                    seen.add(nxt);cursor=nxt
                    if page_number==1:metrics['directoryIncomplete']=True
                cloudsync.schema(c)
                pending=c.execute("SELECT s.*,o.native_id,o.data FROM sessions s JOIN origins o ON o.session_id=s.id AND o.source='cohub' LEFT JOIN checkpoints p ON p.key='detail:'||s.id WHERE p.value IS NULL OR p.value<>s.updated ORDER BY s.updated DESC LIMIT 2").fetchall()
                usages=load(USAGE,{})
                for row in pending:
                    if metrics['detailCalls']>=2:break
                    s=dict(row);sid=s['id'];origin=json.loads(s['data']);cursor=cloudsync.cursor_for(c,sid)
                    args=['-s',origin['spaceId'],'spaces','sessions','turns','ls',s['native_id'],'--limit','20']
                    if cursor is not None:args+=['--direction','newer','--cursor',str(cursor)]
                    metrics['detailCalls']+=1
                    try:page=call([*args,'--json'])
                    except RuntimeError as e:
                        if str(e)!='invalid cursor' or cursor is None or metrics['detailCalls']>=2:raise
                        metrics['errors'].append('一条旧游标失效；预算内回读最近20轮')
                        cursor=None;metrics['detailCalls']+=1
                        page=call(['-s',origin['spaceId'],'spaces','sessions','turns','ls',s['native_id'],'--limit','20','--json'])
                    turns=page.get('turns',[])
                    if cursor is None and not page.get('hasMore') and len(turns)<20:c.execute('DELETE FROM cloud_turns WHERE session_id=?',(sid,))
                    for t in turns:
                        msgs=[]
                        for role,txt in [('user',t.get('userText') or db.text_blocks(t.get('userContent'))),('assistant',t.get('assistantText') or db.text_blocks(t.get('assistantContent')))]:
                            if txt:msgs.append({'role':role,'text':db.redact(txt),'ts':t.get('createdAt','')})
                        c.execute('INSERT OR REPLACE INTO cloud_turns VALUES(?,?,?,?,?)',(sid,t['sequence'],t.get('status','unknown'),t.get('updatedAt',''),json.dumps(msgs,ensure_ascii=False)))
                        # 只收原端明确提供的 token 字段；缺失不估计，不把累计量逐轮相加。
                        tokens=token_fields(t.get('usage') or t.get('tokenUsage'))
                        if tokens:usages[sid]={'tokens':tokens,'scope':'原端单轮用量','recordedAt':t.get('updatedAt'),'evidence':'Cohub turn usage','cost':None}
                    all_messages=[]
                    for r in c.execute('SELECT messages FROM cloud_turns WHERE session_id=? ORDER BY sequence',(sid,)):all_messages.extend(json.loads(r[0]))
                    db.replace_messages(c,sid,all_messages,'cohub')
                    if not page.get('hasMore') and len(turns)<20:
                        db.checkpoint(c,'detail:'+sid,s['updated']);db.checkpoint(c,'detail-version:'+sid,db.checkpoint(c,'version:'+sid))
                    else:c.execute('DELETE FROM checkpoints WHERE key=?',('detail:'+sid,))
                    c.commit()
                write(USAGE,usages)
                db.source_status(c,'cohub','部分' if metrics['directoryIncomplete'] else '可用',f'手动有界同步：检查 {metrics["sessionsChecked"]} 条，补读 {metrics["detailCalls"]} 个会话；未覆盖历史保留原索引')
        metrics['ok']=True
    except Exception as e:
        metrics.update(ok=False,error=str(e)[:220] if isinstance(e,(RuntimeError,ValueError)) else type(e).__name__)
    finally:
        metrics['elapsedMs']=round((time.monotonic()-start)*1000,1)
        ledger=load(LEDGER,[]);ledger.append(metrics);write(LEDGER,ledger[-100:]);LOCK.release()
    return metrics
