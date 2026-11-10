# 索引 · 我的本地工作台

生成于 2026-11-10T21:46:56+08:00。数据在 `data/`，引擎在 `app/`。

## 物件

| id | 中文 | English |
|---|---|---|
| `monitor` | 电脑 · 今日待办 | Computer |
| `keyboard` | 键盘 · 命令面板 | Keyboard |
| `mouse` | 鼠标 | Mouse |
| `pc` | 主机 · 在跑什么 | PC tower |
| `book` | 书 · 索引 | Book |
| `mug` | 茶盏 · 光糖动茶 | Tea |
| `pens` | 笔筒 · 写点什么 | Pens |
| `headphones` | 耳机 · 专注模式 | Headphones |
| `figure` | 立牌 · A | Figure |
| `figure2` | 立牌 · B | Figure |
| `speaker` | 音响 · 律动 | Speaker |
| `cd` | CD 机 · 本地歌单 | CD player |
| `tablet` | 平板 · 视频 & 游戏 | Tablet |
| `phone` | 手机 · 通知 | Phone |
| `controller` | 手柄 · 日常在看 & 游戏 | Controller |
| `glasses` | 眼镜 · 漫画滤镜 | Glasses |
| `window` | 窗户 · 索引页 | Window |
| `board` | 软木板 · 关于我 | Board |
| `notes` | 便签墙 | Notes |
| `poster` | 海报 · 图片索引 | Poster |
| `camera` | 相机 · 相册 | Camera |
| `plant` | 绿植 · 心情 | Plant |
| `lamp` | 台灯 · 暖光 | Lamp |
| `calendar` | 台历 · 节律 | Calendar |
| `contract` | 契约卷轴 · 今日契约 | Contract |
| `mora` | 摩拉 · 今日份 | Mora |

## 链接

| 名称 | 分组 | 类型 | 指向 |
|---|---|---|---|
| 收件箱 | 入口 | `folder` | `~/Desktop` |
| 便签账本 | 数据 | `file` | `data/notes.jsonl` |
| 待办账本 | 数据 | `file` | `data/todos.jsonl` |
| 链接表 | 数据 | `file` | `data/links.json` |
| 定时清单 | Agent | `file` | `data/schedule.json` |
| Claude Code | Agent | `app` | `Claude` |
| Codex | Agent | `app` | `Codex` |
| README | 文档 | `file` | `README.md` |
| 方法论 | 文档 | `file` | `METHOD.md` |

## 交给 agent 的定时

| id | when | prompt | output |
|---|---|---|---|
| `morning` | daily 09:00 | 读一遍 data/links.json 和 data/generated/today.json，用三行告诉我：今天保哪条线、三个要拍的板、第一个 15 分钟动作。 | `data/generated/morning.md` |
| `evening` | daily 17:30 | 把今天在本地 agent 会话里发生的事压成五条，写进 data/digest/YYYY-MM-DD.md；没有新事就写「今天为零」。 | `data/digest/YYYY-MM-DD.md` |
