"""Resumable Cohub reads: network outside transactions, durable per-session cursors."""
import concurrent.futures
import json
import time
from urllib.parse import quote
from . import indexdb as db

def schema(c):
    c.executescript('''
    CREATE TABLE IF NOT EXISTS cloud_turns(
      session_id TEXT, sequence INTEGER, status TEXT, updated TEXT, messages TEXT,
      PRIMARY KEY(session_id,sequence));
    CREATE TABLE IF NOT EXISTS sync_failures(
      session_id TEXT PRIMARY KEY, attempts INTEGER, error TEXT, updated TEXT);
    ''')

def fetch_session(cfg, session, origin, cursor=None):
    data=json.loads(origin['data']); space=data['spaceId']; native=origin['native_id']
    args=['-s',space,'spaces','sessions']; cmd=cfg['cohubCommand']
    file_error=''
    try: files=db.run_json(cmd,[*args,'files',native,'--limit','10000','--json'])
    except RuntimeError as e:
        if 'forbidden' not in str(e): raise
        files={'files':[]}; file_error='文件目录 forbidden；正文使用独立会话读取权限'
    turns=[]; seen=set(); next_cursor=cursor
    while True:
        opts=['--direction','newer','--cursor',str(next_cursor)] if cursor is not None else (['--cursor',str(next_cursor)] if next_cursor is not None else [])
        page=db.run_json(cmd,[*args,'turns','ls',native,'--limit','100',*opts,'--json'])
        for t in page.get('turns',[]):
            messages=[]
            for role,txt in [('user',t.get('userText') or db.text_blocks(t.get('userContent'))),
                             ('assistant',t.get('assistantText') or db.text_blocks(t.get('assistantContent')))]:
                if txt: messages.append({'role':role,'text':db.redact(txt),'ts':t.get('createdAt','')})
            images=[]
            for b in t.get('assistantContent') or []:
                if not isinstance(b,dict): continue
                if b.get('type') in ('image','image_url','output_image'):
                    source=b.get('source')
                    url=b.get('url') or b.get('image_url') or (source.get('url') if isinstance(source,dict) else None)
                    if isinstance(url,dict): url=url.get('url')
                    if isinstance(url,str) and url.startswith(('https://','http://','/workspace/')): images.append(url)
            turns.append({'sequence':t['sequence'],'status':t.get('status',''),'updated':t.get('updatedAt',''),
                          'messages':messages,'images':images})
        # API can report hasMore=false on an exactly full page despite older turns existing.
        # Probe the supplied cursor on full pages; an empty/short page terminates naturally.
        if not page.get('hasMore') and len(page.get('turns',[]))<100: break
        nxt=page.get('nextCursor')
        if nxt is None or nxt in seen or nxt==next_cursor: raise RuntimeError('正文分页游标没有前进')
        seen.add(nxt); next_cursor=nxt
    return {'files':files.get('files',[]),'file_error':file_error,'turns':turns,'full':cursor is None,
            'file_limit':files.get('truncated',False) or len(files.get('files',[]))>=10000}

def cursor_for(c,sid):
    # Re-read the latest turn and every unfinished turn: their replies can still change.
    row=c.execute('SELECT max(sequence),min(CASE WHEN status NOT IN (\'completed\',\'failed\',\'cancelled\',\'interrupted\',\'merged\') THEN sequence END) FROM cloud_turns WHERE session_id=?',(sid,)).fetchone()
    if row[0] is None: return None
    return max(0,min(row[0],row[1] if row[1] is not None else row[0])-1)

