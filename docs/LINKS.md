# 链接 · 一物一指针

`data/links.json` 是整张桌子的入口表。

```json
{
  "version": 1,
  "links": [
    {
      "id": "inbox",
      "label": "收件箱",
      "group": "入口",
      "type": "folder",
      "target": "~/Desktop",
      "icon": "📥",
      "note": "每天真的会打开的那个文件夹"
    }
  ]
}
```

## 类型

| type | 行为 | target 例子 |
|---|---|---|
| `folder` | 用 Finder 打开 | `~/Desktop` / `data/uploads` |
| `file` | 用默认 App 打开 | `data/notes.jsonl` / `~/Documents/a.md` |
| `url` | 浏览器打开 | `https://example.com` / `obsidian://open?vault=...` |
| `app` | `open -a` | `Claude` / `Codex` / `Obsidian` |
| `command` | 默认**不执行** | `open .`（需 `"allowCommand": true`） |

相对路径按桌面根目录解析；`~` 按你的 home 解析。

## 在页面上打开

页面里的链接统一走：

```
/api/open?id=<id>
```

服务会执行对应的 `open`，然后返回一个「已打开，可关闭」的小页。

命令行：

```bash
desk open inbox
```

## 在索引里出现

`desk index` 会把所有链接写进 `INDEX.md` 和 `app/INDEX.html`。

桌面里的四个地方是同一张表的视图：

- 书 → 索引条目
- 海报 → Works 橱窗
- 手柄 → 日常在看
- 窗户 → 内嵌 `INDEX.html`

## 加一条的步骤

1. 打开 `data/links.json`
2. 复制一条，改 `id`、`label`、`group`、`type`、`target`
3. `desk build`
4. 刷新页面

不需要改 HTML，也不需要改 JS。

## 安全

- `command` 默认拒绝执行。要给某一条开口，加 `"allowCommand": true`，并且自己确认 target 是什么。
- `url` 直接交给浏览器，不做白名单；这是你自己的本机入口表，别把不可信的链接写进来。
- 服务只绑 `127.0.0.1`，外部访问不到。
