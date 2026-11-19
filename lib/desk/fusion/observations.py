"""有界、增量读取 Codex 原始事件；不解析思考/工具正文，不累计累计量。"""
import json,time
from pathlib import Path

CAP=256*1024
TOKEN_FIELDS=('input_tokens','cached_input_tokens','cache_write_input_tokens','output_tokens','reasoning_output_tokens','total_tokens')

def token_fields(obj):
    if not isinstance(obj,dict):return {}
    return {k:v for k,v in (obj or {}).items() if k in TOKEN_FIELDS and isinstance(v,(int,float)) and v>=0}

def read(path,old=None,engine="codex"):
    p=Path(path);old=old or {};size=p.stat().st_size;mt=p.stat().st_mtime_ns
    if old.get('fileSize',old.get('size'))==size and old.get('mtime')==mt:return old,0,True
    # 压缩历史只用原索引，不为看板反复解压。
    if p.suffix=='.zst':return {'size':size,'mtime':mt,'partial':True},0,False
    append=old.get('size',0)<=size and old.get('inode')==p.stat().st_ino and (size>old.get('fileSize',0) or mt==old.get('mtime'))
    start=old.get('size',0) if append else 0
    begin=max(start,size-CAP)
    obs=dict(old) if append else {}
    with p.open('rb') as f:
        f.seek(begin);buf=f.read(CAP)
    # 未结束的一行留到下次，不能将 JSONL 的半行当成功游标。
    complete=buf.rfind(b'\n')+1
    body=buf[:complete]
    if begin>start:
        first=body.find(b'\n');body=body[first+1:] if first>=0 else b''
        obs['partial']=True
    for line in body.splitlines():
        try:j=json.loads(line)
        except (ValueError,TypeError):continue
        if not isinstance(j,dict):continue
        pl=j.get('payload') or {}
        if not isinstance(pl,dict):continue
        typ=j.get('type');pt=pl.get('type');ts=j.get('timestamp')
        if engine=='claude':
            if typ=='cost-state' and isinstance(j.get('totalCostUSD'),(int,float)):
                obs['cost']={'amount':j['totalCostUSD'],'currency':'USD','scope':'原端会话累计费用记录，未核对账单','hasUnknownModelCost':bool(j.get('hasUnknownModelCost')),'evidence':'Claude cost-state.totalCostUSD'}
                continue
            message=j.get('message') or {}
            if typ=='assistant' and isinstance(message,dict):
                usage=message.get('usage') or {}
                if isinstance(usage,dict) and usage:
                    tokens=token_fields(usage)
                    if isinstance(usage.get('cache_read_input_tokens'),(int,float)):tokens['cached_input_tokens']=usage['cache_read_input_tokens']
                    if isinstance(usage.get('cache_creation_input_tokens'),(int,float)):tokens['cache_write_input_tokens']=usage['cache_creation_input_tokens']
                    obs['usage']={'tokens':tokens,'scope':'末条API原记录','recordedAt':ts,'evidence':'Claude assistant.message.usage'}
                content=message.get('content') or []
                text=content if isinstance(content,str) else '\n'.join(b.get('text','') for b in content if isinstance(b,dict) and b.get('type')=='text')
                if message.get('stop_reason') in ('end_turn','stop_sequence') and text:
                    obs['lifecycle']={'type':'task_complete','at':ts,'hasReply':True,'error':False};obs['reply']=text[:600];obs['finalTail']=text[-8192:];obs['finalAt']=ts
            elif typ=='system' and j.get('subtype')=='api_error':obs['lifecycle']={'type':'error','at':ts,'error':True}
            continue
        if typ=='token_usage_record':
            usage=token_fields(pl.get('thread_token_usage'))
            if usage:obs['usage']={'tokens':usage,'scope':'会话累计（原记录）','recordedAt':ts,'evidence':'token_usage_record.thread_token_usage'}
        elif typ=='event_msg' and pt=='token_count':
            usage=token_fields((pl.get('info') or {}).get('total_token_usage'))
            if usage:obs['usage']={'tokens':usage,'scope':'会话累计（原记录）','recordedAt':ts,'evidence':'event_msg.token_count.total_token_usage'}
        elif typ=='event_msg' and pt in ('task_started','task_complete','task_completed','turn_aborted','error'):
            obs['lifecycle']={'type':pt,'at':ts,'error':bool(pl.get('error')),'hasReply':bool(pl.get('last_agent_message'))}
            if pt in ('task_complete','task_completed'):
                text=str(pl.get('last_agent_message') or '');obs['reply']=text[:600];obs['finalTail']=text[-8192:];obs['finalAt']=ts
    obs.update(size=begin+complete,mtime=mt,inode=p.stat().st_ino,observedAt=int(time.time()*1000),fileSize=size)
    return obs,len(buf),False
