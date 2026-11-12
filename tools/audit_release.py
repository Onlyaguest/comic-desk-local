#!/usr/bin/env python3
"""Audit staged/tracked source and ignore rules. Prints paths, never matching secrets."""
import re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
files=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0')
errors=[]
patterns=[rb'/Users/(?!me(?:/|\b))[A-Za-z0-9_-]+/',rb'(?i)(?:sk-[A-Za-z0-9_-]{24,}|gh[pousr]_[A-Za-z0-9_]{24,})',rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',rb'https://cohub\.live/spaces/[0-9a-f]{8}-[0-9a-f-]{27,}']
for name in files:
    if not name:continue
    p=ROOT/name
    if not p.is_file():continue
    if name.startswith(('data/','.serena/')) or p.suffix in ('.sqlite3','.db','.log'):
        errors.append(name+': runtime file')
    raw=p.read_bytes()
    if b'\0' not in raw and any(re.search(pat,raw) for pat in patterns):errors.append(name+': private identifier / credential pattern')
    if len(raw)>2_000_000:errors.append(name+': oversized payload needs review')
probes=['data/todos.jsonl','data/sources.local.json','data/index.sqlite3','data/works-cloud.json','app/js/today.js','app/js/todos-board.js','app/js/data.js']
for name in probes:
    if subprocess.run(['git','check-ignore','--no-index','-q',name],cwd=ROOT).returncode:errors.append(name+': missing ignore')
if errors:print('\n'.join(errors));sys.exit(1)
print(f'PASS: {len([x for x in files if x])} tracked paths audited; runtime data ignored')
