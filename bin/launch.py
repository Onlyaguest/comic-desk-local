#!/usr/bin/env python3
"""Double-click launcher. Never installs global hooks or changes shell settings."""
import json, os, subprocess, sys, time, urllib.request, webbrowser
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PORT=int(os.environ.get('COMIC_DESK_PORT','7777'))
URL=f'http://127.0.0.1:{PORT}'
def health():
    try:
        with urllib.request.urlopen(URL+'/api/health',timeout=2) as r: return json.load(r)
    except Exception: return None
d=health()
if d and d.get('root')!=str(ROOT):
    raise SystemExit(f'{PORT} 端口已有其他工作台。请先关闭它，或用 COMIC_DESK_PORT 指定其他端口。')
if not d:
    (ROOT/'data').mkdir(exist_ok=True)
    with (ROOT/'data/server.log').open('a') as log:
        p=subprocess.Popen([sys.executable,str(ROOT/'bin/desk'),'serve','--no-open','--port',str(PORT)],cwd=ROOT,
                           stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True,
                           env={**os.environ,'PATH':'/opt/homebrew/bin:/usr/local/bin:'+os.environ.get('PATH','')})
    (ROOT/'data/server.pid').write_text(str(p.pid))
    for _ in range(40):
        if health(): break
        if p.poll() is not None: raise SystemExit('启动失败，详情见 data/server.log')
        time.sleep(.25)
    else: raise SystemExit('启动超时，详情见 data/server.log')
if not os.environ.get('DESK_NO_BROWSER'): webbrowser.open(URL)
print('工作台已启动：'+URL+'\n四端索引：'+URL+'/library.html\n可关闭这个终端窗口。')
