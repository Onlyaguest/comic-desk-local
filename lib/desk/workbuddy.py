"""Read-only WorkBuddy JSONL and artifact-index adapter; no agent execution."""
import json
import re
from pathlib import Path
from . import indexdb as db

def timestamp(value):
    if isinstance(value,str) and value.isdigit(): value=int(value)
    return db.ts_epoch(value)

def parse(path):
    meta={};messages=[];seen=set();bad=0
    with path.open(encoding='utf-8') as f:
        for line in f:
            try: row=json.loads(line)
            except (ValueError,TypeError): bad+=1;continue
            if not isinstance(row,dict): bad+=1;continue
            for key in ('sessionId','cwd','aiTitle'):
                if row.get(key): meta[key]=row[key]
            if row.get('type')!='message' or row.get('role') not in ('user','assistant'): continue
            uid=row.get('id')
            if uid and uid in seen: continue
            if uid: seen.add(uid)
            text=db.text_blocks(row.get('content'))
            if row['role']=='user':
                text=re.sub(r'<system-reminder\b[^>]*>.*?</system-reminder>','',text,flags=re.S)
                query=re.findall(r'<user_query>(.*?)</user_query>',text,re.S)
                text='\n'.join(query) if query else text
            if text.strip(): messages.append({'role':row['role'],'text':text.strip(),'ts':timestamp(row.get('timestamp',''))})
    return meta,messages,bad

def sync(c,cfg,progress=lambda x:None):
    home=Path(cfg.get('workbuddyHome',str(Path.home()/'.workbuddy'))).expanduser()
    stats={'parsed':0,'cached':0,'errors':0,'artifact_files':0}
    if not home.exists():
        db.source_status(c,'workbuddy','未安装','未发现 WorkBuddy 本地数据目录');return stats
    for path in sorted((home/'projects').glob('*/*.jsonl')):
        try:
            st=path.stat();fingerprint=f'v2:{st.st_mtime_ns}:{st.st_size}'
            key='workbuddy:transcript:'+str(path)
            if db.checkpoint(c,key)==fingerprint: stats['cached']+=1;continue
            meta,messages,bad=parse(path);native=meta.get('sessionId') or path.stem;sid='workbuddy:'+native
            title=meta.get('aiTitle') or next((m['text'] for m in messages if m['role']=='user'),native)
            cwd=meta.get('cwd','');updated=max((m['ts'] for m in messages if m['ts']),default='')
            db.upsert(c,sid,'workbuddy',title,cwd,updated,path=str(path),native_id=native,
                      native_status='有回复' if messages and messages[-1]['role']=='assistant' else '未知')
            db.replace_messages(c,sid,messages,'workbuddy',cwd)
            if bad: c.execute('UPDATE sessions SET coverage=? WHERE id=?',(f'正文已索引；跳过 {bad} 行',sid))
            # A partial last line may be a live write: retry next refresh.
            if not bad: db.checkpoint(c,key,fingerprint)
            c.commit();stats['parsed']+=1
        except (OSError,ValueError,TypeError): c.rollback();stats['errors']+=1
    for path in sorted((home/'artifact-index').glob('*.json')):
        sid='workbuddy:'+path.stem
        if not c.execute('SELECT 1 FROM sessions WHERE id=?',(sid,)).fetchone(): continue
        try:
            st=path.stat();fingerprint=f'v2:{st.st_mtime_ns}:{st.st_size}';key='workbuddy:artifacts:'+str(path)
            if db.checkpoint(c,key)==fingerprint: stats['cached']+=1;continue
            data=json.loads(path.read_text());artifacts=data.get('artifacts',[])
            for a in artifacts:
                target=(a.get('fileChangeInfo') or {}).get('uri') or a.get('uri','')
                if not target.startswith(('/','file://','https://','http://')): continue
                db.artifact(c,a.get('title') or a.get('name',''),target,'workbuddy',
                            'WorkBuddy 产物目录（文件变更不等于成品）',timestamp(a.get('updatedAt') or data.get('lastUpdated','')),sid)
            db.checkpoint(c,key,fingerprint);c.commit();stats['artifact_files']+=1
        except (OSError,ValueError,TypeError): c.rollback();stats['errors']+=1
    n=c.execute("SELECT count(*) FROM sessions WHERE engine='workbuddy'").fetchone()[0]
    db.source_status(c,'workbuddy','部分' if stats['errors'] else '可用',f'{n} 条本机会话；解析 {stats["parsed"]}，复用 {stats["cached"]}，产物目录更新 {stats["artifact_files"]}，错误 {stats["errors"]}。仅本机记录；App 暂无已验证的会话深链。')
    return stats
