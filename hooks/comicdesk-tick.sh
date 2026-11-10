#!/bin/bash
# launchd / cron 可调：看有没有到点的 prompt，写到 data/generated/due.json。
# 默认不执行 agent；要自动执行，把下面 --run 加上（会花额度）。
set -e
DESK="$(cd "$(dirname "$0")/.." && pwd)"
cd "$DESK"
python3 bin/desk sync >/dev/null 2>&1 || true
python3 bin/desk schedule > data/generated/due.json
echo "due → data/generated/due.json"
