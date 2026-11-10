#!/bin/bash
# Codex notify 钩子：只同步桌面 + 记下到点的 prompt，不自动调 agent。
# 用法：在 ~/.codex/config.toml 里写
#   notify = ["bash", "/Users/you/ComicDesk/hooks/codex-notify.sh"]
set -e
DESK="$(cd "$(dirname "$0")/.." && pwd)"
cd "$DESK"
python3 bin/desk sync >/dev/null 2>&1 || true
python3 bin/desk schedule > data/generated/due.json 2>/dev/null || true
