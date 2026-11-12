"""Synthetic, idempotent offline fixtures. Never read user transcripts or call a CLI."""
from datetime import timedelta, datetime, timezone
from .paths import DATA, ROOT, now, iso, load_json, write_json


def seed():
    from . import indexdb, works
    cfg = indexdb.config()
    config_path = DATA / 'sources.local.json'
    if not config_path.exists():
        write_json(config_path, {'demo': True, 'localEnabled': False, 'workbuddyEnabled': False,
            'cohubEnabled': False, 'mirasimEnabled': False,
            'sessionStartDay': (now()-timedelta(days=1)).date().isoformat()})
    if not cfg.get('demo', True): return
    # Runtime-resolved paths make a copied checkout portable. Existing ledgers stay untouched.
    samples = ROOT / 'samples'
    with indexdb.connect() as c:
        if not indexdb.checkpoint(c, 'demo:seed:v1'):
            for i, (engine, title) in enumerate([
                ('codex','样例 · 做一个番茄钟工具'), ('cohub','样例 · 设计春日海报'),
                ('mirasim','样例 · 整理旅行报告'), ('workbuddy','样例 · 完成演示页面')]):
                sid = 'demo:' + engine
                ts = iso(now() - timedelta(days=1 if i>1 else 0, minutes=i+2))
                indexdb.upsert(c,sid,engine,title,updated=ts,coverage='样例正文',summary='虚构样例，不对应真实账号。')
                c.execute('INSERT OR IGNORE INTO messages VALUES(?,?,?,?,?)',
                    (sid,0,'user',indexdb.ts_epoch(ts),'这是离线样例对话。可以在待办勾选，再模拟新对话验证自动重开。'))
            indexdb.checkpoint(c, 'demo:seed:v1', iso())
        for name,title,source in [('spring-final.svg','样例 · 春日成品海报','cohub'),('screenshot.svg','样例 · 过程截图','codex')]:
            indexdb.artifact(c,title,str(samples/name),source,'样例正式交付',updated=datetime.fromtimestamp((samples/name).stat().st_mtime,timezone.utc).isoformat(),sid='demo:'+source,kind='image')
        for name in ['report-v1.html','report-v2.html','timer.html']:
            indexdb.artifact(c,'样例 · '+name,str(samples/name),'codex','样例页面',updated=datetime.fromtimestamp((samples/name).stat().st_mtime,timezone.utc).isoformat(),sid='demo:codex',kind='html')
        c.commit()
    from . import store, indexapi
    store.SESSION_START_DAY = (load_json(config_path,{}) or {}).get('sessionStartDay',store.SESSION_START_DAY)
    indexapi.write_today()


def new_message(sid):
    from . import indexdb
    if not indexdb.config().get('demo', True) or sid not in ('demo:codex','demo:cohub','demo:mirasim','demo:workbuddy'):
        raise ValueError('只可更新离线样例会话')
    with indexdb.connect() as c:
        n=c.execute('SELECT count(*) FROM messages WHERE session_id=?',(sid,)).fetchone()[0]
        ts=indexdb.ts_epoch(iso())
        c.execute('INSERT INTO messages VALUES(?,?,?,?,?)',(sid,n,'user',ts,'样例新增对话 '+str(n)))
        c.execute('UPDATE sessions SET updated=? WHERE id=?',(ts,sid))
        c.commit()
    return {'ok':True}
