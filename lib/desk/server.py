"""本机 HTTP 服务：静态页面 + /api。只绑 127.0.0.1。"""
from __future__ import annotations
import json, mimetypes, os, urllib.parse
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path

from .paths import ROOT, APP, DATA, GEN, load_json
from . import actions, adapters, indexapi

HOST = "127.0.0.1"
PORT = 7777
IMG = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".avif", ".svg"}


def _json(handler: BaseHTTPRequestHandler, code: int, obj) -> None:
    body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    handler.send_response(code)
    handler.send_header("content-type", "application/json; charset=utf-8")
    handler.send_header("content-length", str(len(body)))
    handler.send_header("cache-control", "no-store")
    handler.end_headers()
    handler.wfile.write(body)


def _html(handler: BaseHTTPRequestHandler, code: int, text: str) -> None:
    body = text.encode("utf-8")
    handler.send_response(code)
    handler.send_header("content-type", "text/html; charset=utf-8")
    handler.send_header("content-length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _safe_media(p: Path) -> bool:
    try:
        rp = p.resolve()
        rp.relative_to(ROOT.resolve())
        return True
    except Exception:
        pass
    try:
        rp.relative_to(Path.home().resolve())
        return True
    except Exception:
        return False


class Handler(BaseHTTPRequestHandler):
    server_version = "ComicDeskLocal/1.0"

    def log_message(self, fmt, *args):
        # 静音；要看日志用 desk serve --verbose
        if getattr(self.server, "verbose", False):
            super().log_message(fmt, *args)

    def _static(self, rel_path: str) -> None:
        p = (APP / rel_path.lstrip("/")).resolve()
        try:
            p.relative_to(APP.resolve())
        except Exception:
            return _html(self, 403, "403")
        if not p.exists() or p.is_dir():
            return _html(self, 404, "404 · 没有这个文件")
        ctype = mimetypes.guess_type(str(p))[0] or "application/octet-stream"
        body = p.read_bytes()
        self.send_response(200)
        self.send_header("content-type", ctype + ("; charset=utf-8" if ctype.startswith("text/") or ctype in ("application/javascript", "application/json") else ""))
        self.send_header("content-length", str(len(body)))
        self.send_header("cache-control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        path = u.path
        q = urllib.parse.parse_qs(u.query)
        host = self.headers.get("Host", "").split(":")[0]
        if host not in ("127.0.0.1", "localhost"):
            return _json(self, 403, {"error": "仅本机访问"})
        if indexapi.handle(self, "GET", path, q, _json):
            return
        if path == "/api/health":
            return _json(self, 200, {"ok": True, "root": str(ROOT)})
        if path == "/api/state":
            return _json(self, 200, {
                "ok": True,
                "today": load_json(GEN / "today.json", {}),
                "gallery": load_json(GEN / "gallery.json", []),
                "uploads": load_json(GEN / "uploads.json", []),
                "links": load_json(DATA / "links.json", {"links": []}),
                "schedule": load_json(DATA / "schedule.json", {"jobs": []}),
            })
        if path == "/api/open":
            lid = (q.get("id") or [""])[0]
            try:
                r = actions.open_link({"id": lid})
                return _html(self, 200, f"<!doctype html><meta charset=utf-8><body style='font:16px -apple-system;padding:40px'><h2>已打开</h2><p>{lid} → {r.get('target','')}</p><p style='color:#888'>可以关掉这一页了。</p>")
            except Exception as e:
                return _html(self, 400, f"<!doctype html><meta charset=utf-8><body style='font:16px -apple-system;padding:40px'><h2>没打开</h2><p>{e}</p>")
        if path.startswith("/data/"):
            p = (DATA / path[len("/data/"):]).resolve()
            try:
                p.relative_to(DATA.resolve())
            except Exception:
                return _html(self, 403, "403")
            if not p.exists() or p.is_dir():
                return _html(self, 404, "404")
            ctype = mimetypes.guess_type(str(p))[0] or "application/octet-stream"
            body = p.read_bytes()
            self.send_response(200)
            self.send_header("content-type", ctype)
            self.send_header("content-length", str(len(body)))
            self.send_header("cache-control", "no-store")
            self.end_headers()
            self.wfile.write(body)
            return
        if path == "/media":
            raw = (q.get("path") or [""])[0]
            p = Path(raw)
            if not p.is_absolute():
                p = (ROOT / raw).resolve()
            if p.suffix.lower() not in IMG or not p.exists() or not _safe_media(p):
                return _html(self, 404, "404")
            ctype = mimetypes.guess_type(str(p))[0] or "application/octet-stream"
            body = p.read_bytes()
            self.send_response(200)
            self.send_header("content-type", ctype)
            self.send_header("content-length", str(len(body)))
            self.send_header("cache-control", "max-age=60")
            self.end_headers()
            self.wfile.write(body)
            return
        if path in ("/catalog.html", "/README.md", "/METHOD.md"):
            p = ROOT / path.lstrip("/")
            if p.exists():
                if p.suffix == ".md":
                    body = ("<!doctype html><meta charset=utf-8><body style='max-width:860px;margin:40px auto;"
                            "font:16px/1.7 -apple-system;padding:0 20px;white-space:pre-wrap'>"
                            + p.read_text(encoding="utf-8").replace("&", "&amp;").replace("<", "&lt;") + "</body>").encode("utf-8")
                    self.send_response(200); self.send_header("content-type", "text/html; charset=utf-8")
                    self.send_header("content-length", str(len(body))); self.end_headers(); self.wfile.write(body)
                    return
                return self._static(path.lstrip("/"))
        if path == "/" or path == "":
            return self._static("index.html")
        return self._static(path)

    def do_POST(self):
        u = urllib.parse.urlparse(self.path)
        host = self.headers.get("Host", "")
        origin = self.headers.get("Origin")
        if host.split(":")[0] not in ("127.0.0.1", "localhost") or (origin and origin not in ("http://" + host,)):
            return _json(self, 403, {"error": "仅同源本机操作"})
        if self.headers.get("Sec-Fetch-Site") == "cross-site":
            return _json(self, 403, {"error": "拒绝跨站操作"})
        if indexapi.handle(self, "POST", u.path, {}, _json):
            return
        if u.path != "/api/action":
            return _json(self, 404, {"ok": False, "error": "not found"})
        n = int(self.headers.get("content-length") or 0)
        raw = self.rfile.read(n) if n else b"{}"
        try:
            payload = json.loads(raw.decode("utf-8") or "{}")
        except Exception:
            return _json(self, 400, {"ok": False, "error": "JSON 读不了"})
        action = payload.get("action")
        inp = payload.get("input") or {}
        try:
            r = actions.dispatch(action, inp)
            return _json(self, 200, r if isinstance(r, dict) else {"ok": True, "result": r})
        except Exception as e:
            return _json(self, 200, {"ok": False, "error": str(e)})


def serve(port: int = PORT, open_browser: bool = True, verbose: bool = False) -> None:
    httpd = ThreadingHTTPServer((HOST, port), Handler)
    httpd.verbose = verbose  # type: ignore
    url = f"http://{HOST}:{port}/"
    print(f"桌面已启动：{url}")
    print(f"数据目录：{DATA}")
    print("Ctrl+C 停止。")
    if open_browser:
        import threading, webbrowser
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止。")
    finally:
        httpd.server_close()
