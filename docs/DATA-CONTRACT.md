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
- `app/catalog.html`
- `INDEX.md`

这些文件都可以随时删掉重建；不要手改。

## 10. 四端本地增量索引（2026-11-11）

`data/index.sqlite3` 为可重建 SQLite WAL 索引，不修改原始日志。`sessions` 用 engine/native ID 去重，`origins` 记录宿主与账号，`messages`、FTS、`artifacts`、`relations` 分离。

新增 `cloud_turns(session_id,sequence,status,updated,messages)` 保存经遮盖的用户/助手文本，主键为会话＋sequence；不保存工具过程、Space.meta 或账号凭据。`sync_failures(session_id,attempts,error,updated)` 为可重试失败队列，不能用失败覆盖原有消息。

`checkpoints`：`file:<path>` 为mtime_ns:size；`version:<sid>` 为源目录版本哈希；`detail:<sid>` 为最后成功对应时间；`detail-version:<sid>` 为成功版本。网络期间若目录版本更新，旧请求不能将新版本标为已完成。目录连续两页无变化停止；手动 reconcile 只全查目录，不重读未变正文。正文增量回读最新轮和所有未结束轮，合并后原子重建该会话消息/FTS。

`GET /api/index/today` 返回北京时间date、items、四端counts、来源状态；items.sources可多宿主标签，counts总和可大于去重items长度。`data/generated/today.json` 是同结构快照，不自动写待办账本。

图片由kind=image标记，按文件后缀、Markdown图片或助手图片块识别。`GET /api/index/artifacts?images=1` 支持原分页，`GET /api/index/image?id=` 仅服务已登记且魔数可识别的图片。`data/image-cache/<id>/<revision>/` 是可重建缓存，不是独立原件。

补齐状态拆分为pending_bodies（尚无正文）与blocked_files（正文已读、文件目录权限受限）。blocked-version:<sid>保存权限失败对应版本，默认增量不会反复请求同一拒绝；显式补齐允许重试。API满100轮误报hasMore=false时仍沿nextCursor探测，避免静默截断。

## WorkBuddy 兼容（2026-11-11）

