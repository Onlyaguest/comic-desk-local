#!/bin/bash
# 双击我：安装本地工作台（macOS）
set -e
cd "$(dirname "$0")"

echo "======================================"
echo "  我的本地工作台 · 安装"
echo "======================================"
echo

if ! command -v python3 >/dev/null 2>&1; then
  echo "没找到 python3。macOS 自带的话，先在终端运行：xcode-select --install"
  echo "或者从 https://www.python.org/downloads/ 装一个。"
  read -r -p "按回车关闭…" _
  exit 1
fi

python3 bin/desk install "$@"

echo
read -r -p "装好了。现在启动吗？[Y/n] " ans
case "$ans" in
  n|N) echo "好的。以后双击 start.command 启动。";;
  *) python3 bin/desk serve;;
esac
