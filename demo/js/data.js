/* 自动生成：desk build —— 内容来自 data/content.json + data/content.local.json */
(function () {
  window.DESK_DATA = {
  "meta": {
    "owner": "MY DESK",
    "brandSub": "我的本地工作台",
    "title": "我的本地工作台",
    "theme": "liyue",
    "ticker": "✦ 点一点桌上的东西 ✦ 显示器是今天的 todo ✦ 卷轴是今日契约 ✦ 书是索引 ✦ 所有数据都在本机 ✦ 调度交给本地 agent ✦"
  },
  "window": {
    "mode": "auto",
    "city": "我的城市",
    "sign": "LOCAL DESK",
    "lanterns": true,
    "dashboard": {
      "title": "索引 · 所有物件与链接",
      "sub": "本地生成的 catalog.html",
      "url": "/catalog.html"
    }
  },
  "arsenal": {
    "title": "索引 · 物件与链接",
    "sub": "每个物件、每条链接、每个数据文件",
    "url": "/catalog.html"
  },
  "about": {
    "kicker": "MY DESK",
    "name": "我",
    "boardTitle": [
      "我的",
      "工作台"
    ],
    "role": "把散在各处的入口，收在一张桌子上",
    "lines": [
      "数据是本机的纯文本：JSONL、JSON、Markdown。平台不在了，桌面还在。",
      "界面只是索引：每个物件都指向一个真实位置——文件、页面、会话或命令。",
      "时钟不属于桌面。定时与判断交给本地 agent，桌面只负责把该看的东西摆出来。"
    ],
    "tags": [
      "本地数据",
      "链接索引",
      "Agent 驱动",
      "可移植"
    ],
    "chips": [
      "索引",
      "本地",
      "Agent"
    ],
    "polaroids": [
      {
        "file": "assets/base/photo-1.svg",
        "cap": "一个入口",
        "pos": "center",
        "title": "入口 · 文件夹",
        "note": "把最常用的文件夹钉在这里；改 data/links.json 就能换。",
        "url": "",
        "urlLabel": ""
      },
      {
        "file": "assets/base/photo-2.svg",
        "cap": "第二个入口",
        "pos": "center",
        "title": "入口 · 网页",
        "note": "一个链接就是一条路；本地版不绑定平台。",
        "url": "",
        "urlLabel": ""
      },
      {
        "file": "assets/base/photo-3.svg",
        "cap": "第三个入口",
        "pos": "center",
        "title": "入口 · 会话",
        "note": "本地 agent 的会话、笔记、项目页，都可以挂上来。",
        "url": "",
        "urlLabel": ""
      }
    ],
    "chipActs": [
      {
        "open": "book",
        "hint": "索引 → 书"
      },
      {
        "open": "poster",
        "hint": "图片索引 → 海报"
      },
      {
        "open": "contract",
        "hint": "今日契约 → 卷轴"
      }
    ]
  },
  "work": {
    "greeting": "今天只保一条线 👋",
    "progressLabel": "待办来自本机 data/todos.jsonl",
    "storageKey": "local_desk_todos_v1",
    "todos": [
      {
        "id": "t1",
        "text": "把最常用的三个入口写进 data/links.json",
        "done": false,
        "tag": "桌"
      },
      {
        "id": "t2",
        "text": "跑一次 desk sync，让今天的待办出现",
        "done": false,
        "tag": "数据"
      },
      {
        "id": "t3",
        "text": "把 desk serve 设成开机启动（可选）",
        "done": false,
        "tag": "安装"
      }
    ],
    "projects": [
      {
        "name": "桌面",
        "progress": 100,
        "color": "#14b8a6",
        "note": "本地引擎已装好"
      },
      {
        "name": "索引",
        "progress": 60,
        "color": "#ffb020",
        "note": "把入口一条条挂上来"
      }
    ]
  },
  "contract": {
    "title": "今日契约",
    "clauses": [
      {
        "k": "身",
        "text": "先保物理层：吃饭、睡觉、走两步"
      },
      {
        "k": "心",
        "text": "只保一条线，不开新口子"
      }
    ],
    "source": "我自己 · 本地",
    "note": "契约是提醒，不是新任务：这里不会替你确认、完成或对外承诺任何事。"
  },
  "music": {
    "album": {
      "title": "本地歌单",
      "artist": "把 mp3 放进 app/assets/audio/",
      "sub": "没有歌也能用",
      "bpm": "0 首",
      "cover": "assets/base/cover.svg",
      "url": ""
    },
    "songs": []
  },
  "videos": {
    "sites": [
      {
        "name": "Bilibili",
        "desc": "视频入口",
        "url": "https://www.bilibili.com/",
        "color": "#ff5fa2"
      },
      {
        "name": "YouTube",
        "desc": "视频入口",
        "url": "https://www.youtube.com/",
        "color": "#ff3b3b"
      },
      {
        "name": "小红书",
        "desc": "灵感与案例",
        "url": "https://www.xiaohongshu.com/",
        "color": "#e5484d"
      }
    ],
    "recentTitle": "最近在看的",
    "recent": []
  },
  "watchlist": {
    "title": "日常在看",
    "sub": "在 data/links.json 里加一条，就会出现在这里",
    "items": [
      {
        "icon": "📥",
        "title": "收件箱",
        "note": "先改成一个你每天真的会打开的文件夹",
        "tag": "入口",
        "color": "#14b8a6",
        "url": "./api/open?id=inbox"
      },
      {
        "icon": "🗒",
        "title": "便签账本",
        "note": "append-only，可 diff",
        "tag": "数据",
        "color": "#14b8a6",
        "url": "./api/open?id=notes"
      },
      {
        "icon": "✅",
        "title": "待办账本",
        "note": "append-only，可 diff",
        "tag": "数据",
        "color": "#14b8a6",
        "url": "./api/open?id=todos"
      },
      {
        "icon": "🔗",
        "title": "链接表",
        "note": "这个索引的源头",
        "tag": "数据",
        "color": "#14b8a6",
        "url": "./api/open?id=links"
      },
      {
        "icon": "⏰",
        "title": "定时清单",
        "note": "只写 prompt，不装 cron",
        "tag": "Agent",
        "color": "#14b8a6",
        "url": "./api/open?id=schedule"
      },
      {
        "icon": "🤖",
        "title": "Claude Code",
        "note": "本机装了才会打开",
        "tag": "Agent",
        "color": "#14b8a6",
        "url": "./api/open?id=claude"
      },
      {
        "icon": "⌨",
        "title": "Codex",
        "note": "本机装了才会打开",
        "tag": "Agent",
        "color": "#14b8a6",
        "url": "./api/open?id=codex"
      },
      {
        "icon": "📖",
        "title": "README",
        "note": "安装、结构、方法论",
        "tag": "文档",
        "color": "#14b8a6",
        "url": "./api/open?id=readme"
      },
      {
        "icon": "🧭",
        "title": "方法论",
        "note": "本地数据 + 链接索引 + agent 时钟",
        "tag": "文档",
        "color": "#14b8a6",
        "url": "./api/open?id=method"
      }
    ]
  },
  "gamelib": {
    "title": "游戏库",
    "sub": "本地版不内置；想放就加 links",
    "from": "",
    "groups": []
  },
  "books": [
    {
      "title": "收件箱",
      "author": "入口",
      "progress": null,
      "color": "#14b8a6",
      "note": "先改成一个你每天真的会打开的文件夹",
      "link": "./api/open?id=inbox"
    },
    {
      "title": "便签账本",
      "author": "数据",
      "progress": null,
      "color": "#ffb020",
      "note": "append-only，可 diff",
      "link": "./api/open?id=notes"
    },
    {
      "title": "待办账本",
      "author": "数据",
      "progress": null,
      "color": "#7c4dff",
      "note": "append-only，可 diff",
      "link": "./api/open?id=todos"
    },
    {
      "title": "链接表",
      "author": "数据",
      "progress": null,
      "color": "#e5484d",
      "note": "这个索引的源头",
      "link": "./api/open?id=links"
    },
    {
      "title": "定时清单",
      "author": "Agent",
      "progress": null,
      "color": "#2f6df6",
      "note": "只写 prompt，不装 cron",
      "link": "./api/open?id=schedule"
    },
    {
      "title": "Claude Code",
      "author": "Agent",
      "progress": null,
      "color": "#14b8a6",
      "note": "本机装了才会打开",
      "link": "./api/open?id=claude"
    },
    {
      "title": "Codex",
      "author": "Agent",
      "progress": null,
      "color": "#ffb020",
      "note": "本机装了才会打开",
      "link": "./api/open?id=codex"
    },
    {
      "title": "README",
      "author": "文档",
      "progress": null,
      "color": "#7c4dff",
      "note": "安装、结构、方法论",
      "link": "./api/open?id=readme"
    },
    {
      "title": "方法论",
      "author": "文档",
      "progress": null,
      "color": "#e5484d",
      "note": "本地数据 + 链接索引 + agent 时钟",
      "link": "./api/open?id=method"
    }
  ],
  "booksLink": "/catalog.html",
  "booksLinkLabel": "打开索引页 ↗",
  "booksLink2": "",
  "booksLink2Label": "",
  "showcase": {
    "title": "图片索引",
    "sub": "由 data/generated/gallery.json 生成",
    "stats": [
      {
        "n": 0,
        "label": "本地图片",
        "color": "#14b8a6"
      }
    ],
    "works": [
      {
        "title": "收件箱",
        "tag": "入口",
        "color": "#171310",
        "icon": "📥",
        "slug": "inbox"
      },
      {
        "title": "便签账本",
        "tag": "数据",
        "color": "#171310",
        "icon": "🗒",
        "slug": "notes"
      },
      {
        "title": "待办账本",
        "tag": "数据",
        "color": "#171310",
        "icon": "✅",
        "slug": "todos"
      },
      {
        "title": "链接表",
        "tag": "数据",
        "color": "#171310",
        "icon": "🔗",
        "slug": "links"
      },
      {
        "title": "定时清单",
        "tag": "Agent",
        "color": "#171310",
        "icon": "⏰",
        "slug": "schedule"
      },
      {
        "title": "Claude Code",
        "tag": "Agent",
        "color": "#171310",
        "icon": "🤖",
        "slug": "claude"
      },
      {
        "title": "Codex",
        "tag": "Agent",
        "color": "#171310",
        "icon": "⌨",
        "slug": "codex"
      },
      {
        "title": "README",
        "tag": "文档",
        "color": "#171310",
        "icon": "📖",
        "slug": "readme"
      },
      {
        "title": "方法论",
        "tag": "文档",
        "color": "#171310",
        "icon": "🧭",
        "slug": "method"
      }
    ]
  },
  "notes": [
    {
      "text": "数据在本机，\n平台不在也还在。",
      "color": "#ffd23f",
      "rot": -3
    },
    {
      "text": "界面只是索引。",
      "color": "#8ee6c8",
      "rot": 2
    },
    {
      "text": "时钟交给\n本地 agent。",
      "color": "#9ec5ff",
      "rot": -2
    }
  ],
  "notesKey": "local_desk_notes_v1",
  "notifications": [
    {
      "app": "桌面",
      "icon": "🖥",
      "text": "本地服务已启动：http://127.0.0.1:7777",
      "time": "现在",
      "color": "#14b8a6"
    },
    {
      "app": "数据",
      "icon": "🗂",
      "text": "所有内容都在 data/ 下，可直接编辑",
      "time": "今天",
      "color": "#2f6df6"
    },
    {
      "app": "Agent",
      "icon": "🤖",
      "text": "desk sync 会扫描本地 agent 记录",
      "time": "今天",
      "color": "#7c4dff"
    }
  ],
  "figures": [
    {
      "id": "a",
      "name": "立牌 A",
      "series": "本地模板",
      "story": "把透明立牌图放到 app/assets/me/，再把 data/content.local.json 里的 photo 指过去。",
      "height": "Q 版立牌",
      "photo": "assets/base/figure-a.svg",
      "photoHint": "占位立牌",
      "turn": "assets/base/figure-a.svg",
      "model3d": {
        "glb": ""
      },
      "link": "",
      "linkLabel": "",
      "actions": [
        {
          "group": "动作",
          "items": [
            {
              "label": "站好",
              "kind": "img",
              "src": "assets/base/figure-a.svg",
              "hint": "占位"
            }
          ]
        }
      ]
    },
    {
      "id": "b",
      "name": "立牌 B",
      "series": "本地模板",
      "story": "同上；这一格可以放另一个角色或另一张立牌。",
      "height": "Q 版立牌",
      "photo": "assets/base/figure-b.svg",
      "photoHint": "占位立牌",
      "turn": "assets/base/figure-b.svg",
      "model3d": {
        "glb": ""
      },
      "link": "",
      "linkLabel": "",
      "actions": [
        {
          "group": "动作",
          "items": [
            {
              "label": "站好",
              "kind": "img",
              "src": "assets/base/figure-b.svg",
              "hint": "占位"
            }
          ]
        }
      ]
    }
  ],
  "photos": [
    {
      "file": "assets/base/photo-1.svg",
      "cat": "模板",
      "title": "放一张照片",
      "loc": "app/assets/me/"
    },
    {
      "file": "assets/base/photo-2.svg",
      "cat": "模板",
      "title": "第二个入口",
      "loc": "data/links.json"
    },
    {
      "file": "assets/base/photo-3.svg",
      "cat": "模板",
      "title": "第三个入口",
      "loc": "data/links.json"
    }
  ],
  "calendar": {
    "title": "固定节律",
    "today": "今天的节律",
    "events": [
      {
        "time": "09:00",
        "text": "开机：看显示器，只保一条线",
        "color": "#e5484d"
      },
      {
        "time": "14:00",
        "text": "同步一次：desk sync",
        "color": "#2f6df6"
      },
      {
        "time": "17:30",
        "text": "收口：写一条便签，关桌面",
        "color": "#ffb020"
      }
    ]
  },
  "plant": {
    "name": "绿植 · 一枝",
    "line": "先保物理层。",
    "moods": [
      "先跑通，再分叉。",
      "只保一条线。",
      "数据在本机，心就稳一点。",
      "今天份的摩拉，已经够用了。"
    ]
  },
  "lamp": {
    "caption": "暖光一开，房间就安静了。"
  },
  "mug": {
    "kicker": "TEA · 茶盏",
    "unit": "盏",
    "storageKey": "local_desk_tea_v1",
    "lines": [
      "还没泡茶。",
      "茶刚刚好。",
      "再续一盏也无妨。",
      "该起身走两步了。"
    ]
  },
  "pc": {
    "name": "LOCAL-DESK",
    "parts": [
      "本机",
      "data/",
      "links",
      "agent"
    ],
    "stats": [
      {
        "label": "专注",
        "live": "focus"
      },
      {
        "label": "心情",
        "live": "mood"
      },
      {
        "label": "茶温",
        "live": "tea"
      },
      {
        "label": "本地数据",
        "value": 100,
        "fixed": true
      },
      {
        "label": "索引条目",
        "value": 9,
        "fixed": true
      }
    ],
    "running": [
      "desk serve  127.0.0.1:7777",
      "data/  纯文本",
      "agent  本地",
      "时钟  agent 驱动"
    ]
  },
  "glasses": {
    "caption": "戴上眼镜，整个世界变成漫画。"
  },
  "update": {
    "title": "这张桌子怎么更新？",
    "lines": [
      "所有内容在 data/：content.json（文案与结构）、links.json（入口）、notes.jsonl / todos.jsonl（账本）、schedule.json（交给 agent 的定时）。",
      "改完运行 desk build，刷新页面即可。",
      "勾选和便签写入本机账本；配色等外观偏好保存在浏览器。",
      "这张桌子只在本机跑：http://127.0.0.1:7777"
    ]
  },
  "labels": {
    "monitor": {
      "zh": "电脑 · 今日待办",
      "en": "Computer"
    },
    "keyboard": {
      "zh": "键盘 · 命令面板",
      "en": "Keyboard"
    },
    "mouse": {
      "zh": "鼠标",
      "en": "Mouse"
    },
    "pc": {
      "zh": "主机 · 在跑什么",
      "en": "PC tower"
    },
    "book": {
      "zh": "书 · 索引",
      "en": "Book"
    },
    "mug": {
      "zh": "茶盏 · 光糖动茶",
      "en": "Tea"
    },
    "pens": {
      "zh": "笔筒 · 写点什么",
      "en": "Pens"
    },
    "headphones": {
      "zh": "耳机 · 专注模式",
      "en": "Headphones"
    },
    "figure": {
      "zh": "立牌 · A",
      "en": "Figure"
    },
    "figure2": {
      "zh": "立牌 · B",
      "en": "Figure"
    },
    "speaker": {
      "zh": "音响 · 律动",
      "en": "Speaker"
    },
    "cd": {
      "zh": "CD 机 · 本地歌单",
      "en": "CD player"
    },
    "tablet": {
      "zh": "平板 · 视频 & 游戏",
      "en": "Tablet"
    },
    "phone": {
      "zh": "手机 · 通知",
      "en": "Phone"
    },
    "controller": {
      "zh": "手柄 · 日常在看 & 游戏",
      "en": "Controller"
    },
    "glasses": {
      "zh": "眼镜 · 漫画滤镜",
      "en": "Glasses"
    },
    "window": {
      "zh": "窗户 · 索引页",
      "en": "Window"
    },
    "board": {
      "zh": "软木板 · 关于我",
      "en": "Board"
    },
    "notes": {
      "zh": "便签墙",
      "en": "Notes"
    },
    "poster": {
      "zh": "海报 · 图片索引",
      "en": "Poster"
    },
    "camera": {
      "zh": "相机 · 相册",
      "en": "Camera"
    },
    "plant": {
      "zh": "绿植 · 心情",
      "en": "Plant"
    },
    "lamp": {
      "zh": "台灯 · 暖光",
      "en": "Lamp"
    },
    "calendar": {
      "zh": "台历 · 节律",
      "en": "Calendar"
    },
    "contract": {
      "zh": "契约卷轴 · 今日契约",
      "en": "Contract"
    },
    "mora": {
      "zh": "摩拉 · 今日份",
      "en": "Mora"
    }
  }
};
  window.DESK_DATA.showcase.link = function (slug) {
    return /^https?:/.test(slug) ? slug : './api/open?id=' + encodeURIComponent(slug);
  };
  window.DESK_LABELS = {
  "monitor": {
    "zh": "电脑 · 今日待办",
    "en": "Computer"
  },
  "keyboard": {
    "zh": "键盘 · 命令面板",
    "en": "Keyboard"
  },
  "mouse": {
    "zh": "鼠标",
    "en": "Mouse"
  },
  "pc": {
    "zh": "主机 · 在跑什么",
    "en": "PC tower"
  },
  "book": {
    "zh": "书 · 索引",
    "en": "Book"
  },
  "mug": {
    "zh": "茶盏 · 光糖动茶",
    "en": "Tea"
  },
  "pens": {
    "zh": "笔筒 · 写点什么",
    "en": "Pens"
  },
  "headphones": {
    "zh": "耳机 · 专注模式",
    "en": "Headphones"
  },
  "figure": {
    "zh": "立牌 · A",
    "en": "Figure"
  },
  "figure2": {
    "zh": "立牌 · B",
    "en": "Figure"
  },
  "speaker": {
    "zh": "音响 · 律动",
    "en": "Speaker"
  },
  "cd": {
    "zh": "CD 机 · 本地歌单",
    "en": "CD player"
  },
  "tablet": {
    "zh": "平板 · 视频 & 游戏",
    "en": "Tablet"
  },
  "phone": {
    "zh": "手机 · 通知",
    "en": "Phone"
  },
  "controller": {
    "zh": "手柄 · 日常在看 & 游戏",
    "en": "Controller"
  },
  "glasses": {
    "zh": "眼镜 · 漫画滤镜",
    "en": "Glasses"
  },
  "window": {
    "zh": "窗户 · 索引页",
    "en": "Window"
  },
  "board": {
    "zh": "软木板 · 关于我",
    "en": "Board"
  },
  "notes": {
    "zh": "便签墙",
    "en": "Notes"
  },
  "poster": {
    "zh": "海报 · 图片索引",
    "en": "Poster"
  },
  "camera": {
    "zh": "相机 · 相册",
    "en": "Camera"
  },
  "plant": {
    "zh": "绿植 · 心情",
    "en": "Plant"
  },
  "lamp": {
    "zh": "台灯 · 暖光",
    "en": "Lamp"
  },
  "calendar": {
    "zh": "台历 · 节律",
    "en": "Calendar"
  },
  "contract": {
    "zh": "契约卷轴 · 今日契约",
    "en": "Contract"
  },
  "mora": {
    "zh": "摩拉 · 今日份",
    "en": "Mora"
  }
};
})();
