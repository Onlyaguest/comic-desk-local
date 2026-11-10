#!/bin/bash
# 双击我：启动桌面
set -e
cd "$(dirname "$0")"
exec python3 bin/desk serve
