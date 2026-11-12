"""本地数据源适配器：Claude Code / Codex 的会话记录，以及本地图片文件夹。

原则：只读、尽力解析、解析不了就跳过并在 doctor 里说明。
"""
from __future__ import annotations
import json, os, re
from datetime import datetime, timezone, timedelta
from pathlib import Path

from .paths import ROOT, DATA, GEN, load_json, write_json, iso, today, expand, rel

CST = timezone(timedelta(hours=8))
IMG = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".avif"}
SKIP = re.compile(r"^(<local-command|Caveat:|<command-name>|<command-message>|\[Request interrupted)")


def _ts(v):
    if not v:
        return None
    try:
        if isinstance(v, (int, float)):
            return datetime.fromtimestamp(v / (1000 if v > 1e12 else 1), CST)
        s = str(v).replace("Z", "+00:00")
        d = datetime.fromisoformat(s)
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return d.astimezone(CST)
    except Exception:
        return None


def _text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        out = []
        for b in content:
            if isinstance(b, str):
                out.append(b)
            elif isinstance(b, dict):
                if b.get("type") in ("text", "input_text", "output_text") and b.get("text"):
                    out.append(str(b["text"]))
                elif b.get("type") == "message" and b.get("text"):
                    out.append(str(b["text"]))
        return "\n".join(out)
    if isinstance(content, dict) and content.get("text"):
        return str(content["text"])
    return ""


def _clean(t: str, n=180) -> str:
    t = re.sub(r"```.*?```", "[代码]", t or "", flags=re.S)
    t = re.sub(r"\s+", " ", t).strip()
    if SKIP.match(t):
        return ""
    return t if len(t) <= n else t[: n - 1] + "…"


def _parse_jsonl(path: Path):
    """返回 [(role, text, dt)]；兼容 Claude Code 与 Codex 两种行形状。"""
    out = []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return out
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except Exception:
            continue
        dt = _ts(o.get("timestamp") or o.get("time") or (o.get("payload") or {}).get("timestamp"))
        # Claude Code
        msg = o.get("message") if isinstance(o.get("message"), dict) else None
        if msg:
            role = msg.get("role") or o.get("type")
            txt = _text(msg.get("content"))
            if role in ("user", "assistant") and txt:
                out.append((role, txt, dt))
            continue
        # Codex / 通用
        payload = o.get("payload") if isinstance(o.get("payload"), dict) else None
        if payload:
            typ = payload.get("type")
            role = payload.get("role") or o.get("role")
            if not role and typ in ("agent_message", "user_message"):
                role = "assistant" if typ == "agent_message" else "user"
            txt = _text(payload.get("content")) or _text(payload.get("message")) or _text(payload.get("text"))
            if role in ("user", "assistant") and txt:
                out.append((role, txt, dt))
            continue
        role = o.get("role") or o.get("type")
        txt = _text(o.get("content")) or _text(o.get("text"))
        if role in ("user", "assistant") and txt:
            out.append((role, txt, dt))
    return out


def _roots(config: dict) -> list[Path]:
    roots = []
    for r in config.get("transcriptRoots") or []:
        roots.append(expand(r))
    home = Path.home()
    if not config.get("transcriptRoots"):
        roots += [home / ".claude" / "projects", home / ".codex" / "sessions"]
    seen, out = set(), []
    for r in roots:
        if r.exists() and str(r) not in seen:
            seen.add(str(r)); out.append(r)
    return out


def scan_sessions(config: dict | None = None) -> list[dict]:
    config = config or {}
    sessions = []
    for root in _roots(config):
        for p in root.rglob("*.jsonl"):
            rows = _parse_jsonl(p)
            if not rows:
                continue
            user = [(t, d) for role, t, d in rows if role == "user" and _clean(t)]
            asst = [(t, d) for role, t, d in rows if role == "assistant" and _clean(t)]
            if not user:
                continue
            # 只保留今天有提问的会话
            today_user = [(t, d) for t, d in user if d and d.strftime("%Y-%m-%d") == today()]
            if not today_user:
                continue
            first_text = _clean(user[0][0], 60) or p.stem
            times = [d for _, d in user + asst if d]
            last_user = max(d for _, d in today_user if d)
            last_asst = max((d for _, d in asst if d), default=None)
            status = "replied" if (last_asst and last_asst >= last_user) else "running"
            sessions.append({
                "id": p.stem, "source": "claude" if "claude" in str(p).lower() else "codex",
                "title": first_text, "path": str(p), "cwd": p.parent.name,
                "first": min(times).strftime("%H:%M") if times else "",
                "last": last_user.strftime("%H:%M"),
                "ask": _clean(today_user[-1][0], 120),
                "asks": len(today_user), "status": status,
            })
    sessions.sort(key=lambda s: s.get("last", ""), reverse=True)
    return sessions


