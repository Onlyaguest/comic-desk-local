"""本地动作：便签、待办、刷新、打开链接、派给 agent、定时清单。"""
from __future__ import annotations
import os, re, shutil, subprocess, sys, webbrowser
from datetime import datetime, timedelta
from pathlib import Path

from .paths import ROOT, DATA, GEN, load_json, write_json, iso, today, expand, now as now_cst
from .store import Notes, Todos
from . import adapters, build as builder


def _links() -> list[dict]:
    return (load_json(DATA / "links.json", {}) or {}).get("links", [])


def open_link(payload: dict) -> dict:
    lid = payload.get("id")
    link = next((l for l in _links() if l.get("id") == lid), None)
    if not link:
        # 允许直接传 target
        link = {"id": lid, "type": payload.get("type", "url"), "target": payload.get("target", "")}
    t, target = link.get("type"), str(link.get("target", ""))
    if not target:
        raise ValueError("这条链接没有 target")
    if t == "url":
        webbrowser.open(target)
    elif t == "app":
        if sys.platform == "darwin":
            subprocess.Popen(["open", "-a", target])
        else:
            subprocess.Popen([target])
    elif t in ("folder", "file"):
        if target.startswith("~"):
            p = Path(os.path.expanduser(target))
        elif os.path.isabs(target):
            p = Path(target)
        else:
            p = (ROOT / target).resolve()
        if not p.exists():
            raise FileNotFoundError(f"找不到：{p}")
        if sys.platform == "darwin":
            subprocess.Popen(["open", str(p)])
        else:
            webbrowser.open(p.as_uri())
    elif t == "command":
        if not link.get("allowCommand"):
            raise PermissionError("command 类型默认不执行；在 links.json 里给这条加 \"allowCommand\": true")
        subprocess.Popen(target, shell=True)
    else:
        raise ValueError(f"不认识的链接类型：{t}")
    return {"ok": True, "opened": lid, "type": t, "target": target}


def _agent_cmd(agent: str) -> list[str] | None:
    if agent in ("auto", "", None):
        if shutil.which("claude"):
            agent = "claude"
        elif shutil.which("codex"):
            agent = "codex"
        else:
            return None
    if agent == "claude" and shutil.which("claude"):
        return ["claude", "-p"]
    if agent == "codex" and shutil.which("codex"):
        return ["codex", "exec"]
    return None


def run_agent(prompt: str, agent: str = "auto", timeout: int = 600) -> dict:
    cmd = _agent_cmd(agent)
    if not cmd:
        raise RuntimeError("本机没找到 claude 或 codex 命令；先装一个，或在 config.json 里写 agent")
    p = subprocess.run(cmd + [prompt], capture_output=True, text=True, timeout=timeout, cwd=str(ROOT))
    if p.returncode != 0:
        raise RuntimeError((p.stderr or p.stdout or "agent 执行失败").strip()[-1200:])
    return {"ok": True, "agent": agent, "output": (p.stdout or "").strip()}


def ask(payload: dict) -> dict:
    if not payload.get("confirm"):
        raise PermissionError("派活会花你的额度：调用时加 {\"confirm\": true}，或用命令行 desk ask")
    return run_agent(payload.get("text", ""), payload.get("agent", "auto"))


def digest(payload: dict) -> dict:
    day = payload.get("date") or today()
    d = DATA / "digest" / f"{day}.md"
    if d.exists():
        return {"ok": True, "date": day, "md": d.read_text(encoding="utf-8"), "path": str(d)}
    return {
        "ok": False, "date": day,
        "error": f"还没有 {day} 的总结。运行 `desk digest`，它会把 prompt 交给本地 agent；或直接写 {d}",
    }


def refresh(payload: dict) -> dict:
    from . import indexapi
    job = indexapi.start_job()
    j = load_json(GEN / "today.json", {}) or {}
    return {"ok": True, "job": job, "today": j}


def note(payload: dict) -> dict:
    return {"ok": True, **Notes().op(payload)}


def todo(payload: dict) -> dict:
    if payload.get("op") == "refresh":
        from . import indexapi
        indexapi.write_today()
        tj = load_json(GEN / "today.json", {}) or {}
        existing = {x.get("id"): x for x in Todos()._items().values()}
        new, touched = [], 0
        day = tj.get("date") or today()
        for it in tj.get("items", []):
            rid = f"s:{day}:{it.get('id')}"
            body = {
                "id": rid, "text": it.get("ask") or it.get("session") or "",
                "kind": "session", "session": it.get("session"), "status": it.get("status"),
                "asks": it.get("asks"), "first": it.get("first"), "last": it.get("last"),
                "url": it.get("url", ""), "day": day, "tag": "今天", "by": "sync",
            }
            if rid not in existing:
                new.append(body)
            else:
                cur = existing[rid]
                if cur.get("state") == "open" and (cur.get("text") != body["text"] or cur.get("asks") != body["asks"]):
                    Todos().op({"op": "update", **body})
                    touched += 1
        if new:
            Todos().op({"op": "import", "items": new})
        return {"ok": True, "added": len(new), "touched": touched, **Todos().list()}
    return {"ok": True, **Todos().op(payload)}


def schedule_due(now: datetime | None = None) -> list[dict]:
    now = now or now_cst()
    sched = load_json(DATA / "schedule.json", {"jobs": []}) or {"jobs": []}
    state = load_json(DATA / "schedule-state.json", {}) or {}
    due = []
    for j in sched.get("jobs", []):
        if not j.get("enabled", True):
            continue
        jid, when = j.get("id"), str(j.get("when", ""))
        last = state.get(jid, {}).get("last")
        last_dt = None
        if last:
            try:
                last_dt = datetime.fromisoformat(last)
            except Exception:
                pass
        m = re.match(r"daily\s+(\d{1,2}):(\d{2})", when)
        if m:
            hh, mm = int(m.group(1)), int(m.group(2))
            target = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
            if now >= target and (not last_dt or last_dt < target):
                due.append(j)
            continue
        m = re.match(r"every\s+(\d+)\s*m", when)
        if m:
            mins = int(m.group(1))
            if not last_dt or now - last_dt >= timedelta(minutes=mins):
                due.append(j)
            continue
        # 不认识的写法：只在从未跑过时提醒一次
        if not last_dt:
            due.append(j)
    for j in due:
        j["_prompt"] = (j.get("prompt") or "").replace("YYYY-MM-DD", today()).replace("{date}", today())
    return due


def schedule_mark(job_id: str) -> None:
    p = DATA / "schedule-state.json"
    state = load_json(p, {}) or {}
    state[job_id] = {"last": iso()}
    write_json(p, state)


def schedule_tick(run: bool = False, agent: str = "auto") -> dict:
    due = schedule_due()
    out = []
    for j in due:
        rec = {"id": j.get("id"), "when": j.get("when"), "prompt": j.get("_prompt")}
        if run:
            try:
                rec.update(run_agent(rec["prompt"], j.get("agent", agent)))
                schedule_mark(j["id"])
            except Exception as e:
                rec["error"] = str(e)
        out.append(rec)
    return {"ok": True, "due": out, "ran": bool(run)}


def dispatch(action: str, payload: dict) -> dict:
    table = {
        "notes": note, "todos": todo, "refresh-today": refresh,
        "daily-digest": digest, "open": open_link, "prompt": ask,
        "schedule": lambda p: schedule_tick(bool(p.get("run")), p.get("agent", "auto")),
    }
    fn = table.get(action)
    if not fn:
        raise ValueError(f"不认识的动作：{action}")
    return fn(payload or {})
