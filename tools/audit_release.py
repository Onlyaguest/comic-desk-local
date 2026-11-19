#!/usr/bin/env python3
"""本地发布审计：候选源码及可选历史。仅打印文件和规则名，不打印秘密。"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from release_files import ROOT, candidates

PATTERNS={
    '个人HOME路径':rb'/Users/(?!(?:me|you|user)(?:/|\b))[A-Za-z0-9_-]+/|/home/(?!user(?:/|\b))[A-Za-z0-9_-]+/',
    '服务密钥':rb'(?i)\b(?:sk-[A-Za-z0-9_-]{24,}|gh[pousr]_[A-Za-z0-9_]{24,}|github_pat_[A-Za-z0-9_]{30,}|AKIA[A-Z0-9]{16}|xox[baprs]-[A-Za-z0-9-]{20,})',
    '私钥':rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
    'JWT':rb'\beyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+',
    '私人空间地址':rb'https://(?:cohub\.live/spaces/[0-9a-f]{8}-[0-9a-f-]{27,}|mirasim\.ai/@mirasim-host-[0-9]+/)',
    '明文凭据赋值':rb'''(?i)(?:api[_-]?key|access[_-]?token|password|secret)\s*[=:]\s*["'][A-Za-z0-9_+/=-]{20,}["']''',
}
PROBES=['data/todos.jsonl','data/sources.local.json','data/index.sqlite3','data/fusion/context.local.json',
        'data/fusion/board.local.json','app/js/data.js','app/js/today.js','app/js/todos-board.js',
        '.env','.env.local','credentials.json','private.pem','private.key','server.log','node_modules/test.js','startup/machine.plist']


def scan(raw,terms=()):
    rules=[name for name,pat in PATTERNS.items() if re.search(pat,raw)]
    if any(term.encode() in raw for term in terms if term):rules.append('本机隐私标识')
    return rules


def audit(terms=(),history=False):
    files=candidates();errors=[];manifest=[]
    for name in files:
        p=ROOT/name;raw=p.read_bytes();parts=Path(name).parts
        if (parts[0] in ('data','.serena','.mirasim','.codex','.claude','startup','review')
            or p.suffix.lower() in ('.sqlite','.sqlite3','.db','.log','.pem','.key','.plist')
            or p.name.startswith('.env') or p.name in ('credentials.json','service-account.json')
            or '.local.' in p.name):errors.append(name+': 敏感/运行时文件')
        if len(raw)>2_000_000:errors.append(name+': 超过2MB需人工审阅')
        errors.extend(name+': '+rule for rule in scan(raw,terms))
        manifest.append({'path':name,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)})
    for name in PROBES:
        if subprocess.run(['git','check-ignore','--no-index','-q',name],cwd=ROOT).returncode:errors.append(name+': 未被忽略')
    historical=0
    if history:
        for line in subprocess.check_output(['git','rev-list','--objects','--all'],cwd=ROOT).decode().splitlines():
            oid,_,name=line.partition(' ')
            if subprocess.check_output(['git','cat-file','-t',oid],cwd=ROOT).strip()!=b'blob':continue
            historical+=1
            raw=subprocess.check_output(['git','cat-file','blob',oid],cwd=ROOT)
            errors.extend('历史 '+oid[:12]+' '+name+': '+rule for rule in scan(raw,terms))
    result={'ok':not errors,'candidateFiles':len(files),'historyBlobs':historical,'errors':errors,'manifest':manifest,
            'boundary':'源码、虚构样例；不含忽略数据。扫描不等于对所有未知隐私模式的保证。'}
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--history',action='store_true')
    parser.add_argument('--deny-file',type=Path,help='仓库外的本机隐私标识JSON列表，不会输出其内容')
    parser.add_argument('--output',type=Path,help='审计清单应写仓库外或被忽略的目录')
    args=parser.parse_args();terms=json.loads(args.deny_file.read_text()) if args.deny_file else []
    result=audit(terms,args.history)
    if args.output:args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(('PASS' if result['ok'] else 'FAIL')+f": 候选 {result['candidateFiles']} 文件，历史 {result['historyBlobs']} 个内容对象，问题 {len(result['errors'])}")
    for error in result['errors']:print(error)
    sys.exit(0 if result['ok'] else 1)
