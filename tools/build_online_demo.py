#!/usr/bin/env python3
"""生成在线样例版：把离线样例「录」成一份纯静态网页，放到 demo/。

做法：复制一份干净的候选源码，在空 HOME、样例模式下起本机服务；把前端会调的接口
（GET 和几条只读 POST）各请求一次存成文件；把页面和脚本里的绝对路径改成相对路径；
每个页面最先加载 demo/_demo/shim.js，由它把 fetch 和图片地址对到录好的文件上。

产物不需要服务器：任何能按路径发静态文件的地方都能放（GitHub 原始文件经 githack、
任意静态托管）。只含虚构样例；不读用户 HOME、不调用外部 CLI、不联网。

用法：python3 tools/build_online_demo.py [--out demo]
"""
import argparse, hashlib, json, os, re, shutil, socket, subprocess, sys, tempfile, time
import urllib.error, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from release_files import copy_candidate  # noqa: E402

TEXT_EXT = {'.html', '.js', '.css', '.json', '.svg', '.md', '.txt', '.mjs'}
SKIP_APP = {'catalog.html'}  # 开发用目录页，直接列 data/，在线版不带
# 服务端把这些路径挂在站点根上；静态版里要改成相对路径
ABS = r'(?:api/|desk-v2/|css/|js/|assets/|library\.html|works\.html|original\.html|publish/|samples/|index\.html|media\b)'
NEVER_GET = ('/api/open', '/api/index/open')  # 会在本机打开东西，不录
READ_POSTS = [
    ('/api/action', {'action': 'todos', 'input': {'op': 'list'}}),
    ('/api/action', {'action': 'notes', 'input': {'op': 'list'}}),
    ('/api/desk/sync-index', {}),
]
SEED_GETS = [
    '/api/index/status', '/api/index/today', '/api/index/works', '/api/index/cover',
    '/api/index/artifacts?images=1&limit=100',
    '/api/index/sessions?q=&source=&from=&to=&offset=0&limit=30',
    '/api/index/artifacts?q=&source=&from=&to=&offset=0&limit=30',
    '/api/index/artifacts?q=&source=&from=&to=&offset=0&limit=30&images=1',
    '/api/desk/agent-status', '/api/desk/space',
    '/api/desk/board?days=7', '/api/desk/board?days=30', '/api/desk/board?days=all',
    '/api/desk/images?q=&source=&status=&offset=0&limit=24',
    '/api/publish/state',
]


