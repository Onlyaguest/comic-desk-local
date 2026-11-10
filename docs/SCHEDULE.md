# 定时 · 时钟外置

这张桌子**不装 cron**。

`data/schedule.json` 只是一份 prompt 清单：

```json
{
  "jobs": [
    {"id":"morning","when":"daily 09:00","agent":"auto","prompt":"读今天的 today.json，用三行告诉我：今天保哪条线、三个要拍的板、第一个 15 分钟动作。","enabled":true},
    {"id":"evening","when":"daily 17:30","agent":"auto","prompt":"把今天压成五条，写到 data/digest/YYYY-MM-DD.md；没有就写「今天为零」。","enabled":true}
  ]
}
```

查看哪些到点了：

```bash
desk schedule          # JSON：due + prompt
desk schedule --run    # 真跑（花额度）
```

`desk schedule` 只读不跑；`--run` 才会调用 `claude -p` 或 `codex exec`。

---

## 三种接法

### A. 交给 Claude Code 的钩子

Claude Code 支持 `Stop` / `SessionStart` 钩子。把下面写进 `~/.claude/settings.json`（路径换成你的桌面）：

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {"type": "command", "command": "cd \"$HOME/ComicDesk\" && python3 bin/desk sync >/dev/null 2>&1"}
        ]
      }
    ],
    "SessionStart": [
      {
        "hooks": [
          {"type": "command", "command": "cd \"$HOME/ComicDesk\" && python3 bin/desk schedule"}
        ]
      }
    ]
  }
}
```

- `Stop`：每轮结束同步一次，显示器上的「今天」就是新的。
- `SessionStart`：新会话开始时把到点的 prompt 打给 Claude，让它自己决定做不做。

> 不同版本的 Claude Code 钩子字段可能略有差异；先跑 `claude --help` 或看它的 settings 文档。钩子只读 `desk schedule`，不自动 `--run`。

### B. 交给 Codex 的 notify

`~/.codex/config.toml`：

```toml
notify = ["bash", "/Users/you/ComicDesk/hooks/codex-notify.sh"]
```

`hooks/codex-notify.sh` 只做一件事：同步桌面，并把到点的 prompt 写到 `data/generated/due.json`，下一次你打开 Codex 时自己看。

### C. 交给 launchd（系统闹钟）

如果你就是想要「到点自动跑」，用 `hooks/comicdesk-tick.sh` + 一个 LaunchAgent：

```bash
# 每 15 分钟看一次有没有到点；只写 due.json，不自动调 agent
bash hooks/comicdesk-tick.sh
```

要自动调 agent，把脚本里的 `desk schedule` 改成 `desk schedule --run`。**这会花额度**，自己决定。

---

## 为什么不让桌面自己定时

- 桌面没有判断：它不知道你今天是不是在开会、是不是该熔断。
- 桌面没有上下文：它不知道昨天那条线走到哪了。
- 桌面没有权限边界：一旦它能自动执行，就会变成一个你要维护的半吊子调度器。

agent 有这三样。所以时钟给它。

---

## 一个最小可用的节律

| 时间 | 谁 | 做什么 |
|---|---|---|
| 09:00 | agent | 读 `today.json`，回三行：保哪条线、三个板、第一个 15 分钟 |
| 每轮结束 | 钩子 | `desk sync`，把新会话收进今天 |
| 17:30 | agent | 写 `data/digest/YYYY-MM-DD.md`，只写五条 |
| 睡前 | 人 | 看一眼便签墙，关桌面 |

不需要更多。定时越多，你越不会看。
