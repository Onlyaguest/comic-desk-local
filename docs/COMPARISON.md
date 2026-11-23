# Comic Desk 和相近项目对比 · How Comic Desk compares

> 核对日期 2026-11-23。别人的项目信息全部来自各自 GitHub 仓库首页和 README 当天的内容，star 数是当天的数；它们更新很快，以对方仓库为准。我们自己的功能以本仓库 [README](../README.md) 和 [数据契约](DATA-CONTRACT.md) 为准。
>
> Checked on 2026-11-23 against each project's GitHub page and README. Star counts are from that day. Other projects move fast — their repos are the source of truth.

## 一句话 · In one line

- **agentsview** 帮你**查**：把几十种编程助手的会话收进本机，搜索、看统计、算 token 和花费。
- **omnigent** 帮你**指挥**：一个编排层同时调度 Claude Code、Codex、Cursor 等，跨设备、云沙箱、策略管控。
- **claudian / obsidian-mind** 帮助手**记**：把 Obsidian 笔记库变成助手的工作目录或长期记忆。
- **Comic Desk（本项目）** 帮你**收口**：把几家助手的会话变成每天能勾的待办，谁在等你点头、谁出错放在一张桌面上看；图片和做出来的小页面也摆在同一张桌上。

English: agentsview helps you *search and measure* agent sessions; omnigent helps you *orchestrate* agents; claudian and obsidian-mind give agents a *memory* inside Obsidian; Comic Desk helps one person *close the loop* each day — sessions from several agents become a check-off list, with "waiting on you / errored" flags, an image shelf and a shelf of the small HTML apps you made, all on one local desk.

## 对照表 · Side by side

