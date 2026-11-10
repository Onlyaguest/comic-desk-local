#!/usr/bin/env python3
"""生成一份通用、脱敏的本地桌面种子。

只跑一次；之后由 `desk install` / `desk build` 读写 data/。
这个文件留在 tools/ 里，是为了让人一眼看懂「模板原来长什么样」。
"""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(ROOT, 'app', 'assets', 'base')
os.makedirs(BASE, exist_ok=True)

def svg(name, body, w=400, h=300, transparent=False):
    bg = '' if transparent else '<rect width="100%" height="100%" fill="#f6eeda"/>'
    doc = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
           f'{bg}{body}</svg>')
    open(os.path.join(BASE, name), 'w', encoding='utf-8').write(doc)

# 占位图：故意画得诚实，不装成真照片
svg('photo-1.svg', '''
<rect x="40" y="40" width="320" height="220" rx="10" fill="#fff" stroke="#171310" stroke-width="5"/>
<circle cx="120" cy="120" r="34" fill="#ffd23f" stroke="#171310" stroke-width="5"/>
<path d="M40 230 L150 140 L220 200 L280 160 L360 230" fill="none" stroke="#171310" stroke-width="6"/>
<text x="200" y="286" text-anchor="middle" font-family="sans-serif" font-size="20" fill="#6b6257">放一张照片</text>''')

svg('photo-2.svg', '''
<rect x="40" y="40" width="320" height="220" rx="10" fill="#fff" stroke="#171310" stroke-width="5"/>
<text x="200" y="140" text-anchor="middle" font-family="sans-serif" font-size="46" fill="#171310">A</text>
<text x="200" y="220" text-anchor="middle" font-family="sans-serif" font-size="18" fill="#6b6257">一个入口 / 一张图</text>''')

svg('photo-3.svg', '''
<rect x="40" y="40" width="320" height="220" rx="10" fill="#fff" stroke="#171310" stroke-width="5"/>
<text x="200" y="140" text-anchor="middle" font-family="sans-serif" font-size="46" fill="#171310">B</text>
<text x="200" y="220" text-anchor="middle" font-family="sans-serif" font-size="18" fill="#6b6257">一个入口 / 一张图</text>''')

# 透明立牌占位
svg('figure-a.svg', '''
<g stroke="#171310" stroke-width="6" fill="#fff">
<circle cx="200" cy="90" r="38"/>
<path d="M200 128 L200 230 M200 155 L160 190 M200 155 L240 190 M200 230 L175 292 M200 230 L225 292" fill="none" stroke-linecap="round"/>
</g>
<circle cx="186" cy="86" r="5" fill="#171310"/><circle cx="214" cy="86" r="5" fill="#171310"/>
<path d="M188 104 Q200 112 212 104" fill="none" stroke="#171310" stroke-width="4" stroke-linecap="round"/>''', w=400, h=320, transparent=True)

svg('figure-b.svg', '''
<g stroke="#171310" stroke-width="6" fill="#fff">
<circle cx="200" cy="96" r="34"/>
<path d="M200 130 L200 226 M200 152 L165 182 M200 152 L235 182 M200 226 L178 286 M200 226 L222 286" fill="none" stroke-linecap="round"/>
<path d="M176 80 Q200 58 224 80" fill="none" stroke="#171310" stroke-width="6" stroke-linecap="round"/>
</g>
<circle cx="188" cy="92" r="4.5" fill="#171310"/><circle cx="212" cy="92" r="4.5" fill="#171310"/>
<path d="M191 108 Q200 114 209 108" fill="none" stroke="#171310" stroke-width="4" stroke-linecap="round"/>''', w=400, h=320, transparent=True)

svg('cover.svg', '''
<rect width="400" height="400" fill="#171310"/>
<circle cx="200" cy="200" r="120" fill="none" stroke="#f6eeda" stroke-width="10"/>
<circle cx="200" cy="200" r="24" fill="#ffd23f"/>
<text x="200" y="352" text-anchor="middle" font-family="sans-serif" font-size="24" fill="#f6eeda" letter-spacing="4">LOCAL</text>''', w=400, h=400)