已增加第五来源 workbuddy，配置 workbuddyHome 默认 ~/.workbuddy。只读 projects/*/*.jsonl 与 artifact-index/*.json；session 主键 workbuddy:<原生 ID>，不与 Claude 混同。正文只保留 user/assistant 文本并去掉注入的 system-reminder，以 ai-title 最新值作为标题。毫秒时间统一为 UTC，再由今日视图按北京时间筛选。

checkpoints 分别保存 workbuddy:transcript:<path> 和 workbuddy:artifacts:<path> 的解析版本、mtime_ns、size；不变文件跳过正文读取，文件目录变化可独立更新。目录枚举仍会执行，不代表有文件系统 watcher。损坏行不会写入成功指纹，下次重试。

今日 counts 包含 workbuddy。图片复用已登记文件预览接口。私有画布 ardot:// 暂不导入；文件变更记录明确标为引用，不冒充成品。

当前 WorkBuddy 5.1.7 的已检查深链路由只支持功能页，未发现已验证的原会话直达。显示器的 WorkBuddy 卡片打开本地详情；详情提供打开 WorkBuddy 首页和复制会话标题。POST /api/index/open 的 kind=app、source=workbuddy 只接受已登记 WorkBuddy 会话，并打开固定 workbuddy://home。不会猜造会话深链。

## 2026-11-12 显示器会话待办

固定起始日 2026-11-11（北京时间）。Todos 默认只读 index.sqlite3，将起始日以来有正文活动或原端更新时间的去重会话映射为虚拟待办；不复制或修改完整索引。最近活动日在今天归 today_open，之前归 carry；同一会话只出现一次。手动待办保留。

虚拟主键为 indexed-session:<索引会话ID>，session_id 保存原索引主键。勾选/放下/重开沿用 todos.jsonl 的 done/drop/reopen 追加事件；会话再次活跃不自动清除人工状态。done_today 只含 doneAt 按北京时间落在当天的完成记录，页面名为“今天勾掉的”。往日完成记录不进入界面，但追加日志与完成状态永久保留，不重新进入未完成列表。start_day 返回固定起始日。跨日归类按北京时间动态计算，完整索引无日期裁剪。

### 新对话重新进入待办（2026-11-12）

会话 done 事件额外保存 dialogue 水位（最近 user/assistant 消息的时间戳与 SHA256，不复制正文）。读取时，若最近消息时间不早于完成水位且内容指纹变化，派生 state=open、reopened_by=new_dialogue；刷新同步到的新消息及流式回复续写可触发。标题/元数据变化不触发；正文暂不可用或回退到更老消息不触发。再次勾选追加新的 done 和新水位，旧事件不改。自动重开为索引＋账本派生结果，不在每次读取重复追加日志；doneAt仍保留上次完成时间。

旧 done 事件没有水位时，只在消息时间晚于 doneAt 时重新打开；不猜测旧回复是否在原时间戳下被修改。放下状态不自动重开。发现新对话仍依赖既有增量刷新，未增加后台轮询或模型调用。

### 展台封面规则 finished-image-v1

GET /api/index/cover 返回 {item: artifact|null, rule: "finished-image-v1"}。按索引updated倒序、id稳定排序，从全体图片中只读筛选；无候选返回null，桌面恢复默认展台，不退回过程图片。

拒绝优先：标题/解码后的文件名包含二维码、截图、登录、验收、调试、草稿、预览、参考图、缩略图或对应英文标记；路径位于tmp/temp/research/sources/reference/input等过程目录。再要求标题/文件名有成品、终稿、封面、海报、壁纸、头像、表情包或cover/final/poster/wallpaper/avatar标记，或位于图片产物目录，或证据注明正式交付。仅publish目录不足以入选。

该规则不调用模型、不识别图片像素，不保证命名不规范的图片分类正确；无法判断的图片不作封面。完整图片列表与索引条目不删除、不改写。最新以索引更新时间为准，不声称一定为原始创作时间。

## 应用与页面展台 v1（2026-11-12）

新增只读投影 GET /api/index/works，Cohub 按原应用 ID 去重；本地从 artifacts 已登记绝对 HTML/HTM 路径发现，不扫描整盘。仅同父目录、去除明确 -vN 后同名文件合并版本；不猜测不同作品关系。local title 从前64KiB的<title>提取，mtime_ns/size未变则复用元数据。缺失、测试、草稿等进入待整理。作品分类为工具/报告/演示/其他，规则匹配，不调用模型。

- data/works-cloud.json：Cohub应用目录快照，保留稳定ID、发布状态、真实URL、封面与版本号。初次全量读应用目录，后续随既有增量同步按返回页合并。离线沿用旧快照，不推断删除。
- data/works-metadata.json：本地HTML元数据缓存，可重建。
- data/works-state.json：用户置顶顺序、改名、分类、隐藏、待整理确认、默认版本选择。POST /api/index/works 只接受登记作品及所属版本。刷新不会覆盖人工设置。
- GET /api/index/work-view?id=...：仅对登记本地HTML重定向到独立loopback origin的静态预览，保留同目录及子目录依赖；不注入代码，不修改原文件。无目录列表，拒绝隐藏文件、目录外符号链接和非素材扩展。需要父目录资源、额外后端或原站API的HTML不保证完整运行。
- GET /api/index/work-cover?id=...：本地相邻cover/poster图片，同样隔离预览。云端优先已提供封面，否则文字配色卡，不自动截图或生成图。

展示为常用、最近更新、全部；搜索、来源、类型、待整理/隐藏筛选。未发布云应用不提供伪造的运行链接，只提供源空间。完整会话及产物索引不删除、不重写。独立入口 /works.html，桌面展台的“应用与页面”使用同一组件。

## 可分发版本

默认 `sources.local.json` 中 `demo: true`，首次启动动态生成当天与昨天的虚构记录。`demo:seed:v1` 检查点防止重复初始化，勾选账本不重置。所有真实连接器默认关闭；localEnabled / workbuddyEnabled / cohubEnabled / mirasimEnabled 分别显式启用。
`sessionStartDay` 首次初始化为昨天，之后固定；个人配置优先。`POST /api/index/demo-message` 仅可更新四条 demo: 会话且只允许 demo 模式。`GET /api/index/status` 返回 demo 标志。样例会话打开返回本机索引 URL；真实会话仍由原适配器处理。
`tools/import_files.py` 仅导入明确指定路径，使用 manual:<path> 检查点与 mtime_ns/size 增量登记；不调用模型、不做目录扫描。


## 融合版 2.2 可分发契约

- 首页 `app/index.html` 叠加 `app/fusion/`；`/original.html` 保留旧入口，共用索引和追加账本。不会覆盖既有勾选或便签历史。
- `GET /api/desk/board?days=7|30|all&pin=<id>` 合并空间快照与 Codex / Claude / Cohub 索引，返回 `board`、`freshness`、`sessionCounts`、原字段 `usage` 和本次消耗 `metrics`。宿主别名只按显式映射合并，远端节点保留命名空间。
- `GET /api/desk/card?id=<id>` 按需核对纸卡背面；`GET /api/desk/evidence?receipt=<id>&index=0` 只读项目范围内已登记文本，拒绝越界/符号链接越界，并以 CSP sandbox 展示。
- `GET /api/desk/images` 接收 q/source/status/offset/limit，默认24张；目录不联网。图片接口 `/api/desk/image?id=&mode=thumb|full` 不取远端；只有显式 `POST /api/desk/image-fetch` 才可在个人模式取单张。`POST /api/desk/image-cover` 只保存封面偏好。未登记 ID 不可读取。
- `POST /api/desk/sync-index` 尊重 demo/localEnabled/cohubEnabled，样例模式禁止所有外部读取；非样例 Cohub 同步最多5次只读 CLI，互斥与成功30秒冷却。无后台轮询或模型调用。

样例由 `samples/fusion-board.json`、`fusion-context.json`、`fusion-evidence.md` 提供，全部虚构。首次启动增加 `demo:claude`，并保留旧版4条样例与所有账本；检查点 `demo:seed:v2` 防止重复写入。样例时间动态生成，不声称是云端核对时间。

个人模式（demo=false）只读如下显式配置，不扫描 HOME 或聊天：

- `data/fusion/board.local.json`：`{space, spaceNodeId, fetchedAt, checkedAt, board:{v,day,cards:[],projects:[],today:[]}}`。卡状态为 ai/wait/me/stuck/done/unknown；受限卡不保存正文，入口拒绝 javascript 和协议相对地址。
- `data/fusion/context.local.json`：形状参考样例。`aliases` 为宿主/原生会话ID映射，`tasks[sessionId]` 提供 assistant/taskRef，`roles[assistantId]` 提供 name/duty/machine；`records` 可提供显式宿主生命周期。`feedback[]` 只包含自己明确登记的反馈和项目证据，不自动读取任何聊天。
- `data/fusion/writeback-receipts.json`：列表，每条含 id/taskRef/statementHash/sourceRef/evidence。statementHash 为移除空白及粗体标记后的独立「回写：」行 SHA-256；仅相同任务、声明和文件证据同时匹配才算 verified。引用和代码块内的回写行不计。历史证据不自动认定本轮交付完成。
- `data/fusion/observations.json`、`cohub-usage.json`、`sync-ledger.json`、`images/`、`image-prefs.json` 为运行时缓存；不入 Git。原记录观察仅在非样例且 localEnabled 时读取已登记的近期日志，不遍历 HOME；上限256KiB，不保存思考/工具正文。
