"""发稿台：一篇稿从写好到发出的流程条、两版对比、「我来改」留底、外部编辑器改完拉回对比再采用。

默认离线样例：只读写 data/publish/demo/（首次用时从 samples/publish/ 复制），不调用任何外部命令。
个人模式：自己写 data/publish/config.local.json（不进 Git），见 docs/PUBLISH.md。
只用标准库；对比用 difflib。
"""
from __future__ import annotations

import difflib
import json
import re
import shutil
import subprocess
from pathlib import Path

from .paths import DATA, ROOT, append_jsonl, iso, load_json, now, read_jsonl, today

SAMPLES = ROOT / 'samples' / 'publish'
CONF = DATA / 'publish' / 'config.local.json'
DEMO = DATA / 'publish' / 'demo'
STATUS = ['灵感', '草稿', '待发', '已发出', '已归档']
KINDS = {'rewrite': '按我这段重写整篇', 'patch': '只改这一处', 'rule': '以后都这样'}
COMMAND_KEYS = ('preview', 'check', 'export', 'fetch')
IMG_EXT = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg'}
IMG = re.compile(r'!\[([^\]]*)\]\(([^)\s]+)[^)]*\)')


# ---------- 配置与登记表 ----------
def config():
    c = load_json(CONF, None)
    if isinstance(c, dict) and c.get('posts'):
        return c
    return None


def mode():
    return 'personal' if config() else 'demo'


def where():
    """返回 (登记表路径, 稿件根目录)。样例模式首次用时把 samples/publish 复制到 data/publish/demo。"""
    c = config()
    if c:
        reg = Path(c['posts']).expanduser().resolve()
        root = Path(c.get('root') or reg.parent).expanduser().resolve()
        return reg, root
    if not (DEMO / 'posts.json').exists():
        DEMO.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(SAMPLES, DEMO, dirs_exist_ok=True)
    return DEMO / 'posts.json', DEMO.resolve()


def load():
    reg, _ = where()
    data = load_json(reg, [])
    return [x for x in (data if isinstance(data, list) else []) if isinstance(x, dict) and x.get('id')]


def save(posts, change):
    reg, _ = where()
    tmp = reg.with_suffix(reg.suffix + '.tmp')
    # 一行一条：和常见的手写登记表一样好 diff
    tmp.write_text('[\n' + ',\n'.join('  ' + json.dumps(x, ensure_ascii=False) for x in posts) + '\n]\n', encoding='utf-8')
    tmp.replace(reg)
    append_jsonl(DATA / 'publish' / 'changes.jsonl', {'at': iso(), **change})


def find(pid):
    for x in load():
        if x['id'] == pid:
            return x
    raise ValueError('登记表里没有这篇')


def inside(root: Path, rel: str) -> Path:
    """相对路径只许落在稿件根目录里。"""
    if not rel:
        raise ValueError('路径是空的')
    p = (root / rel).resolve()
    if not p.is_relative_to(root):
        raise ValueError('路径越界')
    return p


def pack_of(x):
    return x.get('pack') or (str(Path(x['body']).parent) if x.get('body') else '')


def pack_dir(x):
    _, root = where()
    rel = pack_of(x)
    return inside(root, rel) if rel else None


def body_path(x):
    _, root = where()
    return inside(root, x['body']) if x.get('body') else None


def desk_dir(x, make=False):
    d = pack_dir(x)
    if d is None:
        raise ValueError('这篇没有稿件目录')
    d = d / '.desk'
    if make:
        d.mkdir(parents=True, exist_ok=True)
    return d


def read(p):
    try:
        return Path(p).read_text(encoding='utf-8') if p else ''
    except FileNotFoundError:
        return ''


# ---------- 两版 ----------
def siblings(x, posts=None):
    """同一平台、目录名只差 -v2 / -gemini / -opus 这类后缀，或用 versionOf 指明的，算同一篇的另一版。"""
    posts = posts if posts is not None else load()
    base = lambda r: re.sub(r'-(v\d+|gemini|opus|gpt|claude)$', '', pack_of(r), flags=re.I)
    root_id = x.get('versionOf') or x['id']
    out = []
    for r in posts:
        if r['id'] == x['id'] or r.get('status') == '已归档':
            continue
        same_pack = pack_of(x) and r.get('platform') == x.get('platform') and base(r) == base(x)
        same_root = (r.get('versionOf') or r['id']) == root_id
        if same_pack or same_root:
            out.append(r)
    return out


