# AGENTS.md · 本地工作台

先读 [HANDOFF.md](HANDOFF.md)，再读 [README.md](README.md) 和 [METHOD.md](METHOD.md)。

## 硬规则

- 这是通用模板；个人内容放 `data/content.local.json`，不要改 `data/content.json` 的公共默认值。
- `data/notes.jsonl` 和 `data/todos.jsonl` 是 append-only；不要覆盖、不要重写历史行。
- 生成物不要手改：`app/js/data.js`、`app/js/today.js`、`app/js/gallery.js`、`app/js/notes-board.js`、`app/js/todos-board.js`、`app/INDEX.html`。改 `data/` 后跑 `desk build`。
- 不联网、不上传、不加遥测；服务只绑 `127.0.0.1`。
- 发布页面用 `visibility=space`，不得 public。
- `desk ask` / `desk schedule --run` 会花额度；没有明确要求不要跑。
- 改数据契约时，同步更新 `docs/DATA-CONTRACT.md` 和 `tests/test_desk.py`。

## 验证

```bash
bash verify.sh
```

打印 `PASS` 才算接上。
