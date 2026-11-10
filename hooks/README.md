# 钩子样例

这里的文件都不会自动生效。挑一个，按 [docs/SCHEDULE.md](../docs/SCHEDULE.md) 接到你本地的 agent 上。

| 文件 | 给谁 | 做什么 |
|---|---|---|
| `claude-settings.example.json` | Claude Code | `Stop` 时同步；`SessionStart` 时打印到点 prompt |
| `codex-notify.sh` | Codex | 同步 + 把到点 prompt 写到 `data/generated/due.json` |
| `comicdesk-tick.sh` | launchd / cron | 同上；想自动跑就加 `--run` |

原则：**钩子只同步和提醒，不在背后替你花额度。**
