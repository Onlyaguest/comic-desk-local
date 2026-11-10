# 我的本地工作台 · Local Desk

一张彩色漫画风的工作桌面，装在你自己的 Mac 上。

**数据全在本机，物件全是索引，时钟交给本地 agent。**

这个版本抽象自一张彩色漫画工作台——原版跑在 Cohub 上，靠平台会话、App Action 和 SpaceView 链接驱动。本地版把那些脐带剪掉，换成：

- `data/` 里的纯文本（JSON / JSONL / Markdown）
- `data/links.json` 里的一条条真实入口
- 你本机 Claude Code / Codex 的会话记录

---

## 30 秒装上（macOS）

1. 把整个文件夹解压到一个你记得住的地方，比如 `~/ComicDesk`。
2. 双击 **`install.command`**。
   - 如果 macOS 提示「无法打开，因为来自身份不明的开发者」：右键 → 打开 → 再点「打开」。
   - 或者打开终端，运行 `bash install.command`。
3. 安装完它会问你要不要现在启动；选 Y。
4. 浏览器打开 **http://127.0.0.1:7777**

以后启动：双击 **`start.command`**，或终端运行 `desk serve`。

> 需要 Python 3.9+。macOS 自带；没有就 `xcode-select --install`，或从 python.org 装一个。

第一次用，先跑一次：

```bash
desk sync      # 扫描本机 Claude Code / Codex 的会话与本地图片
desk serve     # 打开桌面
```

给接手的 agent：先读 [HANDOFF.md](HANDOFF.md)，再跑 `bash verify.sh`。

---

## 第一次打开你会看到

| 物件 | 它是什么 |
|---|---|
| 显示器 | 今天你在本地 agent 里发起的事，按会话分组，带状态 |
| 便签墙 | `data/notes.jsonl` 的只追加回放，点着就能改字 |
| 契约卷轴 | `data/content.json` 里的今日契约 |
| 书 | 索引：`data/links.json` 的每一条入口 |
| 海报 | 本地图片索引（`data/generated/gallery.json`） |
| 相机 | 最近上传 / 放进 `data/uploads` 的图片 |
| 窗户 | 内嵌 `INDEX.html`，所有物件与链接的总表 |
| 键盘 / `/` | 命令面板 |
| 眼镜 | 漫画滤镜 |
| 台灯 / 窗户 | 昼夜与暖光 |

所有面板、动画、小游戏、投影仪都还在；它们只依赖浏览器和本机文件。

---

## 只改三个文件

| 文件 | 管什么 |
|---|---|
| `data/content.json` | 文案、颜色主题、契约、书、通知、手办、节律——桌面上所有「内容」 |
| `data/links.json` | 所有入口：文件夹、文件、网页、App、命令 |
| `data/schedule.json` | 交给本地 agent 的定时 prompt 清单 |

改完运行：

```bash
desk build     # 把 data/ 编译成页面快照
```

刷新页面即可。想保留自己的改动又不想动模板，把差异写进 `data/content.local.json`（会覆盖 `content.json` 的同名键）。

---

## 可以保留的（从原版直接搬过来）

| 部分 | 状态 | 说明 |
|---|---|---|
| 2D 舞台、CSS、26 个物件 | ✅ 原样 | 纯静态、零构建，`app/` 下即是 |
| 面板、命令面板、小游戏 | ✅ 原样 | 只改了「写数据」那三个动作的调用 |
| 投影仪 / 黑板页 | ✅ 原样 | 片单换成了本地版 |
| 便签 / 待办账本 | ✅ 原样格式 | append-only JSONL，可直接 diff |
| localStorage 状态 | ✅ 原样 | 键都带 `local_` / `yz_desk_` 前缀，不串 |
| 3D 桌面（旧版） | ✅ 原样 | `app/desk3d.html`，命令面板里进 |
| 个人素材（照片/手办/歌） | ⚠️ 未带 | 放到 `app/assets/me/`，在 `content.local.json` 里指过去 |

## 必须重写的（原版的 Cohub 脐带）

| 原版 | 本地版 |
|---|---|
| `sync-today.py` 读 `cohub me sessions` | `adapters.py` 读 Claude Code / Codex 的 JSONL |
| `sync-gallery.py` / `sync-uploads.py` | 扫本地目录（`config.json` 可配） |
| `sync-daily-sessions.py` | 从本地 transcript 生成 |
| App Action `notes/todos/refresh-today/daily-digest` | 本机 `/api/action` + `lib/desk/actions.py` |
| Cohub SDK / App Action 轮询 | `app/js/local-api.js` 一个 `fetch` |
| `session.turn.finalized` 钩子 | 本地 agent 钩子 / launchd（见 `docs/SCHEDULE.md`） |
| `cohub.run` / SpaceView 链接 | `data/links.json` + `/api/open` |

## 没有搬的

- 每日一首歌、音色烘焙、微信群多 agent：依赖平台能力，搬走会变成空壳或持续烧钱。
- 001 数据看板、3D 微缩工作室：依赖账号层数据与另一个 App。
- 原版的个人照片、手办、歌单：没有随包发布；用 `desk import --with-assets` 从旧目录导入。

---

