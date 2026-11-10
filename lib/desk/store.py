"""便签与待办：append-only JSONL 的真相层，以及给页面用的快照。"""
from __future__ import annotations
import hashlib
from typing import Any

from .paths import DATA, load_json, append_jsonl, read_jsonl, iso, today, write_json

NOTES = DATA / "notes.jsonl"
TODOS = DATA / "todos.jsonl"
NOTE_COLORS = ["#ffd23f", "#ff8fb1", "#8ee6c8", "#9ec5ff", "#ffb020", "#c9b6ff", "#b8e986"]


def _rot(text: str) -> int:
    h = int(hashlib.sha1(text.encode("utf-8")).hexdigest()[:6], 16)
    return (h % 7) - 3


class Notes:
    def __init__(self, path=NOTES):
        self.path = path

    def list(self) -> dict:
        rows = read_jsonl(self.path)
        active: dict[str, dict] = {}
        archive: list[dict] = []
        for r in rows:
            op, rid = r.get("op"), r.get("id")
            if not rid:
                continue
            if op == "add":
                rec = {
                    "id": rid, "text": r.get("text", ""), "color": r.get("color") or NOTE_COLORS[0],
                    "rot": r.get("rot", _rot(rid)), "born": r.get("at", iso()), "updated": r.get("at", iso()),
                    "by": r.get("by", "page"),
                }
                active[rid] = rec
            elif op == "edit" and rid in active:
                active[rid]["text"] = r.get("text", active[rid]["text"])
                active[rid]["updated"] = r.get("at", iso())
            elif op == "del" and rid in active:
                rec = active.pop(rid)
                rec["delAt"] = r.get("at", iso())
                rec["reason"] = r.get("reason", "在桌上撕掉")
                archive.insert(0, rec)
            elif op == "restore":
                found = next((x for x in archive if x["id"] == rid), None)
                if found:
                    archive.remove(found)
                    found.pop("delAt", None); found.pop("reason", None)
                    found["updated"] = r.get("at", iso())
                    active[rid] = found
        board = sorted(active.values(), key=lambda x: str(x.get("born", "")), reverse=True)
        return {
            "schema": "comic-desk.notes.log.v1", "at": iso(), "events": len(rows),
            "nextRot": (_rot(str(len(rows))) + 3), "board": board, "archive": archive,
        }

    def op(self, payload: dict) -> dict:
        op = payload.get("op", "list")
        if op == "list":
            return self.list()
        if op == "add":
            text = (payload.get("text") or "").strip()
            if not text:
                raise ValueError("便签不能是空的")
            rid = payload.get("id") or f"n-{iso().replace('-', '').replace(':', '').replace('+', '')[:15]}"
            append_jsonl(self.path, {
                "op": "add", "id": rid, "text": text[:400],
                "color": payload.get("color") or NOTE_COLORS[len(read_jsonl(self.path)) % len(NOTE_COLORS)],
                "rot": payload.get("rot", _rot(rid)), "at": iso(), "by": payload.get("by", "page"),
            })
            return self.list()
        if op == "edit":
            if not payload.get("id"):
                raise ValueError("缺 id")
            text = (payload.get("text") or "").strip()
            if not text:
                raise ValueError("便签不能是空的")
            append_jsonl(self.path, {"op": "edit", "id": payload["id"], "text": text[:400], "at": iso(), "by": payload.get("by", "page")})
            return self.list()
        if op == "del":
            append_jsonl(self.path, {"op": "del", "id": payload.get("id"), "reason": payload.get("reason", "在桌上撕掉"), "at": iso(), "by": payload.get("by", "page")})
            return self.list()
        if op == "restore":
            append_jsonl(self.path, {"op": "restore", "id": payload.get("id"), "at": iso(), "by": payload.get("by", "page")})
            return self.list()
        raise ValueError(f"不认识的便签操作：{op}")