def save_session(c,s,o,result):
    sid=s['id']; space=json.loads(o['data'])['spaceId']
    if result['full']: c.execute('DELETE FROM cloud_turns WHERE session_id=?',(sid,))
    for t in result['turns']:
        c.execute('INSERT OR REPLACE INTO cloud_turns VALUES(?,?,?,?,?)',
                  (sid,t['sequence'],t['status'],t['updated'],json.dumps(t['messages'],ensure_ascii=False)))
        for url in t['images']: db.artifact(c,'对话图片',url,'cohub','助手图片内容',t['updated'],sid,'image')
    for f in result['files']:
        target=f'cohub-file://{space}/'+quote(f['path'],safe='/')
        db.artifact(c,f['path'],target,'cohub','会话文件变更（非交付认定）',f.get('lastChangedAt',''),sid,'remote-file')
    messages=[]
    for row in c.execute('SELECT messages FROM cloud_turns WHERE session_id=? ORDER BY sequence',(sid,)):
        messages.extend(json.loads(row[0]))
    db.replace_messages(c,sid,messages,'cohub')
    if result['file_limit']: c.execute('UPDATE sessions SET coverage=? WHERE id=?',('正文已索引；文件达到服务上限',sid))
    current_version=db.checkpoint(c,'version:'+sid)
    if current_version==s.get('_known_version') and not result.get('file_error'):
        db.checkpoint(c,'detail:'+sid,s['updated'])
        db.checkpoint(c,'detail-version:'+sid,current_version or s['updated'])
    else:
        # A catalog refresh discovered a newer revision while this request was in flight.
        c.execute('DELETE FROM checkpoints WHERE key=?',('detail:'+sid,))
    if result.get('file_error'):
        c.execute('UPDATE sessions SET coverage=? WHERE id=?',('正文已索引；文件目录无权访问',sid))
        c.execute('INSERT INTO sync_failures VALUES(?,1,?,?) ON CONFLICT(session_id) DO UPDATE SET attempts=attempts+1,error=excluded.error,updated=excluded.updated',
                  (sid,result['file_error'],db.stamp()))
        db.checkpoint(c,'blocked-version:'+sid,current_version or s['updated'])
    else:
        c.execute('DELETE FROM sync_failures WHERE session_id=?',(sid,))
        c.execute('DELETE FROM checkpoints WHERE key=?',('blocked-version:'+sid,))
    c.commit()
    return not bool(result.get('file_error'))

def backfill(c,cfg,progress=lambda s:None,limit=None,retry_blocked=False):
    schema(c)
    rows=c.execute("SELECT s.*,o.native_id,o.data,(SELECT value FROM checkpoints WHERE key='version:'||s.id) AS _known_version FROM sessions s JOIN origins o ON s.id=o.session_id LEFT JOIN checkpoints p ON p.key='detail:'||s.id WHERE o.source='cohub' AND (p.value IS NULL OR p.value<>s.updated) ORDER BY s.updated DESC").fetchall()
    if not retry_blocked:
        rows=[r for r in rows if db.checkpoint(c,'blocked-version:'+r['id'])!=(r['_known_version'] or r['updated'])]
    if limit is not None: rows=rows[:limit]
    jobs=[(dict(r),{'native_id':r['native_id'],'data':r['data']},cursor_for(c,r['id'])) for r in rows]
    total=len(jobs); done=0; failed=0
    def fetch(job):
        s,o,cursor=job
        for attempt in range(3):
            try: return fetch_session(cfg,s,o,cursor)
            except Exception:
                if attempt==2: raise
                time.sleep(1.5*(attempt+1))
    # Bounded submission makes cancellation prompt and avoids retaining the entire history in RAM.
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        pending={}; iterator=iter(jobs)
        def fill():
            while len(pending)<4:
                job=next(iterator,None)
                if job is None: break
                pending[pool.submit(fetch,job)]=job
        fill()
        while pending:
            ready,_=concurrent.futures.wait(pending,return_when=concurrent.futures.FIRST_COMPLETED)
            for future in ready:
                s,o,_=pending.pop(future)
                try:
                    if not save_session(c,s,o,future.result()): failed+=1
                except Exception as e:
                    c.rollback();failed+=1
                    c.execute('INSERT INTO sync_failures VALUES(?,1,?,?) ON CONFLICT(session_id) DO UPDATE SET attempts=attempts+1,error=excluded.error,updated=excluded.updated',
                              (s['id'],str(e)[:180] if isinstance(e,RuntimeError) else type(e).__name__,db.stamp()))
                    if 'forbidden' in str(e): db.checkpoint(c,'blocked-version:'+s['id'],s.get('_known_version') or s['updated'])
                    c.commit()
                done+=1
                progress(f'Cohub 补齐 {done}/{total} · 失败 {failed}（已完成逐条保存）')
            fill()
    return {'processed':done,'failed':failed}