labels = {
    'monitor': {'zh': '电脑 · 今日待办', 'en': 'Computer'},
    'keyboard': {'zh': '键盘 · 命令面板', 'en': 'Keyboard'},
    'mouse': {'zh': '鼠标', 'en': 'Mouse'},
    'pc': {'zh': '主机 · 在跑什么', 'en': 'PC tower'},
    'book': {'zh': '书 · 索引', 'en': 'Book'},
    'mug': {'zh': '茶盏 · 光糖动茶', 'en': 'Tea'},
    'pens': {'zh': '笔筒 · 写点什么', 'en': 'Pens'},
    'headphones': {'zh': '耳机 · 专注模式', 'en': 'Headphones'},
    'figure': {'zh': '立牌 · A', 'en': 'Figure'},
    'figure2': {'zh': '立牌 · B', 'en': 'Figure'},
    'speaker': {'zh': '音响 · 律动', 'en': 'Speaker'},
    'cd': {'zh': 'CD 机 · 本地歌单', 'en': 'CD player'},
    'tablet': {'zh': '平板 · 视频 & 游戏', 'en': 'Tablet'},
    'phone': {'zh': '手机 · 通知', 'en': 'Phone'},
    'controller': {'zh': '手柄 · 日常在看 & 游戏', 'en': 'Controller'},
    'glasses': {'zh': '眼镜 · 漫画滤镜', 'en': 'Glasses'},
    'window': {'zh': '窗户 · 索引页', 'en': 'Window'},
    'board': {'zh': '软木板 · 关于我', 'en': 'Board'},
    'notes': {'zh': '便签墙', 'en': 'Notes'},
    'poster': {'zh': '海报 · 图片索引', 'en': 'Poster'},
    'camera': {'zh': '相机 · 相册', 'en': 'Camera'},
    'plant': {'zh': '绿植 · 心情', 'en': 'Plant'},
    'lamp': {'zh': '台灯 · 暖光', 'en': 'Lamp'},
    'calendar': {'zh': '台历 · 节律', 'en': 'Calendar'},
    'contract': {'zh': '契约卷轴 · 今日契约', 'en': 'Contract'},
    'mora': {'zh': '摩拉 · 今日份', 'en': 'Mora'},
}

