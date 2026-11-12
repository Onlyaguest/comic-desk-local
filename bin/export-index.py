#!/usr/bin/env python3
"""Export the local index for reuse. No network calls; no source mutation."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'lib'))
from desk import indexdb
parser=argparse.ArgumentParser(description='导出本机索引 JSONL，默认不导出对话正文')
parser.add_argument('destination',type=Path)
parser.add_argument('--messages',action='store_true',help='同时导出已索引的私人对话正文')
args=parser.parse_args(); args.destination.mkdir(parents=True,exist_ok=True)
with indexdb.connect() as c:
    for table in ['sessions','origins','artifacts','relations','sources']+(['messages'] if args.messages else []):
        dest=args.destination/(table+'.jsonl')
        if dest.exists(): raise SystemExit(f'文件已存在，未覆盖：{dest}')
        with dest.open('x') as f:
            for row in c.execute('SELECT * FROM '+table): f.write(json.dumps(dict(row),ensure_ascii=False)+'\n')
        dest.chmod(0o600)
print('已导出到 '+str(args.destination.resolve()))
