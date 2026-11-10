#!/bin/bash
# 一条命令自检：编译 → build → 测试 → doctor → 起服务 → 调 API
set -euo pipefail
cd "$(dirname "$0")"
PORT="${1:-7799}"
PY="${PYTHON:-python3}"

echo "== 1/5 编译 =="
"$PY" -m compileall -q lib

echo "== 2/5 build =="
"$PY" bin/desk build

echo "== 3/5 测试 =="
"$PY" -m unittest discover -s tests

echo "== 4/5 doctor =="
"$PY" bin/desk doctor

echo "== 5/5 起服务 + API =="
"$PY" bin/desk serve --no-open --port "$PORT" >/tmp/comicdesk-verify.log 2>&1 &
PID=$!
trap 'kill "$PID" 2>/dev/null || true' EXIT
sleep 1
curl -fsS "http://127.0.0.1:$PORT/api/health"
echo
curl -fsS -X POST "http://127.0.0.1:$PORT/api/action" \
  -H 'content-type: application/json' \
  -d '{"action":"notes","input":{"op":"list"}}' \
  | "$PY" -c "import sys,json; d=json.load(sys.stdin); assert d.get('ok') and 'board' in d; print('notes', len(d['board']))"

echo
echo "PASS"