content = {
    'meta': {
        'owner': 'MY DESK',
        'brandSub': '我的本地工作台',
        'title': '我的本地工作台',
        'theme': 'liyue',
        'ticker': '✦ 点一点桌上的东西 ✦ 显示器是今天的 todo ✦ 卷轴是今日契约 ✦ 书是索引 ✦ 所有数据都在本机 ✦ 调度交给本地 agent ✦',
    },
    'window': {
        'mode': 'auto', 'city': '我的城市', 'sign': 'LOCAL DESK', 'lanterns': True,
        'dashboard': {'title': '索引 · 所有物件与链接', 'sub': '本地生成的 INDEX.html', 'url': '/INDEX.html'},
    },
    'arsenal': {'title': '索引 · 物件与链接', 'sub': '每个物件、每条链接、每个数据文件', 'url': '/INDEX.html'},
    'about': {
        'kicker': 'MY DESK',
        'name': '我',
        'boardTitle': ['我的', '工作台'],
        'role': '把散在各处的入口，收在一张桌子上',
        'lines': [
            '数据是本机的纯文本：JSONL、JSON、Markdown。平台不在了，桌面还在。',
            '界面只是索引：每个物件都指向一个真实位置——文件、页面、会话或命令。',
            '时钟不属于桌面。定时与判断交给本地 agent，桌面只负责把该看的东西摆出来。',
        ],
        'tags': ['本地数据', '链接索引', 'Agent 驱动', '可移植'],
        'chips': ['索引', '本地', 'Agent'],
        'polaroids': [
            {'file': 'assets/base/photo-1.svg', 'cap': '一个入口', 'pos': 'center', 'title': '入口 · 文件夹', 'note': '把最常用的文件夹钉在这里；改 data/links.json 就能换。', 'url': '', 'urlLabel': ''},
            {'file': 'assets/base/photo-2.svg', 'cap': '第二个入口', 'pos': 'center', 'title': '入口 · 网页', 'note': '一个链接就是一条路；本地版不绑定平台。', 'url': '', 'urlLabel': ''},
            {'file': 'assets/base/photo-3.svg', 'cap': '第三个入口', 'pos': 'center', 'title': '入口 · 会话', 'note': '本地 agent 的会话、笔记、项目页，都可以挂上来。', 'url': '', 'urlLabel': ''},
        ],
        'chipActs': [
            {'open': 'book', 'hint': '索引 → 书'},
            {'open': 'poster', 'hint': '图片索引 → 海报'},
            {'open': 'contract', 'hint': '今日契约 → 卷轴'},
        ],
    },
    'work': {
        'greeting': '今天只保一条线 👋',
        'progressLabel': '待办来自本机 data/todos.jsonl',
        'storageKey': 'local_desk_todos_v1',
        'todos': [
            {'id': 't1', 'text': '把最常用的三个入口写进 data/links.json', 'done': False, 'tag': '桌'},
            {'id': 't2', 'text': '跑一次 desk sync，让今天的待办出现', 'done': False, 'tag': '数据'},
            {'id': 't3', 'text': '把 desk serve 设成开机启动（可选）', 'done': False, 'tag': '安装'},
        ],
        'projects': [
            {'name': '桌面', 'progress': 100, 'color': '#14b8a6', 'note': '本地引擎已装好'},
            {'name': '索引', 'progress': 60, 'color': '#ffb020', 'note': '把入口一条条挂上来'},
        ],
    },
    'contract': {
        'title': '今日契约',
        'clauses': [
            {'k': '身', 'text': '先保物理层：吃饭、睡觉、走两步'},
            {'k': '心', 'text': '只保一条线，不开新口子'},
        ],
        'source': '我自己 · 本地',
        'note': '契约是提醒，不是新任务：这里不会替你确认、完成或对外承诺任何事。',
    },
    'music': {
        'album': {'title': '本地歌单', 'artist': '把 mp3 放进 app/assets/audio/', 'sub': '没有歌也能用', 'bpm': '0 首', 'cover': 'assets/base/cover.svg', 'url': ''},
        'songs': [],
    },
    'videos': {
        'sites': [
            {'name': 'Bilibili', 'desc': '视频入口', 'url': 'https://www.bilibili.com/', 'color': '#ff5fa2'},
            {'name': 'YouTube', 'desc': '视频入口', 'url': 'https://www.youtube.com/', 'color': '#ff3b3b'},
            {'name': '小红书', 'desc': '灵感与案例', 'url': 'https://www.xiaohongshu.com/', 'color': '#e5484d'},
        ],
        'recentTitle': '最近在看的', 'recent': [],
    },
    'watchlist': {'title': '日常在看', 'sub': '在 data/links.json 里加一条，就会出现在这里', 'items': []},
    'gamelib': {'title': '游戏库', 'sub': '本地版不内置；想放就加 links', 'from': '', 'groups': []},
    'books': [],
    'booksLink': '/INDEX.html',
    'booksLinkLabel': '打开索引页 ↗',
    'booksLink2': '',
    'booksLink2Label': '',
    'showcase': {
        'title': '图片索引', 'sub': '由 data/generated/gallery.json 生成',
        'stats': [{'n': 0, 'label': '本地图片', 'color': '#14b8a6'}],
        'works': [],
    },
    'notes': [
        {'text': '数据在本机，\n平台不在也还在。', 'color': '#ffd23f', 'rot': -3},
        {'text': '界面只是索引。', 'color': '#8ee6c8', 'rot': 2},
        {'text': '时钟交给\n本地 agent。', 'color': '#9ec5ff', 'rot': -2},
    ],
    'notesKey': 'local_desk_notes_v1',
    'notifications': [
        {'app': '桌面', 'icon': '🖥', 'text': '本地服务已启动：http://127.0.0.1:7777', 'time': '现在', 'color': '#14b8a6'},
        {'app': '数据', 'icon': '🗂', 'text': '所有内容都在 data/ 下，可直接编辑', 'time': '今天', 'color': '#2f6df6'},
        {'app': 'Agent', 'icon': '🤖', 'text': 'desk sync 会扫描本地 agent 记录', 'time': '今天', 'color': '#7c4dff'},
    ],
    'figures': [
        {'id': 'a', 'name': '立牌 A', 'series': '本地模板', 'story': '把透明立牌图放到 app/assets/me/，再把 data/content.local.json 里的 photo 指过去。', 'height': 'Q 版立牌', 'photo': 'assets/base/figure-a.svg', 'photoHint': '占位立牌', 'turn': 'assets/base/figure-a.svg', 'model3d': {'glb': ''}, 'link': '', 'linkLabel': '', 'actions': [{'group': '动作', 'items': [{'label': '站好', 'kind': 'img', 'src': 'assets/base/figure-a.svg', 'hint': '占位'}]}]},
        {'id': 'b', 'name': '立牌 B', 'series': '本地模板', 'story': '同上；这一格可以放另一个角色或另一张立牌。', 'height': 'Q 版立牌', 'photo': 'assets/base/figure-b.svg', 'photoHint': '占位立牌', 'turn': 'assets/base/figure-b.svg', 'model3d': {'glb': ''}, 'link': '', 'linkLabel': '', 'actions': [{'group': '动作', 'items': [{'label': '站好', 'kind': 'img', 'src': 'assets/base/figure-b.svg', 'hint': '占位'}]}]},
    ],
    'photos': [
        {'file': 'assets/base/photo-1.svg', 'cat': '模板', 'title': '放一张照片', 'loc': 'app/assets/me/'},
        {'file': 'assets/base/photo-2.svg', 'cat': '模板', 'title': '第二个入口', 'loc': 'data/links.json'},
        {'file': 'assets/base/photo-3.svg', 'cat': '模板', 'title': '第三个入口', 'loc': 'data/links.json'},
    ],
    'calendar': {'title': '固定节律', 'today': '今天的节律', 'events': [
        {'time': '09:00', 'text': '开机：看显示器，只保一条线', 'color': '#e5484d'},
        {'time': '14:00', 'text': '同步一次：desk sync', 'color': '#2f6df6'},
        {'time': '17:30', 'text': '收口：写一条便签，关桌面', 'color': '#ffb020'},
    ]},
    'plant': {'name': '绿植 · 一枝', 'line': '先保物理层。', 'moods': [
        '先跑通，再分叉。', '只保一条线。', '数据在本机，心就稳一点。', '今天份的摩拉，已经够用了。',
    ]},
    'lamp': {'caption': '暖光一开，房间就安静了。'},
    'mug': {'kicker': 'TEA · 茶盏', 'unit': '盏', 'storageKey': 'local_desk_tea_v1', 'lines': ['还没泡茶。', '茶刚刚好。', '再续一盏也无妨。', '该起身走两步了。']},
    'pc': {'name': 'LOCAL-DESK', 'parts': ['本机', 'data/', 'links', 'agent'], 'stats': [
        {'label': '专注', 'live': 'focus'}, {'label': '心情', 'live': 'mood'}, {'label': '茶温', 'live': 'tea'},
        {'label': '本地数据', 'value': 100, 'fixed': True}, {'label': '索引条目', 'value': 0, 'fixed': True},
    ], 'running': ['desk serve  127.0.0.1:7777', 'data/  纯文本', 'agent  本地', '时钟  agent 驱动']},
    'glasses': {'caption': '戴上眼镜，整个世界变成漫画。'},
    'update': {'title': '这张桌子怎么更新？', 'lines': [
        '所有内容在 data/：content.json（文案与结构）、links.json（入口）、notes.jsonl / todos.jsonl（账本）、schedule.json（交给 agent 的定时）。',
        '改完运行 desk build，刷新页面即可。',
        '页面里的勾选、便签、随手记、茶盏数、配色只存在你自己的浏览器。',
        '这张桌子只在本机跑：http://127.0.0.1:7777',
    ]},
    'labels': labels,
}