# ---------- 我来改 ----------
def notes(x):
    try:
        return list(reversed(read_jsonl(desk_dir(x) / '调整.jsonl')))
    except ValueError:
        return []


def add_note(x, kind, text):
    if kind not in KINDS:
        raise ValueError('不认识的改法')
    text = str(text or '').strip()
    if not text:
        raise ValueError('先写你要怎么改')
    if len(text) > 8000:
        raise ValueError('太长了，分几次写')
    rec = {'at': iso(), 'kind': kind, 'label': KINDS[kind], 'text': text}
    append_jsonl(desk_dir(x, make=True) / '调整.jsonl', rec)
    return {**rec, 'prompt': prompt_for(x, kind, text)}


def prompt_for(x, kind, text):
    """给自己的 AI 助手的一段话：复制过去就能开工。"""
    b = body_path(x)
    how = {
        'rewrite': '用我这段当骨架重写整篇：我写的句子原样保留、顺序不改，照我的口气往下扩写。',
        'patch': '只改我指的这一处，别的段落不动。',
        'rule': '这是以后写稿都要照做的要求：先改这篇，再把这条记进你的写稿规矩里。',
    }[kind]
    return (f'请帮我改稿《{x.get("title", "")}》。\n{how}\n\n我写的：\n{text}\n\n'
            f'稿子在：{b}\n改之前先把旧稿复制一份到同目录的「历史/」里；我以前提过的要求在 {desk_dir(x) / "调整.jsonl"}。')


# ---------- 外部编辑器里改：导出 → 改 → 拉回对比 → 采用 ----------
def split_front(src):
    m = re.match(r'---\r?\n([\s\S]*?)\r?\n---\r?\n', src)
    if not m:
        return '', {}, src
    fm = {}
    for line in m.group(1).splitlines():
        if ': ' in line:
            k, v = line.split(': ', 1)
            fm[k.strip()] = v.strip()
    return m.group(1), fm, src[m.end():]


def strip_head(md):
    """去掉文档开头的「# 标题 / 封面图 / > 作者、摘要」，云文档导出常带这一段。"""
    title = digest = ''
    _, fm, s = split_front(md.replace('\r', ''))
    title, digest = fm.get('title', ''), fm.get('digest', '')
    h = re.match(r'#\s+(.+)\n+', s)
    if h:
        title = re.sub(r'^旧版\s*·\s*', '', h.group(1).strip())
        s = s[h.end():]
    c = re.match(r'!\[封面\]\([^)]*\)\n+', s)
    if c:
        s = s[c.end():]
    q = re.match(r'(>\s?.*\n?)+', s)
    if q and re.search(r'作者：|摘要：', q.group(0)):
        for line in q.group(0).splitlines():
            t = re.sub(r'^>\s?', '', line).rstrip()
            if t.startswith('摘要：'):
                digest = t[3:]
        s = s[q.end():]
    return title, digest, s.lstrip('\n')


def paras(body):
    imgs = []

    def tok(m):
        imgs.append((m.group(1), m.group(2)))
        return f'［图 {len(imgs)}{"：" + m.group(1) if m.group(1) else ""}］'
    t = IMG.sub(tok, body.replace('\\~', '~'))
    out = []
    for p in re.split(r'\n\s*\n', t):
        p = '\n'.join(line.rstrip() for line in p.split('\n')).strip()
        if p:
            out.append(p)
    return out, imgs


def key(p):
    return re.sub(r'［图 (\d+)(：[^］]*)?］', r'［图 \1］', p)


def export(x):
    """把定稿复制成 .desk/外改.md（拿去任何编辑器改），同时留一份底稿用来对比。"""
    b = body_path(x)
    if not b or not b.exists():
        raise ValueError('找不到定稿文件')
    d = desk_dir(x, make=True)
    src = b.read_text(encoding='utf-8')
    (d / '外改底稿.md').write_text(src, encoding='utf-8')
    (d / '外改.md').write_text(src, encoding='utf-8')
    append_jsonl(d / '调整.jsonl', {'at': iso(), 'kind': 'export', 'label': '导出去改'})
    out = {'ok': True, 'file': str(d / '外改.md')}
    if cmd(x, 'export'):
        out['command'] = run(x, 'export')
    return out


