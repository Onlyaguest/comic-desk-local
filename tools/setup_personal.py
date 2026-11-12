#!/usr/bin/env python3
"""Initialize an unused checkout for personal data. Never remove an existing ledger."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'lib'))
from desk.paths import DATA, write_json, now
from datetime import timedelta
if (DATA/'index.sqlite3').exists() or (DATA/'todos.jsonl').exists():
    raise SystemExit('此目录已经使用过。请另解压一份干净代码再运行，保留现有账本。')
write_json(DATA/'sources.local.json',{'demo':False,'localEnabled':False,'workbuddyEnabled':False,
    'cohubEnabled':False,'mirasimEnabled':False,'sessionStartDay':(now()-timedelta(days=1)).date().isoformat()})
print('个人模式已准备好。双击 start.command 启动；可用 import_files.py 登记自己的图片与 HTML。')