## 接上你本地的 agent

先看看本机有什么：

```bash
desk doctor
```

它会告诉你：

- 有没有装 `claude` / `codex` 命令
- 有没有 `~/.claude/projects` / `~/.codex/sessions`，各有多少份 transcript
- `data/` 是否齐全

然后：

```bash
desk sync                 # 把今天的会话读成 data/generated/today.json
desk ask "帮我把今天的索引整理一下"   # 派给本地 agent（会花额度，先加 --yes）
desk schedule             # 看 schedule.json 里哪些到点了
desk schedule --run       # 真跑（同样花额度）
desk digest               # 打印今天的日结 prompt
desk digest --run         # 交给 agent 写 data/digest/YYYY-MM-DD.md
```

`desk ask` 和 `desk schedule --run` 默认都不执行，必须显式加 `--run` / `--yes`，因为每一次都花你的额度。

---

## 索引：这个桌面最核心的一层

`data/links.json` 是唯一的入口表。一条链接长这样：

```json
{
  "id": "inbox",
  "label": "收件箱",
  "group": "入口",
  "type": "folder",
  "target": "~/Desktop",
  "icon": "📥",
  "note": "每天真的会打开的那个文件夹"
}
```

`type` 支持：

| type | 行为 |
|---|---|
| `folder` / `file` | 用系统默认方式打开；相对路径按桌面根目录解析 |
| `url` | 浏览器打开 |
| `app` | `open -a <名字>` |
| `command` | 默认**不执行**；要给这条加 `"allowCommand": true` |

生成总表：

```bash
desk index     # 写 INDEX.md 和 app/INDEX.html
```

桌面里的「书」「海报」「手柄」「窗户」都是这张表的视图——不是四份数据，是同一个索引入口。

---

## 目录

```
comic-desk-local/
├─ install.command / start.command / uninstall.command
├─ bin/desk                 命令行
├─ app/                     桌面本体（纯静态）
│  ├─ index.html
│  ├─ css/  js/  assets/
│  └─ INDEX.html            desk build 生成
├─ data/                    你的数据
│  ├─ content.json          内容
│  ├─ content.local.json    个人覆盖层
│  ├─ links.json            入口
│  ├─ schedule.json         交给 agent 的定时
│  ├─ notes.jsonl           便签账本
│  ├─ todos.jsonl           待办账本
│  ├─ digest/               日结
│  ├─ uploads/              放图片
│  └─ generated/            today / gallery / sessions 快照
├─ lib/desk/                本地引擎（Python 标准库）
├─ docs/                    数据契约、链接、定时
├─ hooks/                   agent / launchd 钩子样例
├─ tests/                   适配器测试与样例 transcript
├─ README.md
├─ METHOD.md                这套东西的方法论
└─ INDEX.md                 desk index 生成
```

---

## 隐私与安全

- 服务只绑 **127.0.0.1**，局域网和公网都访问不到。
- 不联网、不上传、无遥测、无账号。
- 读 transcript 是**只读**；不会改你的会话。
- `command` 类型默认不执行。
- 派 agent、跑定时默认不执行，必须显式确认。

---

## 常见问题

**双击 install.command 没反应？**
右键 → 打开；或终端 `bash install.command`。

**`desk: command not found`？**
`~/bin` 不在 PATH。把 `export PATH="$HOME/bin:$PATH"` 加进 `~/.zshrc`，或直接用 `python3 bin/desk ...`。

**显示器里没有今天的待办？**
先 `desk doctor` 看 transcripts 是不是 0。是 0 的话，说明没找到 `~/.claude/projects` 或 `~/.codex/sessions`；在 `data/config.json` 的 `transcriptRoots` 里加上你的路径，再 `desk sync`。

**图片不显示？**
把图片放进 `data/uploads/`，再 `desk sync`。外部目录写进 `data/config.json` 的 `galleryDirs`。

**想把旧版桌子的内容搬过来？**
```bash
desk import --from /path/to/旧版桌面 --with-assets
```
它会导入 `notes/便签.log.jsonl`、`todos/待办.log.jsonl`，把旧 `js/data.js` 转成 `data/content.local.json`，并把素材放进 `app/assets/me/`。

**端口被占了？**
`desk serve --port 7788`。

**把文件夹挪了位置？**
重新双击一次 `install.command`，`~/bin/desk` 的命令链接要指向新路径。

**3D 页打不开？**
`app/desk3d.html` 需要浏览器 WebGL；如果关掉了硬件加速，先在 Chrome / Safari 里打开它试试。

---

## 卸载

双击 `uninstall.command`，或：

```bash
desk uninstall
```

它会移除 `~/bin/desk` 和开机启动，**保留** `data/`。要彻底删就把整个文件夹删掉。

---

## 出处

- 原版：一张彩色漫画工作台（Cohub，`visibility=space`）；引擎结构做了通用化，内容和素材已换成模板。
- 本地版：只保留引擎与格式，内容、入口、时钟全部换成你的本机。

方法论见 [METHOD.md](METHOD.md)。

框架图：[docs/framework.html](docs/framework.html)（可点按钮逐步讲）· [docs/architecture.png](docs/architecture.png)（可直接发人）。
