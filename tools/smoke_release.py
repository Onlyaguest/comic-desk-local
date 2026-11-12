#!/usr/bin/env python3
"""Black-box isolated checkout test, no real HOME/CLI/account. Run from Git checkout."""
import json,os,subprocess,sys,tempfile,time,urllib.request,socket,tarfile,io
from pathlib import Path
root=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='comicdesk-clean-') as temp:
    target=Path(temp)/'checkout';target.mkdir()
    archive=subprocess.check_output(['git','archive','HEAD'],cwd=root)
    with tarfile.open(fileobj=io.BytesIO(archive)) as t:t.extractall(target)
    home=Path(temp)/'empty-home';home.mkdir()
    env={**os.environ,'HOME':str(home),'PATH':str(Path(sys.executable).parent)+':/usr/bin:/bin','PYTHONPATH':''}
    with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    base=f'http://127.0.0.1:{port}'
    def req(path,body=None):
        data=None if body is None else json.dumps(body).encode()
        with urllib.request.urlopen(urllib.request.Request(base+path,data=data,headers={'Content-Type':'application/json'}),timeout=10) as r:return json.load(r)
    def start():
        p=subprocess.Popen([sys.executable,'bin/desk','serve','--no-open','--port',str(port)],cwd=target,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        for _ in range(80):
            if p.poll() is not None:raise AssertionError(p.stderr.read().decode())
            try:req('/api/health');return p
            except Exception:time.sleep(.1)
        p.terminate();raise AssertionError('startup timeout')
    p=start()
    try:
        status=req('/api/index/status');assert status['demo'] and status['sessions']==4,status
        todos=req('/api/action',{'action':'todos','input':{'op':'list'}})
        assert len(todos['today_open'])==2 and len(todos['carry'])==2,todos
        rid='indexed-session:demo:codex'
        req('/api/action',{'action':'todos','input':{'op':'done','id':rid}})
        ledger=(target/'data/todos.jsonl').read_bytes()
        req('/api/index/demo-message',{'id':'demo:codex'})
        todos=req('/api/action',{'action':'todos','input':{'op':'list'}})
        assert any(x['id']==rid for x in todos['today_open']),todos
        assert (target/'data/todos.jsonl').read_bytes()==ledger
        opened=req('/api/index/open',{'kind':'session','id':'demo:mirasim'});assert opened['url'].startswith('/library.html?session=demo')
        works=req('/api/index/works')['items'];assert len(works)==3,works
        assert len(next(x for x in works if '报告' in x['title'])['versions'])==2
        for work in works:
            url=work['href'];url=url if url.startswith('http') else base+url
            with urllib.request.urlopen(url) as r:
                html=r.read();assert b'<title>' in html
                asset=r.url.rsplit('/',1)[0]+'/style.css'
            with urllib.request.urlopen(asset) as r:assert r.status==200
        cover=req('/api/index/cover')['item'];assert cover and '成品' in cover['title'],cover
        assert all(not w['pending'] for w in works),works
        arts=req('/api/index/artifacts?images=1')['items'];assert len(arts)==2
        for a in arts:
            with urllib.request.urlopen(base+'/api/index/image?id='+a['id']) as r:assert b'<svg' in r.read()
        req('/api/index/refresh',{})
        time.sleep(.5)
        assert req('/api/index/status')['sessions']==4
        # No external process or network adapters should be reachable in demo refresh.
        guard="from unittest.mock import patch; from desk import indexdb; from desk.demo import seed; from desk import works; "
        guard+="\nwith patch('subprocess.run', side_effect=AssertionError('external process')), patch.object(indexdb,'sync_local',side_effect=AssertionError('private scan')), patch.object(indexdb,'run_json',side_effect=AssertionError('CLI')): indexdb.refresh()"
        subprocess.run([sys.executable,'-c',guard],cwd=target,env={**env,'PYTHONPATH':str(target/'lib')},check=True)
    finally:p.terminate();p.wait(timeout=5);p.stderr.close()
    p=start()
    try:
        assert (target/'data/todos.jsonl').read_bytes()==ledger
        assert req('/api/index/status')['sessions']==4
    finally:p.terminate();p.wait(timeout=5);p.stderr.close()
print('PASS: clean HOME boot, today/carry, done/reopen/history, restart, previews, assets, image APIs, demo refresh isolation')
