#!/bin/bash
# 双击我：移除命令链接和开机启动（数据保留）
set -e
cd "$(dirname "$0")"
python3 bin/desk uninstall
read -r -p "按回车关闭…" _