links = {
    'version': 1,
    'note': '一条链接 = 一个真实位置。type: folder | file | url | app | command。command 默认不允许执行。',
    'links': [
        {'id': 'inbox', 'label': '收件箱', 'group': '入口', 'type': 'folder', 'target': '~/Desktop', 'icon': '📥', 'note': '先改成一个你每天真的会打开的文件夹'},
        {'id': 'notes', 'label': '便签账本', 'group': '数据', 'type': 'file', 'target': 'data/notes.jsonl', 'icon': '🗒', 'note': 'append-only，可 diff'},
        {'id': 'todos', 'label': '待办账本', 'group': '数据', 'type': 'file', 'target': 'data/todos.jsonl', 'icon': '✅', 'note': 'append-only，可 diff'},
        {'id': 'links', 'label': '链接表', 'group': '数据', 'type': 'file', 'target': 'data/links.json', 'icon': '🔗', 'note': '这个索引的源头'},
        {'id': 'schedule', 'label': '定时清单', 'group': 'Agent', 'type': 'file', 'target': 'data/schedule.json', 'icon': '⏰', 'note': '只写 prompt，不装 cron'},
        {'id': 'claude', 'label': 'Claude Code', 'group': 'Agent', 'type': 'app', 'target': 'Claude', 'icon': '🤖', 'note': '本机装了才会打开'},
        {'id': 'codex', 'label': 'Codex', 'group': 'Agent', 'type': 'app', 'target': 'Codex', 'icon': '⌨', 'note': '本机装了才会打开'},
        {'id': 'readme', 'label': 'README', 'group': '文档', 'type': 'file', 'target': 'README.md', 'icon': '📖', 'note': '安装、结构、方法论'},
        {'id': 'method', 'label': '方法论', 'group': '文档', 'type': 'file', 'target': 'METHOD.md', 'icon': '🧭', 'note': '本地数据 + 链接索引 + agent 时钟'},
    ],
}

