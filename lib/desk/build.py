"""把 data/ 编译成页面能直接读的快照。

引擎只读这些快照；数据从哪来（本地 agent、文件夹、手工）由 adapters 决定。
"""
from __future__ import annotations
import json, html as htmlmod
from datetime import datetime

from .paths import ROOT, APP, DATA, GEN, load_json, write_json, iso, today, rel
from .store import Notes, Todos, render_notes_js, render_todos_js


def _deep_merge(base: dict, extra: dict) -> dict:
    out = dict(base or {})
    for k, v in (extra or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_content() -> dict:
    base = load_json(DATA / "content.json", {}) or {}
    local = load_json(DATA / "content.local.json", {}) or {}
    return _deep_merge(base, local)


def load_links() -> dict:
    return load_json(DATA / "links.json", {"version": 1, "links": []}) or {"version": 1, "links": []}


def link_href(l: dict) -> str:
    t = l.get("type")
    if t == "url":
        return l.get("target", "")
    return "/api/open?id=" + l.get("id", "")


def _inject_index(content: dict, links: list[dict]) -> dict:
    c = dict(content)
    books = list(c.get("books") or [])
    seen = {(b.get("title"), b.get("link")) for b in books}
    palette = ["#14b8a6", "#ffb020", "#7c4dff", "#e5484d", "#2f6df6"]
    for i, l in enumerate(links):
        title = l.get("label") or l.get("id")
        href = link_href(l)
        if (title, href) in seen:
            continue
        books.append({
            "title": title, "author": l.get("group", "索引"), "progress": None,
            "color": palette[i % len(palette)], "note": l.get("note") or l.get("target", ""),
            "link": href,
        })
    c["books"] = books

    videos = dict(c.get("videos") or {})
    sites = list(videos.get("sites") or [])
    have = {s.get("url") for s in sites}
    for l in links:
        if l.get("type") == "url" and l.get("target") and l["target"] not in have:
            sites.append({"name": l.get("label"), "desc": l.get("note", ""), "url": l["target"], "color": "#171310"})
    videos["sites"] = sites
    c["videos"] = videos

    watch = dict(c.get("watchlist") or {})
    items = []
    for l in links:
        if l.get("type") in ("url", "app", "folder", "file"):
            items.append({
                "icon": l.get("icon", "🔗"), "title": l.get("label"), "note": l.get("note", ""),
                "tag": l.get("group", "索引"), "color": "#14b8a6", "url": link_href(l),
            })
    watch["items"] = items
    c["watchlist"] = watch

    showcase = dict(c.get("showcase") or {})
    showcase["works"] = [
        {"title": l.get("label"), "tag": l.get("group", "索引"), "color": "#171310",
         "icon": l.get("icon", "🔗"), "slug": l.get("id")}
        for l in links
    ]
    c["showcase"] = showcase

    pc = dict(c.get("pc") or {})
    stats = list(pc.get("stats") or [])
    for s in stats:
        if s.get("label") == "索引条目":
            s["value"] = len(links)
    pc["stats"] = stats
    c["pc"] = pc
    return c


def build_data_js(content: dict) -> str:
    payload = json.dumps(content, ensure_ascii=False, indent=2)
    return (
        "/* 自动生成：desk build —— 内容来自 data/content.json + data/content.local.json */\n"
        "(function () {\n"
        "  window.DESK_DATA = " + payload + ";\n"
        "  window.DESK_DATA.showcase.link = function (slug) {\n"
        "    return /^https?:/.test(slug) ? slug : '/api/open?id=' + encodeURIComponent(slug);\n"
        "  };\n"
        "  window.DESK_LABELS = " + json.dumps(content.get("labels", {}), ensure_ascii=False, indent=2) + ";\n"
        "})();\n"
    )


def build_snapshots() -> dict:
    gen = {
        "today.json": load_json(GEN / "today.json", {"date": today(), "generatedAt": "", "items": [], "stats": {"running": 0, "replied": 0, "cancelled": 0, "error": 0, "spaces": 0, "auto": 0}}),
        "gallery.json": load_json(GEN / "gallery.json", []),
        "uploads.json": load_json(GEN / "uploads.json", []),
        "sessions.json": load_json(GEN / "sessions.json", {}),
    }
    js = {
        "today.js": "/* 自动生成：desk build */\nwindow.DESK_TODAY = " + json.dumps(gen["today.json"], ensure_ascii=False, separators=(",", ":")) + ";\n",
        "gallery.js": "/* 自动生成：desk build */\nwindow.DESK_GALLERY = " + json.dumps(gen["gallery.json"], ensure_ascii=False, separators=(",", ":")) + ";\n",
        "uploads.js": "/* 自动生成：desk build */\nwindow.DESK_UPLOADS = " + json.dumps(gen["uploads.json"], ensure_ascii=False, separators=(",", ":")) + ";\n",
        "daily-sessions.js": "/* 自动生成：desk build */\nwindow.DESK_DAILY_SESSIONS = " + json.dumps(gen["sessions.json"], ensure_ascii=False, separators=(",", ":")) + ";\n",
        "digest.js": "/* 自动生成：desk build */\nwindow.DESK_DIGEST = null;\n",
        "digest-versions.js": "/* 自动生成：desk build */\nwindow.DESK_DIGEST_VERSIONS = [];\n",
    }
    for name, obj in gen.items():
        write_json(GEN / name, obj)
    for name, body in js.items():
        (APP / "js" / name).write_text(body, encoding="utf-8")
    (APP / "js" / "notes-board.js").write_text(render_notes_js(), encoding="utf-8")
    (APP / "js" / "todos-board.js").write_text(render_todos_js(), encoding="utf-8")
    return gen


def build_index(content: dict, links: list[dict], gen: dict) -> str:
    labels = content.get("labels", {})
    schedule = load_json(DATA / "schedule.json", {"jobs": []}) or {"jobs": []}
    rows = []
    for l in links:
        rows.append(
            "<tr><td><b>{}</b></td><td>{}</td><td><code>{}</code></td><td>{}</td></tr>".format(
                htmlmod.escape(str(l.get("label", ""))), htmlmod.escape(str(l.get("group", ""))),
                htmlmod.escape(str(l.get("type", ""))), htmlmod.escape(str(l.get("target", ""))),
            )
        )
    obj_rows = []
    for k, v in labels.items():
        obj_rows.append("<tr><td><code>{}</code></td><td>{}</td><td>{}</td></tr>".format(
            htmlmod.escape(k), htmlmod.escape(v.get("zh", "")), htmlmod.escape(v.get("en", ""))))
    job_rows = []
    for j in schedule.get("jobs", []):
        job_rows.append("<tr><td><code>{}</code></td><td>{}</td><td>{}</td><td><code>{}</code></td></tr>".format(
            htmlmod.escape(str(j.get("id", ""))), htmlmod.escape(str(j.get("when", ""))),
            htmlmod.escape(str(j.get("prompt", ""))[:120]), htmlmod.escape(str(j.get("output", "")))))
    data_files = []
    for p in sorted(DATA.rglob("*")):
        if p.is_file() and p.suffix in (".json", ".jsonl", ".md"):
            data_files.append("<tr><td><a href=\"/data/{}\">{}</a></td><td>{}</td></tr>".format(
                htmlmod.escape(str(p.relative_to(DATA))), htmlmod.escape(str(p.relative_to(DATA))), p.stat().st_size))
    body = f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>索引 · 我的本地工作台</title>
<style>
:root{{--ink:#171310;--paper:#f6eeda;--red:#e5484d;--teal:#14b8a6;--blue:#2f6df6}}
*{{box-sizing:border-box}}body{{margin:0;background:#d9cbb2;color:var(--ink);font:15px/1.65 -apple-system,BlinkMacSystemFont,"PingFang SC","Noto Sans SC",sans-serif}}
.wrap{{max-width:1000px;margin:32px auto 80px;padding:0 20px}}
.card{{background:var(--paper);border:4px solid var(--ink);box-shadow:8px 8px 0 var(--ink);padding:26px 28px;margin:22px 0}}
h1{{font-size:34px;margin:0 0 6px;letter-spacing:-.5px}}h2{{font-size:21px;margin:0 0 12px}}
p.sub{{margin:0 0 4px;color:#6b6257}}code{{background:#fff;border:1.5px solid var(--ink);padding:1px 6px;font-size:13px}}
table{{width:100%;border-collapse:collapse;margin-top:8px}}td,th{{border-bottom:1.5px solid #cfc0a4;padding:7px 8px;text-align:left;vertical-align:top}}
th{{font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:#6b6257}}a{{color:var(--blue)}}
.badge{{display:inline-block;background:var(--teal);color:#fff;border:2px solid var(--ink);padding:2px 8px;font-size:12px;font-weight:700;margin-right:6px}}
</style></head><body><div class="wrap">
<div class="card"><span class="badge">LOCAL</span><span class="badge">INDEX</span>
<h1>我的本地工作台 · 索引</h1>
<p class="sub">生成于 {htmlmod.escape(iso())} · 数据都在 <code>data/</code> · 引擎在 <code>app/</code></p></div>
<div class="card"><h2>物件（{len(labels)}）</h2><table><tr><th>id</th><th>中文</th><th>English</th></tr>{''.join(obj_rows)}</table></div>
<div class="card"><h2>链接（{len(links)}）</h2><table><tr><th>名称</th><th>分组</th><th>类型</th><th>指向</th></tr>{''.join(rows)}</table></div>
<div class="card"><h2>交给 agent 的定时（{len(schedule.get('jobs', []))}）</h2><p class="sub">桌面不装 cron；这些只是 prompt 清单，由你本地的 agent 或 launchd 唤醒。</p><table><tr><th>id</th><th>when</th><th>prompt</th><th>output</th></tr>{''.join(job_rows)}</table></div>
<div class="card"><h2>数据文件</h2><table><tr><th>文件</th><th>bytes</th></tr>{''.join(data_files)}</table></div>
<div class="card"><h2>读法</h2><p>今天：<code>data/generated/today.json</code> · 便签：<code>data/notes.jsonl</code> · 待办：<code>data/todos.jsonl</code> · 图片：<code>data/generated/gallery.json</code></p>
<p>命令行：<code>desk sync</code> · <code>desk build</code> · <code>desk serve</code> · <code>desk doctor</code> · <code>desk index</code></p></div>
</div></body></html>"""
    (APP / "catalog.html").write_text(body, encoding="utf-8")
    md = ["# 索引 · 我的本地工作台", "", f"生成于 {iso()}。数据在 `data/`，引擎在 `app/`。", "", "## 物件", "", "| id | 中文 | English |", "|---|---|---|"]
    for k, v in labels.items():
        md.append(f"| `{k}` | {v.get('zh','')} | {v.get('en','')} |")
    md += ["", "## 链接", "", "| 名称 | 分组 | 类型 | 指向 |", "|---|---|---|---|"]
    for l in links:
        md.append(f"| {l.get('label','')} | {l.get('group','')} | `{l.get('type','')}` | `{l.get('target','')}` |")
    md += ["", "## 交给 agent 的定时", "", "| id | when | prompt | output |", "|---|---|---|---|"]
    for j in schedule.get("jobs", []):
        md.append(f"| `{j.get('id','')}` | {j.get('when','')} | {j.get('prompt','')} | `{j.get('output','')}` |")
    (ROOT / "INDEX.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return body


def build() -> dict:
    content = _inject_index(load_content(), load_links().get("links", []))
    (APP / "js" / "data.js").write_text(build_data_js(content), encoding="utf-8")
    gen = build_snapshots()
    build_index(content, load_links().get("links", []), gen)
    write_json(GEN / "state.json", {"builtAt": iso(), "links": len(load_links().get("links", [])), "items": len(gen["today.json"].get("items", []))})
    return {"ok": True, "links": len(load_links().get("links", [])), "items": len(gen["today.json"].get("items", [])), "builtAt": iso()}
