"""AI 自报状态：读 tools/agent_status_hook.py 追加的本机账本。只读尾部，不联网、不轮询。"""
import json,time
from pathlib import Path
from desk.paths import DATA

LEDGER=DATA/'fusion'/'agent-status.jsonl'
TAIL=256*1024
WORKING_STALE_MS=30*60*1000
SHOW_MS=48*3600*1000
LANES={'working':'ai','waiting':'wait','done':'me','error':'stuck'}
WORDS={'working':'在做','waiting':'等你','done':'做完','error':'出错'}

def latest(ledger=LEDGER):
    """会话 id（engine:native）→ 最新一条自报。坏行跳过。"""
    p=Path(ledger)
    try:
        with p.open('rb') as f:
            size=f.seek(0,2);f.seek(max(0,size-TAIL));raw=f.read()
    except OSError:return {}
    lines=raw.split(b'\n')
    if len(raw)==TAIL and size>TAIL:lines=lines[1:]  # 第一行可能被截断
    out={}
    for line in lines:
        try:row=json.loads(line)
        except ValueError:continue
        if not isinstance(row,dict) or row.get('state') not in LANES or not row.get('session') or row.get('agent') not in ('claude','codex'):continue
        if not isinstance(row.get('at'),(int,float)) or isinstance(row.get('at'),bool):continue  # 手改坏的行不能拖垮整块看板
        key=row['agent']+':'+str(row['session'])
        if key not in out or int(row.get('at') or 0)>=int(out[key].get('at') or 0):out[key]=row
    return out

def lane(row,now=None):
    """自报 → (泳道, 依据)。「在做」超过 30 分钟没新报告就不再当真。"""
    now=now or int(time.time()*1000);state=row.get('state');age=now-int(row.get('at') or 0)
    if state=='working' and age>WORKING_STALE_MS:return 'unknown','AI 钩子 30 分钟前报「在做」，之后没有新报告，状态待核实'
    why={'working':'AI 钩子自报：在做','waiting':'AI 钩子自报：等你','done':'AI 钩子自报：本轮做完；事项尚未验收','error':'AI 钩子自报：出错'}[state]
    if row.get('detail'):why+='（'+str(row['detail'])[:80]+'）'
    return LANES[state],why

def summary(ledger=LEDGER,now=None):
    """顶栏小标用：近 48 小时每个会话的最新状态，等你 / 出错排前面。"""
    now=now or int(time.time()*1000);items=[]
    for key,row in latest(ledger).items():
        at=int(row.get('at') or 0)
        if now-at>SHOW_MS:continue
        state=row['state']
        if state=='working' and now-at>WORKING_STALE_MS:state='unknown'
        items.append({'id':'session:'+key,'agent':row['agent'],'state':state,'label':WORDS.get(state,'状态未知'),'at':at,
                      'project':Path(str(row.get('cwd') or '')).name or '未命名项目','detail':str(row.get('detail') or '')[:80]})
    order={'waiting':0,'error':1,'working':2,'unknown':3,'done':4}
    items.sort(key=lambda x:(order[x['state']],-x['at']))
    counts={s:sum(1 for x in items if x['state']==s) for s in order}
    return {'ok':True,'items':items,'counts':counts,'ledger':'data/fusion/agent-status.jsonl','readOnly':True}