notes = [
    {'op': 'add', 'id': 'n-1', 'text': '数据在本机，\n平台不在也还在。', 'color': '#ffd23f', 'rot': -3, 'at': '2026-01-01T09:00:00+08:00', 'by': 'seed'},
    {'op': 'add', 'id': 'n-2', 'text': '界面只是索引。', 'color': '#8ee6c8', 'rot': 2, 'at': '2026-01-01T09:01:00+08:00', 'by': 'seed'},
    {'op': 'add', 'id': 'n-3', 'text': '时钟交给\n本地 agent。', 'color': '#9ec5ff', 'rot': -2, 'at': '2026-01-01T09:02:00+08:00', 'by': 'seed'},
]

todos = [
    {'op': 'add', 'id': 't-1', 'text': '把最常用的三个入口写进 data/links.json', 'tag': '桌', 'at': '2026-01-01T09:00:00+08:00', 'by': 'seed'},
    {'op': 'add', 'id': 't-2', 'text': '跑一次 desk sync，让今天的待办出现', 'tag': '数据', 'at': '2026-01-01T09:01:00+08:00', 'by': 'seed'},
]

schedule = {
    'version': 1,
    'note': '这里只写「什么时候该想什么」，不装 cron。真正的时钟是你本地的 agent（或系统的 launchd）。',
    'jobs': [
        {'id': 'morning', 'when': 'daily 09:00', 'agent': 'auto', 'prompt': '读一遍 data/links.json 和 data/generated/today.json，用三行告诉我：今天保哪条线、三个要拍的板、第一个 15 分钟动作。', 'output': 'data/generated/morning.md', 'enabled': True},
        {'id': 'evening', 'when': 'daily 17:30', 'agent': 'auto', 'prompt': '把今天在本地 agent 会话里发生的事压成五条，写进 data/digest/YYYY-MM-DD.md；没有新事就写「今天为零」。', 'output': 'data/digest/YYYY-MM-DD.md', 'enabled': True},
    ],
}

def dump(name, obj):
    p = os.path.join(ROOT, 'data', name)
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write('\n')

dump('content.json', content)
dump('links.json', links)
dump('schedule.json', schedule)

with open(os.path.join(ROOT, 'data', 'notes.jsonl'), 'w', encoding='utf-8') as f:
    for r in notes:
        f.write(json.dumps(r, ensure_ascii=False) + '\n')

with open(os.path.join(ROOT, 'data', 'todos.jsonl'), 'w', encoding='utf-8') as f:
    for r in todos:
        f.write(json.dumps(r, ensure_ascii=False) + '\n')

open(os.path.join(ROOT, 'data', 'content.local.json'), 'w', encoding='utf-8').write('{}\n')
print('seed written')