def compare(x):
    try:
        d = desk_dir(x)
    except ValueError:
        return None
    edited_p = d / '外改.md'
    if not edited_p.exists():
        return None
    e_title, e_digest, e_body = strip_head(edited_p.read_text(encoding='utf-8'))
    _, fm, local_body = split_front(read(body_path(x)))
    base_p = d / '外改底稿.md'
    has_base = base_p.exists()
    base_body = strip_head(base_p.read_text(encoding='utf-8'))[2] if has_base else local_body
    A, a_imgs = paras(base_body)
    B, b_imgs = paras(e_body)
    L, _ = paras(local_body)
    blocks = []
    sm = difflib.SequenceMatcher(a=[key(p) for p in A], b=[key(p) for p in B], autojunk=False)
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == 'equal':
            blocks.append({'t': 'same', 'n': i2 - i1})
            continue
        old, new = A[i1:i2], B[j1:j2]
        if op == 'replace' and len(old) == len(new) <= 4:
            for o, n in zip(old, new):
                blocks.append({'t': 'edit', 'parts': char_diff(o, n)})
            continue
        if old:
            blocks.append({'t': 'del', 'v': old})
        if new:
            blocks.append({'t': 'add', 'v': new})
    changed = sum(len(b.get('v', [])) if b['t'] in ('add', 'del') else (1 if b['t'] == 'edit' else 0) for b in blocks)
    return {
        'changed': changed, 'blocks': blocks, 'hasBase': has_base,
        'localMoved': has_base and [key(p) for p in L] != [key(p) for p in A],
        'title': {'edited': e_title, 'local': fm.get('title') or x.get('title', '')},
        'digest': {'edited': e_digest, 'local': fm.get('digest', '')},
        'imgs': {'edited': len(b_imgs), 'base': len(a_imgs)},
        'file': str(edited_p), 'at': iso_mtime(edited_p),
    }


def char_diff(a, b):
    out = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes():
        if op == 'equal':
            out.append(['same', a[i1:i2]])
        else:
            if i2 > i1:
                out.append(['del', a[i1:i2]])
            if j2 > j1:
                out.append(['add', b[j1:j2]])
    return out


def iso_mtime(p):
    from datetime import datetime
    return datetime.fromtimestamp(Path(p).stat().st_mtime, now().tzinfo).isoformat(timespec='seconds')


def adopt(x):
    """采用外部改过的版本当定稿：旧稿先进 历史/，图片按第几张对回本机文件，信息头保留（标题、摘要跟着改）。"""
    b = body_path(x)
    if not b or not b.exists():
        raise ValueError('找不到定稿文件')
    d = desk_dir(x)
    if not (d / '外改.md').exists():
        raise ValueError('还没有外改的版本')
    e_title, e_digest, e_body = strip_head((d / '外改.md').read_text(encoding='utf-8'))
    local_src = b.read_text(encoding='utf-8')
    fm_raw, fm, local_body = split_front(local_src)
    base = strip_head(read(d / '外改底稿.md'))[2] if (d / '外改底稿.md').exists() else local_body
    base_imgs = paras(base)[1]
    lost, k = [], [0]

    def put(m):
        i = k[0]
        k[0] += 1
        if i >= len(base_imgs):
            lost.append(m.group(1) or f'第 {i + 1} 张')
            return f'<!-- 外改里新加的图没对上本机文件：{m.group(1)} -->'
        alt, src = base_imgs[i]
        if m.group(2) == src:
            return m.group(0)
        return f'![{m.group(1) or alt}]({src})'
    body = IMG.sub(put, e_body.replace('\\~', '~'))
    body = re.sub(r'[ \t]+$', '', body, flags=re.M)
    body = re.sub(r'\n{3,}', '\n\n', body).strip() + '\n'

    def set_fm(raw, k2, v):
        if not v:
            return raw
        line = f'{k2}: {v}'
        return re.sub(rf'^{k2}: .*$', line, raw, flags=re.M) if re.search(rf'^{k2}: ', raw, flags=re.M) else (raw + '\n' + line if raw else line)
    if fm_raw:
        if e_title and e_title != fm.get('title'):
            fm_raw = set_fm(fm_raw, 'title', e_title)
        if e_digest and e_digest != fm.get('digest'):
            fm_raw = set_fm(fm_raw, 'digest', e_digest)
    hist = pack_dir(x) / '历史' / (now().strftime('%Y%m%d_%H%M%S') + '_采用外改前')
    hist.mkdir(parents=True, exist_ok=True)
    shutil.copy2(b, hist / b.name)
    b.write_text((f'---\n{fm_raw}\n---\n\n' if fm_raw else '') + body, encoding='utf-8')
    # 采用后外改的版本就是新的底稿，下一轮从这里对比
    shutil.copy2(b, d / '外改底稿.md')
    shutil.copy2(b, d / '外改.md')
    _, root = where()
    rec = {'at': iso(), 'kind': 'adopt', 'label': '采用外改版', 'backup': str(hist.relative_to(root)), 'lost': lost}
    append_jsonl(d / '调整.jsonl', rec)
    return {'ok': True, 'backup': rec['backup'], 'lost': lost}


