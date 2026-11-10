# 给接手的 agent · 先读这一页

你要接手的是一个**本地、纯文本、可自检**的桌面工作台。它不依赖 Cohub 运行时，也不需要账号；只需要一台 Mac、Python 3.9+，以及可选的 Claude Code / Codex。

## 先跑这三条

```bash
cd comic-desk-local
bash verify.sh          # 编译 + build + 测试 + doctor + 起服务 + 调 API
python3 bin/desk serve  # http://127.0.0.1:7777
```

如果 `verify.sh` 最后打印 `PASS`，说明这个包在你手上是活的。

## 预期输出

- `desk build` 返回 `{"ok": true, "links": 9, ...}`
- 单元测试 5 个全过（`Ran 5 tests ... OK`）
- `desk doctor` 显示 `data` 下四个文件都是 `true`
- `/api/health` 返回 `{"ok": true, ...}`
- `/api/action` 的 `notes` 返回 `ok: true` 且有 `board`
- 页面在 `http://127.0.0.1:7777/` 能打开

## 这个包的结构

| 路径 | 是什么 |
|---|---|
| `app/` | 桌面本体，纯静态；`index.html` 可直接打开 |
| `data/` | 唯一真相层：content / links / notes / todos / schedule |
| `lib/desk/` | 本地引擎：适配器、动作、编译、HTTP |
| `bin/desk` | 命令行入口 |
| `docs/` | 数据契约、链接、定时、框架图 |
| `tests/` | 5 个最小回归测试 + 仿真 transcript |
| `README.md` | 给人看的安装与结构 |
| `METHOD.md` | 方法论：物 / 指针 / 时钟 |

## 不要假设

1. **这是通用模板，不是某个人的数据。** 桌面上的内容、链接、立牌都是脱敏占位。要变成某个人的工作台，先填 `data/content.local.json` 和 `data/links.json`，或 `desk import --from <旧版目录>`。
2. **真实 transcript 没有在这个环境里跑过。** 适配器用 `tests/fixtures/` 的仿真 Claude/Codex 记录测过；真实格式可能有差异。先 `desk doctor` 看 `transcripts` 是否大于 0，再 `desk sync` 看 `data/generated/today.json`。
3. **`desk ask` / `desk schedule --run` 会花额度。** 默认不执行；只有显式加 `--yes` / `--run` 才调本地 agent。
4. **macOS 分支没有在真 Mac 上跑过。** `open`、`launchctl`、`install.command` 的 Gatekeeper 行为需要现场确认；Linux 沙箱里验过的是 build / tests / serve / API。
5. **3D 页需要 WebGL。** 没有 WebGL 时 `desk3d.html` 会停在“正在搭建”。

## 接真实数据

```bash
# 1. 看本机有没有 agent
python3 bin/desk doctor

# 2. 扫今天的会话
python3 bin/desk sync
cat data/generated/today.json

# 3. 从旧版彩色漫画工作台导入账本和内容
python3 bin/desk import --from /path/to/旧版桌面 --with-assets

# 4. 把常用入口写进 links.json，再 build
python3 bin/desk build
```

## 边界

- 只绑 `127.0.0.1`，不联网、不上传、无遥测。
- 读 transcript 是只读。
- `command` 类型默认不执行。
- 便签 / 待办只追加；不要覆盖 `data/notes.jsonl`、`data/todos.jsonl`。
- 生成物（`app/js/data.js`、`today.js`、`notes-board.js`、`INDEX.html`）不要手改；改 `data/` 再 `desk build`。
- 发布页面时用 `visibility=space`，不要走 public。

## 验收清单

- [ ] `bash verify.sh` 打印 `PASS`
- [ ] `desk doctor` 看得到 Python、data 四项、agent 路径
- [ ] `desk sync` 后 `today.json` 有今天的会话，或明确为空（没有 transcript）
- [ ] 页面能开，显示器/便签/书/海报至少四个面板能点开
- [ ] `data/` 里没有 token、cookie、凭证
- [ ] 如果你改了 schema，同步更新 `docs/DATA-CONTRACT.md` 和 `tests/`

一句话：**能跑、能验、能改；不能把模板当成品，不能把“已回复”当“已完成”。**
