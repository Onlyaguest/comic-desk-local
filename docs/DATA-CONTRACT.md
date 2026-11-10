# 数据契约 · desk.v1

这张桌子只认下面这些文件。换一个数据来源，只要还产出同样的形状，桌面不用改。

## 1. `data/content.json`

桌面上所有「内容」。键与 `app/js/data.js` 对应：

| 键 | 用途 |
|---|---|
| `meta` | 标题、owner、默认配色、底部字幕 |
| `window` | 昼夜默认、窗角招牌、点窗户的看板 |
| `arsenal` | 软木板上的「索引」卡 |
| `about` | 关于、三张拍立得、三张标签贴 |
| `work` | 显示器面板的种子待办与项目进度 |
| `contract` | 今日契约 |
| `music` | 本地歌单；`songs[].file` 指向 `app/assets/audio/` |
| `videos` | 平板里的站点与最近在看 |
| `watchlist` | 手柄里的「日常在看」 |
| `gamelib` | 手柄里的游戏库 |
| `books` | 书面板；`link` 可以是 `/api/open?id=` |
| `showcase` | 海报里的 Works 橱窗 |
| `notes` | 便签墙的种子 |
| `notifications` | 手机通知 |
| `figures` | 两个立牌；`photo` 指向图片 |
| `photos` | 相册占位 |
| `calendar` | 台历节律 |
| `plant` / `lamp` / `mug` / `pc` / `glasses` / `update` | 小物件面板 |
| `labels` | 物件悬停标签与命令面板条目 |

`data/content.local.json` 会**深合并**覆盖同名键。个人内容放这里，模板保持干净。

## 2. `data/notes.jsonl`

每行一个动作，只追加：

```json
{"op":"add","id":"n-1","text":"先跑通","color":"#ffd23f","rot":-3,"at":"2026-01-01T09:00:00+08:00","by":"seed"}
{"op":"edit","id":"n-1","text":"先跑通，再分叉","at":"..."}
{"op":"del","id":"n-1","reason":"在桌上撕掉","at":"..."}
{"op":"restore","id":"n-1","at":"..."}
```

当前板子由 `lib/desk/store.py` 回放得出。`board` 按 `born` 倒序；`archive` 是被撕掉的。

## 3. `data/todos.jsonl`

```json
{"op":"add","id":"t-1","text":"整理索引","tag":"桌","day":"2026-11-09","by":"page","at":"..."}
{"op":"done","id":"t-1","at":"..."}
{"op":"reopen","id":"t-1","at":"..."}
{"op":"drop","id":"t-1","reason":"不做了","at":"..."}
{"op":"edit","id":"t-1","text":"改成这样","at":"..."}
```

`kind` 可以是 `manual` 或 `session`。`session` 项额外带 `session` / `url` / `status` / `asks` / `first` / `last`。

回放结果：

```json
{
  "today": "2026-11-09",
  "today_open": [],
  "carry": [],
  "done_today": [],
  "dropped": [],
  "counts": {"open":0,"done":0,"carry":0,"dropped":0}
}
```

## 4. `data/generated/today.json`

```json
{
  "date": "2026-11-09",
  "generatedAt": "2026-11-09T11:39:00+08:00",
  "items": [
    {
      "id": "sess-1",
      "source": "claude",
      "space": "本地",
      "session": "帮我把桌面索引整理一下",
      "ask": "再把 notes 里那条旧的删掉",
      "asks": 2,
      "first": "09:12",
      "last": "10:05",
      "status": "replied",
      "url": ""
    }
  ],
  "stats": {"running":0,"replied":1,"cancelled":0,"error":0,"spaces":1,"auto":0}
}
```

`status` 只有三种：`running`（最后一次是用户说、agent 还没回）、`replied`（agent 回过）、`error`。

## 5. `data/generated/gallery.json`

```json
[
  {"url":"/media?path=/Users/me/Pictures/a.png","title":"a","created":"2026-11-09T10:00:00+08:00","src":"gallery","bytes":12345}
]
```

`url` 由本机服务 `/media` 提供，不复制文件。

## 6. `data/generated/sessions.json`

```json
{"2026-11-09":{"id":"sess-1","title":"帮我把桌面索引整理一下","source":"claude"}}
```

## 7. `data/schedule.json`

```json
{
  "jobs": [
    {
      "id": "morning",
      "when": "daily 09:00",
      "agent": "auto",
      "prompt": "读 data/generated/today.json，用三行告诉我今天保哪条线。",
      "output": "data/generated/morning.md",
      "enabled": true
    }
  ]
}
```

`when` 支持：

- `daily HH:MM`
- `every Nm`
- 其他写法：只在从未跑过时提醒一次

真正的执行不在这里，见 [SCHEDULE.md](SCHEDULE.md)。

## 8. `data/config.json`

```json
{
  "agent": "auto",
  "transcriptRoots": [],
  "galleryDirs": ["data/uploads"],
  "uploadDirs": ["data/uploads"]
}
```

`transcriptRoots` 为空时默认扫 `~/.claude/projects` 与 `~/.codex/sessions`。

## 9. 生成物

`desk build` 会写：

- `app/js/data.js`
- `app/js/today.js`
- `app/js/gallery.js`
- `app/js/uploads.js`
- `app/js/daily-sessions.js`
- `app/js/notes-board.js`
- `app/js/todos-board.js`
- `app/js/digest.js` / `digest-versions.js`
- `app/INDEX.html`
- `INDEX.md`

这些文件都可以随时删掉重建；不要手改。
