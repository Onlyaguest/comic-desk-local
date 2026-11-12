#!/bin/bash
# 双击我：启动桌面
set -e
cd "$(dirname "$0")"
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
exec python3 bin/launch.py