def build_today(sessions: list[dict]) -> dict:
    items = []
    for s in sessions:
        items.append({
            "id": s["id"], "source": s["source"], "space": "本地",
            "session": s["title"], "ask": s["ask"], "asks": s["asks"],
            "first": s["first"], "last": s["last"], "status": s["status"], "url": "",
        })
    stats = {
        "running": sum(1 for x in items if x["status"] == "running"),
        "replied": sum(1 for x in items if x["status"] == "replied"),
        "cancelled": 0, "error": 0, "spaces": 1, "auto": 0,
    }
    return {"date": today(), "generatedAt": iso(), "items": items, "stats": stats}


def build_sessions_json(sessions: list[dict]) -> dict:
    out = {}
    for s in sessions:
        key = today()  # 适配器只收今天；保留日期键，页面按天取
        out.setdefault(key, {"id": s["id"], "title": s["title"], "source": s["source"]})
    return out


def _img_entries(paths: list[Path], prefix: str) -> list[dict]:
    out, seen = [], set()
    for p in paths:
        if p.is_file() and p.suffix.lower() in IMG:
            files = [p]
        elif p.is_dir():
            files = [x for x in p.rglob("*") if x.is_file() and x.suffix.lower() in IMG]
        else:
            continue
        for f in files:
            key = str(f.resolve())
            if key in seen:
                continue
            seen.add(key)
            try:
                st = f.stat()
            except Exception:
                continue
            out.append({
                "url": "/media?path=" + str(f.resolve()), "title": f.stem,
                "created": datetime.fromtimestamp(st.st_mtime, CST).isoformat(timespec="seconds"),
                "src": prefix, "bytes": st.st_size,
            })
    out.sort(key=lambda x: x.get("created", ""), reverse=True)
    return out


def build_gallery(config: dict | None = None) -> list[dict]:
    config = config or {}
    dirs = [expand(x) for x in (config.get("galleryDirs") or ["data/uploads"])]
    return _img_entries(dirs, "gallery")


def build_uploads(config: dict | None = None) -> list[dict]:
    config = config or {}
    dirs = [expand(x) for x in (config.get("uploadDirs") or ["data/uploads"])]
    return _img_entries(dirs, "upload")[:60]


def sync(config: dict | None = None) -> dict:
    config = config or load_json(DATA / "config.json", {}) or {}
    sessions = scan_sessions(config)
    today_json = build_today(sessions)
    write_json(GEN / "today.json", today_json)
    write_json(GEN / "sessions.json", build_sessions_json(sessions))
    write_json(GEN / "gallery.json", build_gallery(config))
    write_json(GEN / "uploads.json", build_uploads(config))
    return {
        "ok": True, "sessions": len(sessions), "items": len(today_json["items"]),
        "gallery": len(load_json(GEN / "gallery.json", [])),
        "roots": [str(r) for r in _roots(config)],
    }


def doctor() -> dict:
    from .indexdb import config
    demo = config().get("demo", True)
    home = Path.home()
    agents = {}
    for name, cmd, root in [
        ("claude", "claude", home / ".claude" / "projects"),
        ("codex", "codex", home / ".codex" / "sessions"),
    ]:
        import shutil
        agents[name] = {"binary": shutil.which(cmd), "transcripts": not demo and root.exists() and sum(1 for _ in root.rglob("*.jsonl")) or 0}
    return {
        "python": os.sys.version.split()[0],
        "root": str(ROOT),
        "agents": agents,
        "data": {
            "content": (DATA / "content.json").exists(),
            "links": (DATA / "links.json").exists(),
            "notes": (DATA / "notes.jsonl").exists(),
            "todos": (DATA / "todos.jsonl").exists(),
        },
    }
