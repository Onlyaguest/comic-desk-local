import json,os,signal,urllib.request
from pathlib import Path
root=Path(__file__).resolve().parents[1]
port=int(os.environ.get('COMIC_DESK_PORT','7777'))
try:
    with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/health',timeout=2) as r: health=json.load(r)
    if health.get('root')!=str(root): raise RuntimeError('端口属于其他目录，不停止')
    os.kill(int((root/'data/server.pid').read_text()),signal.SIGTERM)
    print('已停止工作台，数据保留')
except Exception as e: raise SystemExit('未停止：'+str(e))