class Todos:
    def __init__(self, path=TODOS):
        self.path = path

    def _items(self) -> dict[str, dict]:
        items: dict[str, dict] = {}
        seq = 0
        for r in read_jsonl(self.path):
            op, rid = r.get("op"), r.get("id")
            if not rid:
                continue
            seq += 1
            if op == "add" or op == "import":
                rec = {
                    "id": rid, "kind": r.get("kind", "manual"), "state": "open",
                    "text": r.get("text", ""), "day": r.get("day", today()),
                    "born": r.get("at", iso()), "updated": r.get("at", iso()), "seq": seq,
                    "by": r.get("by", "page"),
                }
                for k in ("tag", "session", "space", "url", "status", "asks", "first", "last"):
                    if r.get(k) is not None:
                        rec[k] = r[k]
                items[rid] = rec
            elif rid in items:
                if op == "edit":
                    items[rid]["text"] = r.get("text", items[rid]["text"])
                elif op == "done":
                    items[rid]["state"] = "done"; items[rid]["doneAt"] = r.get("at", iso())
                elif op == "reopen":
                    items[rid]["state"] = "open"; items[rid].pop("doneAt", None)
                elif op == "drop":
                    items[rid]["state"] = "dropped"; items[rid]["reason"] = r.get("reason", "")
                elif op == "update":
                    for k in ("text", "asks", "last", "first", "status", "url", "session", "space", "tag"):
                        if r.get(k) is not None:
                            items[rid][k] = r[k]
                items[rid]["updated"] = r.get("at", iso())
        return items

    def list(self) -> dict:
        items = self._items()
        d = today()
        vals = list(items.values())
        today_open = [x for x in vals if x.get("day") == d and x.get("state") == "open"]
        done_today = [x for x in vals if x.get("day") == d and x.get("state") == "done"]
        carry = [x for x in vals if str(x.get("day", "")) < d and x.get("state") == "open"]
        dropped = [x for x in vals if x.get("state") == "dropped"]
        order = lambda x: (str(x.get("last", "")), x.get("seq", 0))
        today_open.sort(key=order, reverse=True); done_today.sort(key=order, reverse=True)
        carry.sort(key=order, reverse=True); dropped.sort(key=order, reverse=True)
        return {
            "schema": "comic-desk.todos.log.v1", "at": iso(), "today": d, "events": len(read_jsonl(self.path)),
            "session": {}, "today_open": today_open, "carry": carry, "done_today": done_today,
            "dropped": dropped,
            "counts": {"open": len(today_open) + len(carry), "done": len(done_today), "carry": len(carry), "dropped": len(dropped)},
        }

    def op(self, payload: dict) -> dict:
        op = payload.get("op", "list")
        if op == "list":
            return self.list()
        if op in ("add", "import"):
            rows: list[dict[str, Any]] = payload.get("items") or [payload]
            for r in rows if op == "import" else [payload]:
                text = (r.get("text") or "").strip()
                if not text:
                    continue
                rid = r.get("id") or f"t-{iso().replace('-', '').replace(':', '').replace('+', '')[:15]}-{len(read_jsonl(self.path))}"
                append_jsonl(self.path, {
                    "op": "add", "id": rid, "text": text[:300], "tag": r.get("tag", ""),
                    "kind": r.get("kind", "manual"), "day": r.get("day", today()),
                    "at": iso(), "by": r.get("by", payload.get("by", "page")),
                    **({k: r[k] for k in ("session", "space", "url", "status", "asks", "first", "last") if r.get(k) is not None}),
                })
            return self.list()
        if op == "edit":
            append_jsonl(self.path, {"op": "edit", "id": payload.get("id"), "text": (payload.get("text") or "")[:300], "at": iso(), "by": "page"})
            return self.list()
        if op in ("done", "reopen", "drop", "update"):
            rec = {"op": op, "id": payload.get("id"), "reason": payload.get("reason", ""), "at": iso(), "by": "page"}
            for k in ("text", "asks", "last", "first", "status", "url", "session", "space", "tag"):
                if payload.get(k) is not None:
                    rec[k] = payload[k]
            append_jsonl(self.path, rec)
            return self.list()
        raise ValueError(f"不认识的待办操作：{op}")


def render_notes_js() -> str:
    board = Notes().list()
    body = "window.DESK_NOTES_BOARD = " + __import__("json").dumps(board, ensure_ascii=False, separators=(",", ":")) + ";"
    return "/* 自动生成：desk build —— 便签墙首屏快照（真相在 data/notes.jsonl） */\n" + body + "\n"


def render_todos_js() -> str:
    board = Todos().list()
    body = "window.DESK_TODOS = " + __import__("json").dumps(board, ensure_ascii=False, separators=(",", ":")) + ";"
    return "/* 自动生成：desk build —— 待办账本首屏快照（真相在 data/todos.jsonl） */\n" + body + "\n"