# ---------- 可选命令（只在个人模式、只从本机配置读） ----------
def cmd(x, k):
    c = config()
    if not c or k not in COMMAND_KEYS:
        return None
    v = (c.get('commands') or {}).get(k)
    return v if isinstance(v, list) and v and all(isinstance(s, str) for s in v) else None


def run(x, k):
    """跑配置里的一条命令：不经过 shell，占位符只有 {pack} {body} {id} {out}。fetch 的标准输出存成 .desk/外改.md。"""
    argv = cmd(x, k)
    if not argv:
        raise ValueError('样例模式不调用外部命令；个人模式要在 config.local.json 的 commands 里写上 ' + k)
    d = desk_dir(x, make=True)
    sub = {'{pack}': str(pack_dir(x)), '{body}': str(body_path(x) or ''), '{id}': x['id'], '{out}': str(d / '外改.md')}
    argv = [sub.get(a, a) for a in argv]
    try:
        p = subprocess.run(argv, capture_output=True, text=True, timeout=300, cwd=str(pack_dir(x)))
    except (OSError, subprocess.TimeoutExpired) as e:
        return {'ok': False, 'out': str(e)[-1500:]}
    if k == 'fetch' and p.returncode == 0 and p.stdout.strip() and '{out}' not in (cmd(x, k) or []):
        (d / '外改.md').write_text(p.stdout, encoding='utf-8')
    append_jsonl(d / '调整.jsonl', {'at': iso(), 'kind': 'run:' + k, 'label': '跑 ' + k, 'ok': p.returncode == 0})
    return {'ok': p.returncode == 0, 'code': p.returncode, 'out': (p.stdout + p.stderr)[-3000:]}


# ---------- 走到哪了 ----------
def steps(x, posts=None):
    b = body_path(x) if x.get('body') else None
    has_body = bool(b and b.exists())
    sib = siblings(x, posts)
    qa = str(x.get('qa') or '')
    mine = [n for n in notes(x) if n.get('kind') in KINDS or n.get('kind') == 'adopt']
    cmpr = compare(x) if has_body else None
    st = x.get('status')
    out = [
        {'k': 'write', 'label': '写稿', 'state': 'todo' if st == '灵感' else 'done' if has_body else 'doing',
         'detail': '还是灵感' if st == '灵感' else ' '.join(s for s in [x.get('by', ''), x.get('date', '')] if s) + (f' · 另有 {len(sib)} 版可对比' if sib else '')},
        {'k': 'qa', 'label': '验收', 'state': 'todo' if not qa else 'done' if qa.startswith('过') else 'fail',
         'detail': qa[:60] or '还没验（自己或请人照清单验）'},
        {'k': 'mine', 'label': '我来改', 'state': 'done' if mine else 'todo',
         'detail': f'改过 {len(mine)} 次，最近 {mine[0]["at"][:16].replace("T", " ")}' if mine else '有想改的直接写'},
        {'k': 'outside', 'label': '外部改', 'state': 'todo' if not cmpr else 'doing' if cmpr['changed'] else 'done',
         'detail': '导出一份，拿去任何编辑器（或云文档）改' if not cmpr else f'外改版有 {cmpr["changed"]} 处不一样，看完点采用' if cmpr['changed'] else '外改版和定稿一致'},
        {'k': 'pick', 'label': '挑这版', 'state': 'done' if x.get('picked') or st == '已发出' else 'todo',
         'detail': '⭐ 挑中了' if x.get('picked') else ('和另一版比一比再挑' if sib else '点 ⭐ 挑它要发')},
        {'k': 'send', 'label': '发出去', 'state': 'done' if st in ('已发出',) else 'todo',
         'detail': f'发出 {x.get("sentAt", "")}'.strip() if st == '已发出' else '复制标题和正文去发，点发布的永远是你'},
        {'k': 'archive', 'label': '归档', 'state': 'done' if x.get('url') else 'doing' if st == '已发出' else 'todo',
         'detail': '链接已填' if x.get('url') else '发出后填上链接'},
    ]
    return out


