"""命令行入口：desk install / serve / sync / build / doctor / open / ask / digest / schedule / import。"""
from __future__ import annotations
import argparse, json, os, shutil, subprocess, sys
from pathlib import Path

from .paths import ROOT, APP, DATA, GEN, ensure_dirs, load_json, write_json, iso, today
from . import adapters, build as builder, actions, server

LAUNCH = Path.home() / "Library" / "LaunchAgents" / "live.comicdesk.server.plist"


def _seed_if_missing() -> None:
    ensure_dirs()
    if not (DATA / "content.json").exists():
        seed = ROOT / "tools" / "make_seed.py"
        if seed.exists():
            subprocess.run([sys.executable, str(seed)], cwd=str(ROOT), check=False)


def cmd_install(args) -> int:
    _seed_if_missing()
    cfgp = DATA / "config.json"
    if not cfgp.exists():
        write_json(cfgp, {"agent": "auto", "transcriptRoots": [], "galleryDirs": ["data/uploads"], "uploadDirs": ["data/uploads"]})
    builder.build()
    # ~/bin/desk
    bindir = Path.home() / "bin"
    bindir.mkdir(exist_ok=True)
    link = bindir / "desk"
    try:
        if link.is_symlink() or link.exists():
            link.unlink()
        link.symlink_to(ROOT / "bin" / "desk")
    except Exception as e:
        print(f"[warn] 没建成 {link}: {e}")
    if args.login:
        LAUNCH.parent.mkdir(parents=True, exist_ok=True)
        LAUNCH.write_text(f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>live.comicdesk.server</string>
  <key>ProgramArguments</key><array>
    <string>{sys.executable}</string><string>{ROOT / 'bin' / 'desk'}</string><string>serve</string><string>--no-open</string>
  </array>
  <key>WorkingDirectory</key><string>{ROOT}</string>
  <key>RunAtLoad</key><true/><key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>{DATA / 'server.log'}</string>
  <key>StandardErrorPath</key><string>{DATA / 'server.err.log'}</string>
</dict></plist>
''', encoding="utf-8")
        subprocess.run(["launchctl", "unload", str(LAUNCH)], capture_output=True)
        subprocess.run(["launchctl", "load", str(LAUNCH)], capture_output=True)
        print(f"已装开机启动：{LAUNCH}")
    print(f"""
装好了。

  桌面目录  {ROOT}
  数据目录  {DATA}
  命令      {link}  （如果 PATH 里没有 ~/bin，先把它加进去）

启动：    desk serve
或双击：  start.command

第一次用：desk sync   # 扫描本机 Claude Code / Codex 的会话
""")
    return 0


def cmd_uninstall(args) -> int:
    link = Path.home() / "bin" / "desk"
    try:
        if link.is_symlink(): link.unlink()
    except Exception: pass
    if LAUNCH.exists():
        subprocess.run(["launchctl", "unload", str(LAUNCH)], capture_output=True)
        LAUNCH.unlink()
        print(f"已移除开机启动：{LAUNCH}")
    print(f"已移除命令链接。数据还在：{DATA}（要删就手动删这个目录）")
    return 0


def cmd_serve(args) -> int:
    _seed_if_missing()
    if not (APP / "js" / "data.js").exists():
        builder.build()
    server.serve(port=args.port, open_browser=not args.no_open, verbose=args.verbose)
    return 0


def cmd_sync(args) -> int:
    cfg = load_json(DATA / "config.json", {}) or {}
    r = adapters.sync(cfg)
    b = builder.build()
    print(json.dumps({**r, **b}, ensure_ascii=False, indent=2))
    return 0


def cmd_build(args) -> int:
    print(json.dumps(builder.build(), ensure_ascii=False, indent=2))
    return 0


def cmd_doctor(args) -> int:
    d = adapters.doctor()
    print(json.dumps(d, ensure_ascii=False, indent=2))
    return 0


def cmd_open(args) -> int:
    print(json.dumps(actions.open_link({"id": args.id}), ensure_ascii=False, indent=2))
    return 0


def cmd_ask(args) -> int:
    text = " ".join(args.text).strip()
    if not text:
        print("用法：desk ask \"要 agent 做的事\"", file=sys.stderr)
        return 2
    if not args.yes:
        print("这会调用本地 agent 并消耗额度。确认就加 --yes。", file=sys.stderr)
        return 2
    print(json.dumps(actions.run_agent(text, args.agent), ensure_ascii=False, indent=2))
    return 0


def cmd_digest(args) -> int:
    day = args.date or today()
    prompt = (f"读 data/generated/today.json、data/notes.jsonl、data/todos.jsonl，把 {day} 压成一份五条以内的日结，"
              f"写到 data/digest/{day}.md。只写本机真实发生的事；没有就写「今天为零」。")
    if args.run:
        print(actions.run_agent(prompt, args.agent)["output"])
    else:
        print(prompt)
        print(f"\n（交给本地 agent 跑：desk digest --run；或直接把上面这段发给你的 agent）", file=sys.stderr)
    return 0


def cmd_schedule(args) -> int:
    r = actions.schedule_tick(run=args.run, agent=args.agent)
    print(json.dumps(r, ensure_ascii=False, indent=2))
    return 0


def _eval_old_data_js(path: Path) -> dict:
    if not shutil.which("node"):
        raise RuntimeError("导入旧 content 需要 node（用来跑一遍旧 data.js）；没装就手动把内容写成 data/content.local.json")
    script = "global.window={};require(process.argv[1]);process.stdout.write(JSON.stringify(window.DESK_DATA||{}))"
    p = subprocess.run(["node", "-e", script, str(path)], capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr[-800:])
    return json.loads(p.stdout or "{}")


def cmd_import(args) -> int:
    src = Path(args.source).expanduser().resolve()
    if not src.exists():
        print(f"找不到：{src}", file=sys.stderr)
        return 2
    ensure_dirs()
    # 账本
    for a, b in [("notes/便签.log.jsonl", DATA / "notes.jsonl"), ("todos/待办.log.jsonl", DATA / "todos.jsonl")]:
        p = src / a
        if p.exists():
            if b.exists():
                b.replace(b.with_suffix(b.suffix + f".bak-{iso().replace(':','')}"))
            shutil.copy2(p, b)
            print(f"导入账本：{a} → {b}")
    # 内容
    js = src / "js" / "data.js"
    if js.exists():
        data = _eval_old_data_js(js)
        if args.with_assets:
            dst = APP / "assets" / "me"
            for sub in ("figures", "photos", "audio", "props", "voice"):
                s = src / "assets" / sub
                if s.exists():
                    shutil.copytree(s, dst / sub, dirs_exist_ok=True)
            raw = json.dumps(data, ensure_ascii=False)
            raw = raw.replace('"assets/', '"assets/me/')
            data = json.loads(raw)
        write_json(DATA / "content.local.json", data)
        print(f"导入内容：{js} → data/content.local.json" + ("（含素材）" if args.with_assets else "（没导素材，图片会缺）"))
    builder.build()
    print("完成。运行 desk serve 看效果。")
    return 0


def cmd_where(args) -> int:
    print(json.dumps({
        "root": str(ROOT), "app": str(APP), "data": str(DATA),
        "generated": str(GEN), "index": str(ROOT / "INDEX.md"),
    }, ensure_ascii=False, indent=2))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="desk", description="我的本地工作台")
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("install", help="建目录、建命令、可选开机启动")
    p.add_argument("--login", action="store_true", help="装 LaunchAgent，登录后自动启动")
    p.set_defaults(fn=cmd_install)
    p = sub.add_parser("uninstall", help="移除命令链接和开机启动（保留数据）")
    p.set_defaults(fn=cmd_uninstall)
    p = sub.add_parser("serve", help="启动本机页面")
    p.add_argument("--port", type=int, default=7777)
    p.add_argument("--no-open", action="store_true")
    p.add_argument("--verbose", action="store_true")
    p.set_defaults(fn=cmd_serve)
    p = sub.add_parser("sync", help="扫描本地 agent 会话与图片，再 build")
    p.set_defaults(fn=cmd_sync)
    p = sub.add_parser("build", help="把 data/ 编译成页面快照")
    p.set_defaults(fn=cmd_build)
    p = sub.add_parser("doctor", help="看看本机有什么 agent、transcript 在哪")
    p.set_defaults(fn=cmd_doctor)
    p = sub.add_parser("open", help="打开 links.json 里的一条链接")
    p.add_argument("id")
    p.set_defaults(fn=cmd_open)
    p = sub.add_parser("ask", help="把一句话派给本地 agent（会花额度）")
    p.add_argument("text", nargs="+")
    p.add_argument("--agent", default="auto", choices=["auto", "claude", "codex"])
    p.add_argument("--yes", action="store_true")
    p.set_defaults(fn=cmd_ask)
    p = sub.add_parser("digest", help="生成今天的日结 prompt / 交给 agent 跑")
    p.add_argument("--date", default="")
    p.add_argument("--run", action="store_true")
    p.add_argument("--agent", default="auto", choices=["auto", "claude", "codex"])
    p.set_defaults(fn=cmd_digest)
    p = sub.add_parser("schedule", help="看 / 跑 data/schedule.json 里到点的 prompt")
    p.add_argument("--run", action="store_true")
    p.add_argument("--agent", default="auto", choices=["auto", "claude", "codex"])
    p.set_defaults(fn=cmd_schedule)
    p = sub.add_parser("import", help="从旧版彩色漫画工作台导入账本与内容")
    p.add_argument("--from", dest="source", required=True)
    p.add_argument("--with-assets", action="store_true")
    p.set_defaults(fn=cmd_import)
    p = sub.add_parser("where", help="打印路径")
    p.set_defaults(fn=cmd_where)
    args = ap.parse_args(argv)
    if not getattr(args, "fn", None):
        ap.print_help()
        return 0
    try:
        return args.fn(args)
    except KeyboardInterrupt:
        return 130
    except Exception as e:
        print(f"出错：{e}", file=sys.stderr)
        return 1
