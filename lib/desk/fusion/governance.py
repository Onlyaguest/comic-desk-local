"""纸卡协作证据。只读取本项目显式配置，绝不扫描HOME、聊天或派活记录。"""
import hashlib,json,re
from pathlib import Path
from desk import indexdb
from desk.paths import ROOT as PROJECT, DATA
HERE=DATA/'fusion'
CONTEXT=HERE/'context.local.json'
RECEIPTS=HERE/'writeback-receipts.json'

def load(path,default=None):
    try:return json.loads(Path(path).read_text())
    except (OSError,ValueError):return default

def digest(text):return hashlib.sha256(str(text).encode()).hexdigest()

def declaration(text):
    in_code=False;found=''
    for line in str(text or '').splitlines():
        if line.lstrip().startswith('```'):in_code=not in_code;continue
        if in_code or line.lstrip().startswith('>'):continue
        line=line.strip().replace('**','')
        if re.match(r'^回写\s*[：:]',line):found=line[:1500]
    return found

def statement_hash(text):return digest(re.sub(r'\s+','',text.replace('**','')))

def verify_files(evidence,root=None):
    root=root or PROJECT
    checks=[]
    for e in evidence[:12]:
        p=Path(e.get('path',''))
        if not p.is_absolute():p=Path(root)/p
        p=p.resolve()
        if not p.is_relative_to(Path(root).resolve()) or p.suffix.lower() not in ('.md','.json','.txt','.html'):
            checks.append({'target':'目标不在本项目证据范围','ok':False});continue
        try:
            data=p.read_bytes()
            ok=bool(e.get('sha256') and hashlib.sha256(data).hexdigest()==e['sha256'])
            if e.get('contains'):
                contains=all(s in data.decode('utf-8',errors='replace') for s in e['contains'])
                ok=ok and contains if e.get('sha256') else contains
        except OSError:ok=False
        checks.append({'target':str(p.relative_to(Path(root).resolve())),'ok':ok})
    return checks

def writeback(text,task_ref,at=None,receipts=None):
    line=declaration(text)
    result={'state':'not_declared','label':'未见回写说明','statement':line,'observedAt':at,'evidence':[]}
    if not line:return result
    if re.match(r'^回写\s*[：:]\s*(无回写|无需回写)',line):
        result.update(state='not_required',label='原交付声明无需回写');return result
    result.update(state='declared',label='已声明，证据待核对')
    rows=receipts if receipts is not None else receipt_rows()
    for row in reversed(rows):
        if row.get('taskRef')!=task_ref or row.get('statementHash')!=statement_hash(line):continue
        checks=verify_files(row.get('evidence',[]));result['evidence']=checks;result['receiptAt']=row.get('at');result['sourceRef']=row.get('sourceRef');result['receiptId']=row.get('id')
        if checks and all(c['ok'] for c in checks):result.update(state='verified',label='回写内容已核对')
        break
    return result


def context():
    return load(PROJECT/'samples/fusion-context.json' if indexdb.config().get('demo',True) else CONTEXT,{})


def receipt_rows():
    if not indexdb.config().get('demo',True):return load(RECEIPTS,[])
    line='回写：样例说明已更新'
    return [{'id':'sample-writeback','taskRef':'sample:review','statementHash':statement_hash(line),
             'sourceRef':'离线演示','evidence':[{'path':'samples/fusion-evidence.md',
             'sha256':hashlib.sha256((PROJECT/'samples/fusion-evidence.md').read_bytes()).hexdigest()}]}]


class Registry:
    """仅接收显式别名与任务映射，不靠标题猜身份，不读取宿主HOME。"""
    def __init__(self):
        self.context=context();self.aliases=self.context.get('aliases',{})
        self.tasks=self.context.get('tasks',{});self.records=self.context.get('records',{})
        self.local_roles=self.context.get('roles',{});self.role_source=self.context.get('source',{})
    def canonical(self,sid,origins=()):
        for o in origins:
            node=load_json(o.get('data')).get('spaceNodeId')
            if node:return node+'|'+sid
        return self.aliases.get(sid,sid)
    def task(self,sid,origins=()):return self.tasks.get(self.canonical(sid,origins),{})
    def ids_for(self,sid):
        canon=self.aliases.get(sid,sid)
        return [k for k,v in self.aliases.items() if v==canon and ':' in k]
    def runtime(self,sid,origins=()):return self.records.get(self.canonical(sid,origins),{})


def load_json(raw):
    try:return json.loads(raw or '{}') if isinstance(raw,str) else raw or {}
    except ValueError:return {}


def role_for(card,origins=(),registry=None):
    r=registry or Registry();task=r.task(card.get('sessionId') or card.get('id',''),origins)
    actor=task.get('assistant') or card.get('whoId');role=r.local_roles.get(actor,{})
    return {'machine':role.get('machine','执行节点未登记'),'actor':role.get('name',card.get('who') or '执行者待核实'),
            'assistantId':actor,'duty':role.get('duty','只有来源信息，岗位与负责人待核实'),
            'source':r.role_source if role else {},'identified':bool(role),'taskRef':task.get('taskRef','')}


def details(card,origins,last_text,last_at,registry=None):
    r=registry or Registry();role=role_for(card,origins,r)
    if card.get('source')=='mirasim' and not card.get('open'):
        return {'responsibility':role,'writeback':{'state':'unavailable','label':'受限事项不搬交付正文','evidence':[]},'feedback':[]}
    if not last_text and indexdb.config().get('demo',True):last_text=r.context.get('replies',{}).get(card['id'],'')
    current=writeback(last_text,role.get('taskRef',''),last_at,receipt_rows())
    feedback=[]
    for f in r.context.get('feedback',[]):
        if f.get('taskRef')!=role.get('taskRef'):continue
        checks=verify_files(f.get('evidence',[]))
        verified=bool(checks) and all(x['ok'] for x in checks)
        feedback.append({'sourceRef':f.get('sourceRef','本机配置'),'text':f.get('text',''), 'at':f.get('at'),
            'action':{'state':'verified' if verified else 'pending','label':'动作证据已核对' if verified else '动作证据待核对'},
            'principle':{'id':f.get('principleId','规则'),'state':'pending','label':'后续规则采用待核对'},
            'adoption':{'state':'pending','label':'后续采用待核对'},
            'nextDispatch':{'state':'unknown','label':'尚无后续派活核对证据'}})
    return {'responsibility':role,'writeback':current,'writebackHistory':[],'feedback':feedback}


def registered_evidence(receipt_id,index):
    row=next((r for r in receipt_rows() if r.get('id')==receipt_id),None)
    if not row or index<0 or index>=len(row.get('evidence',[])):raise ValueError('核对依据未登记')
    target=(PROJECT/row['evidence'][index].get('path','')).resolve()
    if not target.is_relative_to(PROJECT.resolve()) or target.suffix.lower() not in ('.md','.txt','.json','.html') or not target.is_file():raise ValueError('核对依据当前不可读')
    if target.stat().st_size>8*1024*1024:raise ValueError('核对依据过大')
    return target
