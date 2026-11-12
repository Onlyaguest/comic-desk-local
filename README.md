# 漫画工作台 · Comic Desk

一个在本机运行的工作台，把会话待办、图片和小应用收在桌面上。**默认离线样例模式，无账号、无 AI / token 消耗，无需 Codex、Claude、Mirasim 或 Cohub CLI。**

## 在 Mac 启动

1. 安装 **Python 3.11 或更高版本**（从 [python.org](https://www.python.org/downloads/) 下载；macOS 不保证自带）。没有 pip 依赖。
2. 下载此私有仓库的 ZIP，解压到可写目录。
3. 双击 `start.command`。若系统不允许双击，在终端进入解压目录执行 `bash start.command`。
4. 浏览器自动打开 `http://127.0.0.1:7777/`。以后仍双击同一个文件，已运行时直接打开。

端口被其他工作台占用时：`COMIC_DESK_PORT=7788 bash start.command`。终端直接运行也可以：`python3 bin/desk serve --port 7788`，Ctrl+C 停止该前台服务。双击启动的服务可用 `python3 tools/stop.py` 停止。没有安装全局命令、定时任务或开机启动。

## 三个主要入口

- **显示器 → 会话待办**：今天的会话、往日未收口；标题可打开样例正文。勾选写入本机 JSONL 账本，次日不再显示已完成项；有新对话则重新出现，历史勾选保留。点击底部“模拟一条新对话”可验证 Codex 样例自动重开。样例首次启动按当天 / 昨天生成，重启不重置你的操作。
- **图片展台**：点击图片看大图；封面按文件名 / 路径规则筛最近成品，过程截图仍保留在完整索引。规则可能误判，可通过命名改善，不调用 AI。
- **应用与页面**：常用 / 最近 / 全部、搜索、来源筛选、置顶、隐藏、改名、同名版本选择。包含本地交互计时器、报告 v1/v2，以及明确标记的 **Cohub 离线模拟应用**。模拟项不代表连接了真实云端。

刷新只读增量数据和更新本地投影，不会调用模型。样例模式不会读取本机其他应用的会话。没有自动后台拉取；页面状态查询不等于拉取平台数据。

## 用自己的文件（也不需要 AI）

可在样例模式先试导入：

```sh
python3 tools/import_files.py /完整路径/报告.html /完整路径/海报-final.png
```

仅登记显式给定的文件，以 mtime/size 判断变化，不遍历整个磁盘；图片和 HTML 出现在索引及展台。HTML 从独立本机端口预览，支持同目录 / 子目录资源。依赖父目录、开发服务器、登录或第三方 API 的应用需自行启动其依赖。

想从空数据开始：**另解压一份代码**，首次启动前运行 `python3 tools/setup_personal.py`，然后双击启动。不会清空你已经用过的目录。

## 可选：接真实会话

编辑本机生成的 `data/sources.local.json`（不提交 Git）。先使用个人模式，再按需开启：

```json
{
  "demo": false,
  "localEnabled": true,
  "workbuddyEnabled": false,
  "cohubEnabled": false,
  "mirasimEnabled": false,
  "sessionStartDay": "2026-11-11"
}
```

`localEnabled` 读取自己的 `~/.codex` / `~/.claude`；其他连接器需安装相应应用并登录，云端读取还需该平台权限。Cohub 的 `cohubCommand` 必须指向你自己的 CLI 包装脚本；本仓库不附账号、凭据或私有 skill。Mirasim 云端多空间取数依赖它的空间组网与权限，不保证未经配置即可读取。WorkBuddy 没有可靠原会话深链时返回本地详情，不能冒充已恢复原会话。

配置后重启，执行 `python3 bin/desk sync` 或点击刷新。起始日仅控制待办显示，完整索引保留。增量索引和各连接器实现见 `lib/desk/`。外部 CLI/API 版本变化可能需要调整适配器。

## 数据与隐私

`data/index.sqlite3` 是可重建索引；`data/todos.jsonl` / `notes.jsonl` 是只追加行为账本；`data/works-state.json` 保存展台整理；`app/js/` 中部分文件是启动时生成的快照。**以上均排除 Git；更新前备份自己的 data/，不要覆盖账本。** 浏览器清缓存不会删勾选记录。

服务只绑定回环地址，写接口拒绝跨源。HTML 作品可执行自己的 JavaScript，仅打开你信任的文件。没有遥测。沿用原仓库的通用桌面装饰，样例作品使用本仓库生成的 SVG；不包含私人照片、音频、3D 模型。此仓库保持私有，尚未授予开源许可证。

## 验证和发布

```sh
bash verify.sh
python3 tools/audit_release.py
```

自检需 Python 3.11+、curl，发布审计需 Git。已在本机 Mac 运行回归与空 HOME 验证。`docs/ci/verify.yml` 提供 macOS / Linux CI 模板；仓库管理员可移入 `.github/workflows/verify.yml` 启用（需要 workflow 权限，本次尚未启用）。`data/` 和生成快照不能靠手动脱敏后上传，应始终不跟踪；只提交源码与虚构 `samples/`。审计覆盖当前候选文件，不能保证 Git 历史自动被清洗。历史不重写，仓库权限保持私有。