# ---------- 改状态 ----------
def update(pid, patch):
    posts = load()
    x = next((r for r in posts if r['id'] == pid), None)
    if not x:
        raise ValueError('登记表里没有这篇')
    out = {}
    if 'status' in patch:
        s = patch['status']
        if s not in STATUS:
            raise ValueError('状态只能是：' + ' / '.join(STATUS))
        x['status'] = out['status'] = s
        if s == '已发出':
            x['sentAt'] = today()
            x['picked'] = False
        if s == '已归档':
            x['picked'] = False
    if 'picked' in patch:
        x['picked'] = out['picked'] = bool(patch['picked'])
    if 'qa' in patch:
        x['qa'] = out['qa'] = str(patch['qa'])[:300]
    if 'url' in patch:
        u = str(patch['url']).strip()
        if u and not u.startswith(('http://', 'https://')):
            raise ValueError('链接要以 http:// 或 https:// 开头')
        x['url'] = out['url'] = u
    save(posts, {'op': 'set', 'id': pid, **out})
    return x


# ---------- 给网页的形状 ----------
def summary(x):
    return {k: x.get(k) for k in ('id', 'title', 'platform', 'account', 'status', 'date', 'picked', 'note', 'idea', 'url', 'qa') if x.get(k) not in (None, '')}


def state():
    posts = load()
    return {'ok': True, 'mode': mode(), 'statuses': STATUS, 'posts': [summary(x) for x in posts]}


def post(pid):
    posts = load()
    x = next((r for r in posts if r['id'] == pid), None)
    if not x:
        raise ValueError('登记表里没有这篇')
    b = body_path(x) if x.get('body') else None
    _, root = where()
    c = compare(x) if b and b.exists() else None
    return {
        'ok': True, 'mode': mode(), 'post': summary(x), 'steps': steps(x, posts),
        'body': read(b) if b else '', 'bodyDir': str(Path(x['body']).parent) if x.get('body') else '',
        'siblings': [summary(s) for s in siblings(x, posts)],
        'notes': notes(x)[:8], 'commands': [k for k in COMMAND_KEYS if cmd(x, k)],
        'outside': {k: c[k] for k in ('changed', 'localMoved', 'hasBase', 'at')} if c else None,
        'outsideFile': str(desk_dir(x) / '外改.md') if pack_of(x) else '',
    }


def file_bytes(pid, rel):
    x = find(pid)
    _, root = where()
    p = inside(root, rel)
    base = pack_dir(x)
    if base is None or not p.is_relative_to(base) or p.suffix.lower() not in IMG_EXT or not p.is_file():
        raise ValueError('只能看这篇稿目录里的图片')
    return p


def action(body):
    op = str(body.get('op') or '')
    x = find(str(body.get('id') or ''))
    if op == 'pick':
        return {'ok': True, 'post': summary(update(x['id'], {'picked': bool(body.get('on', True))}))}
    if op == 'status':
        patch = {'status': body.get('status')}
        if body.get('url'):
            patch['url'] = body['url']
        return {'ok': True, 'post': summary(update(x['id'], patch))}
    if op == 'url':
        return {'ok': True, 'post': summary(update(x['id'], {'url': body.get('url', '')}))}
    if op == 'qa':
        return {'ok': True, 'post': summary(update(x['id'], {'qa': body.get('qa', '')}))}
    if op == 'note':
        return {'ok': True, 'note': add_note(x, body.get('kind'), body.get('text'))}
    if op == 'export':
        return export(x)
    if op == 'adopt':
        return adopt(x)
    if op == 'run':
        return {'ok': True, 'result': run(x, str(body.get('key') or ''))}
    raise ValueError('不认识的操作')