| | **Comic Desk** | **agentsview** | **omnigent** | **claudian** | **obsidian-mind** |
|---|---|---|---|---|---|
| 仓库 · Repo | [Onlyaguest/comic-desk-local](https://github.com/Onlyaguest/comic-desk-local) | [kenn-io/agentsview](https://github.com/kenn-io/agentsview) | [omnigent-ai/omnigent](https://github.com/omnigent-ai/omnigent) | [YishenTu/claudian](https://github.com/YishenTu/claudian) | [breferrari/obsidian-mind](https://github.com/breferrari/obsidian-mind) |
| Star（11-23） | 1 | ~6.5k | ~11.5k | ~16k | ~5.6k |
| 协议 · License | MIT | MIT | Apache-2.0 | MIT | MIT |
| 是什么 · What it is | 本机网页工作台（Python 标准库服务 + 浏览器页面） | 会话搜索 / 统计工具：CLI、后台服务、网页、桌面 App、Docker | 多助手编排框架（meta-harness），CLI + 网页 + 桌面 App | Obsidian 插件，在笔记库里内嵌编程助手 | Obsidian 笔记库模板 + 钩子和命令，给助手长期记忆 |
| 接哪些助手 · Agents | Claude Code、Codex（读本机日志）；WorkBuddy、Cohub、Mirasim（各自显式开启） | Claude Code、Codex 及 50 多种助手；还能导入 ChatGPT / Gemini / Grok 网页对话 | Claude Code、Codex、Cursor、OpenCode、Goose、Copilot 等十几种及自定义助手 | Claude Code、Codex、Grok Build、OpenCode、Pi 等 | Claude Code（完整）、Codex CLI、Gemini CLI |
| 会话进本机索引 · Local session index | 有：只读原日志，写一份可重建的 SQLite 索引（含全文检索），不改原文件 | 有：同步进本机 SQLite，全文搜索，可选按意思搜索 | 有本机历史，主打跨设备同步 | 插件内的会话标签页和会话管理 | 不索引会话，把知识写成笔记 |
| 每天的待办 · Daily check-off | **有**：当天和往日没收口的会话变成待办，可勾、可放下；勾掉后有新对话会自动重新出现；记录只追加 | README 未提到 | README 未提到 | README 未提到 | 有晨会 / 收工命令，由助手整理笔记 |
| 助手状态 · Agent status | **有（可选）**：装钩子后 Claude Code / Codex 自己报「在干 / 等你 / 做完 / 出错」，顶栏显示数量 | 会话有新消息时网页实时刷新（SSE）；有活跃时间等统计；README 未提到「等你 / 出错」提示 | 有，且能暂停等你批准高风险操作 | 插件内显示会话活动 | 无 |
| 花费统计 · Token / cost | **不做**：只原样显示来源给出的用量字段，不估账单 | **强项**：按会话 / 模型 / 日算 token 和花费 | 可设花费上限 | 无 | 无 |
| 指挥助手干活 · Orchestration | **不做**：不启动、不调度助手 | 不做 | **强项** | 在笔记库里直接和助手对话，会话间可互发消息 | 通过助手自己的命令工作 |
| 给助手长期记忆 · Agent memory | **不做**：不往助手的上下文里注入东西 | 不做 | 可选记忆扩展 | 项目共享说明和记忆文件 | **强项** |
| 图片和作品 · Images & made things | **有**：已登记图片的图像册；本机 HTML 小应用 / 报告的展台，可置顶、改名、看版本 | 工具输出图片可选 OCR 搜索 | 无 | 无 | 无 |
| 要不要 AI / 账号 · Needs AI or accounts | 不要：默认离线样例，无账号、不调模型、不耗 token | 不需要账号；花费按公开价格表算；按意思搜索默认用本机向量模型 | 要模型或订阅 | 要助手的订阅或 API | 要助手 |
| 平台 · Platform | 在 Mac 上跑过回归；Linux CI 模板已备；Windows 没测 | macOS / Linux / Windows | macOS 桌面 App，CLI | Obsidian 桌面版 | Obsidian + Node 22 |

## 我们做什么 · What Comic Desk does

1. **把几家助手的会话收进一份本机索引。** 只读 `~/.claude`、`~/.codex` 等原日志（WorkBuddy、Cohub、Mirasim 要自己在 `data/sources.local.json` 里开），不改原文件；索引可删掉重建。
2. **把会话变成每天的待办。** 今天有动静的会话进「今天」，往日没收口的进「往日」；勾掉写进只追加的账本；勾掉后这个会话又有新对话，会自己回到待办。
3. **四端事项板。** 空间事项、Codex、Claude Code、Cohub 会话放一块板，标来源，按 7 天 / 30 天 / 全部、来源、项目、关键词筛。
4. **助手自己报状态（可选）。** `python3 tools/agent_hooks.py install claude codex` 装钩子后，助手等你点头或出错会记一行，顶栏显示「等你 2 · 出错 1」。不记提示词和回复。
5. **图片和作品摆上桌。** 图像册看已登记图片；「应用与页面」展台放本机 HTML 报告和小工具。
6. **协作回执核对（可选）。** 自己登记角色和「回写」回执后，纸卡背面核对声明和文件证据是否对得上。不读任何群聊或私聊。
7. **数据是纯文本。** 账本是 JSONL，内容是 JSON，索引是 SQLite；服务只绑本机地址，没有遥测。

## 我们不做什么 · What Comic Desk does not do

- 不算 token 花费、不出用量报表——要这个用 **agentsview**。
- 不启动、不调度、不编排助手，不跨设备同步——要这个用 **omnigent**。
- 不给助手注入长期记忆、不在笔记库里和助手对话——要这个用 **obsidian-mind** 或 **claudian**。
- 不支持几十种助手：现在只接 Claude Code、Codex、WorkBuddy、Cohub、Mirasim 五个来源。
- 不做按意思搜索（语义检索），不做云端同步，不做多人协作。
- 不保证 Windows 能用（没测过）。
- 项目很早期（1 star），一个人在用、在改。

## 怎么选 · Which one to pick

- 想知道「这个月几个助手花了多少钱、哪次会话最贵」→ agentsview。
- 想「一个界面同时指挥几个助手干同一件事」→ omnigent。
- 想「助手记得我上次说过什么」→ obsidian-mind；想「在 Obsidian 里直接和助手干活」→ claudian。
- 想「每天收工前看一眼：今天和几个助手开了哪些头、哪些还没收口、谁在等我」，并且不想装账号、不想耗 token → Comic Desk。

几个可以一起用：比如 agentsview 看花费，Comic Desk 管每天收口。

You can combine them — e.g. agentsview for cost reports and Comic Desk for the daily wrap-up.