def canon_body(b):
    return json.dumps(b, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def canon_path(p):
    u = urllib.parse.urlsplit(p)
    q = sorted(urllib.parse.parse_qsl(u.query, keep_blank_values=True))
    return u.path.lstrip('/') + ('?' + urllib.parse.urlencode(q) if q else '')


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=str(ROOT / 'demo'))
    out = Path(ap.parse_args().out).resolve()
    with tempfile.TemporaryDirectory(prefix='comicdesk-demo-') as tmp:
        co = Path(tmp) / 'checkout'; co.mkdir()
        home = Path(tmp) / 'home'; home.mkdir()
        copy_candidate(co, ROOT)
        env = {**os.environ, 'HOME': str(home), 'PATH': str(Path(sys.executable).parent) + ':/usr/bin:/bin', 'PYTHONPATH': ''}
        with socket.socket() as s:
            s.bind(('127.0.0.1', 0)); port = s.getsockname()[1]
        base = f'http://127.0.0.1:{port}'
        proc = subprocess.Popen([sys.executable, 'bin/desk', 'serve', '--no-open', '--port', str(port)], cwd=co, env=env,
                                stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        try:
            for _ in range(100):
                try:
                    urllib.request.urlopen(base + '/api/health', timeout=2); break
                except Exception:
                    if proc.poll() is not None:
                        raise SystemExit(proc.stderr.read().decode())
                    time.sleep(.1)
            build(out, co, home, base)
        finally:
            proc.terminate(); proc.wait(5)


def build(out, co, home, base):
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    opener = urllib.request.build_opener(NoRedirect)
    roots = [str(co), str(home)]

    def scrub(text):
        for r, rep in ((str(co), '~/comic-desk-local'), (str(home), '~')):
            text = text.replace(r, rep)
        # 作品预览原本走本机另一个端口；静态版里就是 samples/ 下的同名文件
        return re.sub(r'http://127\.0\.0\.1:\d+/', '@@BASE@@samples/', text)

    # ---------- 1. 录接口 ----------
    routes, files, n = {}, {}, [0]

    def save(body, ctype):
        h = hashlib.sha256(body).hexdigest()[:16]
        if h not in files:
            ext = {'application/json': '.json', 'image/svg+xml': '.svg', 'image/png': '.png', 'image/jpeg': '.jpg',
                   'image/webp': '.webp', 'text/html': '.html', 'text/plain': '.txt'}.get(ctype, '.bin')
            files[h] = f'_rec/{h}{ext}'
        return files[h]

    pending = list(SEED_GETS)
    seen = set()
    raw_json = {}
    while pending and len(seen) < 400:
        p = pending.pop(0)
        key = 'GET ' + canon_path(p)
        if key in seen or p.startswith(NEVER_GET):
            continue
        seen.add(key)
        try:
            r = opener.open(base + p, timeout=15)
            status, ctype, body = r.status, r.headers.get('content-type', ''), r.read()
        except urllib.error.HTTPError as e:
            status, ctype, body = e.code, e.headers.get('content-type', ''), e.read()
            if status in (301, 302, 303, 307, 308):
                loc = e.headers.get('Location', '')
                routes[key] = {'go': scrub(loc)}
                continue
        if status >= 400:
            continue
        ctype = ctype.split(';')[0].strip()
        if ctype == 'application/json':
            text = body.decode('utf-8')
            raw_json[key] = text
            for m in re.findall(r'"(/api/[^"\s]+)"', text):
                pending.append(json.loads('"' + m + '"'))
            try:
                d = json.loads(text)
            except ValueError:
                d = None
            pending += follow(p, d)
        routes[key] = {'s': status, 't': ctype, 'raw': body}
    for path, payload in READ_POSTS:
        req = urllib.request.Request(base + path, data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=30) as r:
            routes['POST ' + canon_path(path) + ' ' + canon_body(payload)] = {'s': r.status, 't': 'application/json', 'raw': r.read()}

    # 录好的 JSON 里，凡是指向另一个已录「非 JSON」接口（图片、证据页）的地址，直接换成文件地址
    final = {}
    for key, v in routes.items():
        if 'go' in v:
            final[key] = {'go': v['go']}
            continue
        final[key] = v
    direct = {}
    for key, v in final.items():
        if 'raw' in v and v['t'] != 'application/json' and key.startswith('GET '):
            direct[key[4:]] = v
    rec_dir = out / '_rec'; rec_dir.mkdir()
    table = {}
    for key, v in final.items():
        if 'go' in v:
            table[key] = {'go': v['go']}
            continue
        body = v['raw']
        if v['t'] in ('application/json', 'text/html', 'image/svg+xml', 'text/plain'):
            text = scrub(body.decode('utf-8'))
            if v['t'] == 'application/json':
                def to_file(m):
                    k = canon_path(json.loads('"' + m.group(1) + '"'))
                    if k in direct:
                        return '"@@BASE@@' + save(direct[k]['raw'], direct[k]['t']) + '"'
                    go = final.get('GET ' + k, {}).get('go')
                    if go:  # 作品预览：直接给 samples/ 下的文件地址，免得整页跳到站点根
                        return '"' + (go if go.startswith('@@BASE@@') else '@@BASE@@' + go.lstrip('/')) + '"'
                    return m.group(0)
                text = re.sub(r'"(/api/[^"\s]+)"', to_file, text)
            body = text.encode('utf-8')
        f = save(body, v['t'])
        (out / f).write_bytes(body)
        table[key] = {'f': f, 't': v['t'], 's': v['s']}
    for k, v in direct.items():  # 被 <img src> 直接引用的也要落盘
        f = save(v['raw'], v['t'])
        if not (out / f).exists():
            (out / f).write_bytes(scrub(v['raw'].decode('utf-8')).encode() if v['t'] in ('image/svg+xml', 'text/html') else v['raw'])
    # work-view 302 → samples/ 下的文件
    for key, v in table.items():
        if 'go' in v and not v['go'].startswith('@@BASE@@'):
            v['go'] = '@@BASE@@' + v['go'].lstrip('/')

    # ---------- 2. 复制页面（含启动时生成的快照）并改路径 ----------
    app = co / 'app'
    for src in app.rglob('*'):
        rel = src.relative_to(app)
        if src.is_dir() or rel.parts[0] in SKIP_APP or rel.as_posix() in SKIP_APP:
            continue
        dst = out / ('fusion' / rel.relative_to('fusion') if rel.parts[0] == 'fusion' else rel)
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.suffix in TEXT_EXT:
            dst.write_text(rewrite(src.read_text(encoding='utf-8'), rel, scrub), encoding='utf-8')
        else:
            shutil.copy2(src, dst)
    for src in (co / 'samples').iterdir():
        if src.is_file() and src.suffix in {'.html', '.css', '.svg'}:
            (out / 'samples').mkdir(exist_ok=True)
            shutil.copy2(src, out / 'samples' / src.name)

    # ---------- 3. 垫片 ----------
    shim = (ROOT / 'tools' / 'online_demo_shim.js').read_text(encoding='utf-8')
    (out / '_demo').mkdir()
    (out / '_demo' / 'shim.js').write_text(shim.replace('/*@@ROUTES@@*/{}', json.dumps(table, ensure_ascii=False, sort_keys=True)), encoding='utf-8')
    (out / 'README.md').write_text(
        '# 在线样例版（自动生成，别手改）\n\n'
        '由 `python3 tools/build_online_demo.py` 从 `samples/` 的虚构数据生成：页面 + 录好的接口回应（`_rec/`）+ 垫片（`_demo/shim.js`）。\n'
        '只能看不能改；勾选、写便签、接自己的会话要下载到本机运行。改了 `app/` 或样例后重新生成再提交。\n', encoding='utf-8')
    leaks = [p for p in out.rglob('*') if p.is_file() and p.suffix in TEXT_EXT and any(r in p.read_text(encoding='utf-8', errors='ignore') for r in roots)]
    if leaks:
        raise SystemExit('生成物里还有临时路径：' + ', '.join(str(p) for p in leaks[:5]))
    print(f'在线样例版：{out}  接口 {len(table)} 条，文件 {sum(1 for _ in out.rglob("*") if _.is_file())} 个')


def follow(path, d):
    """从一条回应里找出前端接着会请求的地址。"""
    more = []
    if not isinstance(d, dict):
        return more
    if path.startswith('/api/desk/board'):
        for c in (d.get('board') or {}).get('cards', []):
            more.append('/api/desk/card?id=' + urllib.parse.quote(c['id'], safe=''))
    if path.startswith('/api/publish/state'):
        for x in d.get('posts', []):
            i = urllib.parse.quote(x['id'], safe='')
            more += ['/api/publish/post?id=' + i, '/api/publish/diff?id=' + i]
    if path.startswith('/api/index/sessions'):
        for x in d.get('items', []):
            more.append('/api/index/detail?id=' + urllib.parse.quote(x['id'], safe=''))
    if path.startswith('/api/index/artifacts'):
        for x in d.get('items', []):
            more.append('/api/index/image?id=' + urllib.parse.quote(x['id'], safe=''))
    if path.startswith('/api/publish/post'):
        pid = urllib.parse.quote((d.get('post') or {}).get('id', ''), safe='')
        base_dir = (d.get('bodyDir') or '').strip('/')
        for img in set(re.findall(r'\]\(((?:\./)?imgs/[^)\s]+)\)', d.get('body') or '')):
            rel = '/'.join(x for x in (base_dir, img.removeprefix('./')) if x)
            more.append('/api/publish/file?id=' + pid + '&p=' + urllib.parse.quote(rel, safe=''))
    if path.startswith('/api/desk/card'):
        for rid in set(re.findall(r'"receiptId":\s*"([^"]+)"', json.dumps(d, ensure_ascii=False))):
            for i in range(4):
                more.append('/api/desk/evidence?receipt=' + urllib.parse.quote(rid, safe='') + '&index=' + str(i))
    return more


def rewrite(text, rel, scrub):
    """服务端根路径 → 相对路径。JS 的 fetch 按页面位置解析，CSS 的 url() 按样式表位置解析。"""
    top = rel.parts[0]
    deep = (rel.suffix == '.css' and len(rel.parts) > 1) or top == 'publish'
    pre = '../' if deep else './'
    text = text.replace('/desk-v2/', '/fusion/')
    text = re.sub(r'([\'"`(=])/publish/([\'"`])', lambda m: m.group(1) + pre + 'publish/index.html' + m.group(2), text)
    text = re.sub(r'href="/"', 'href="' + pre + 'index.html"', text)
    text = re.sub(r'([\'"`(=])/(?=' + ABS + r'|fusion/)', lambda m: m.group(1) + pre, text)
    if rel.suffix == '.html':
        tag = f'<script src="{pre}_demo/shim.js"></script>'
        text = re.sub(r'<head>', '<head>' + tag, text, count=1) if '<head>' in text else tag + text
    return scrub(text)


if __name__ == '__main__':
    main()
