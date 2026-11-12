"""本地工作台的最小回归测试。运行：python3 -m unittest discover -s tests -v"""
import json, os, sys, tempfile, unittest
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))

from desk.store import Notes, Todos
from desk import adapters, build as builder


class TestWorksCatalog(unittest.TestCase):
    def test_catalog_versions_preferences_and_assets(self):
        from unittest.mock import patch
        from desk import works, indexdb
        import urllib.request, urllib.error
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root/"report-v1.html").write_text("<title>旧报告</title>")
            (root/"report-v2.html").write_text('<title>新报告</title><link rel="stylesheet" href="style.css">')
            (root/"different.html").write_text("<title>另一个作品</title>")
            (root/"style.css").write_text("body{color:red}")
            (root/".env").write_text("secret")
            (root/"escape.html").symlink_to(Path(__file__))
            with patch.object(works,"CLOUD",root/"cloud.json"), patch.object(works,"STATE",root/"state.json"), patch.object(works,"META",root/"meta.json"), patch.object(indexdb,"DB",root/"index.db"):
                works.ingest_apps([{"id":"app","spaceId":"space","status":"published","publicUrl":"https://example.com/app","meta":{"title":"应用"},"updatedAt":"2026-11-12"}])
                with indexdb.connect() as c:
                    for i,name in enumerate(("report-v1.html","report-v2.html","different.html")):
                        c.execute("INSERT INTO artifacts(id,title,target,kind,updated) VALUES(?,?,?,'html','2026-11-12')",(str(i),name,str(root/name)))
                    rows=works.catalog(c)["items"]
                    self.assertEqual(len(rows),3)
                    report=next(x for x in rows if len(x["versions"])==2)
                    works.update(c,{"id":report["id"],"title":"我的报告","pinned":True,"preferred":"0"})
                    rows=works.catalog(c)["items"]
                    saved=next(x for x in rows if x["id"]==report["id"])
                    self.assertEqual(saved["title"],"我的报告")
                    self.assertTrue(saved["pinned"])
                    self.assertEqual(saved["preferred"],"0")
                    self.assertEqual(c.execute("SELECT count(*) FROM artifacts").fetchone()[0],3)
                    works.update(c,{"id":report["id"],"hidden":True})
                    self.assertTrue(next(x for x in works.catalog(c)["items"] if x["id"]==report["id"])["hidden"])
                url=works.preview_url(root/"report-v2.html")
                with urllib.request.urlopen(url) as response: self.assertIn(b"style.css",response.read())
                base=url.rsplit("/",1)[0]
                with urllib.request.urlopen(base+"/style.css") as response: self.assertIn(b"color:red",response.read())
                for name in (".env","escape.html"):
                    with self.assertRaises(urllib.error.HTTPError) as error: urllib.request.urlopen(base+"/"+name)
                    self.assertEqual(error.exception.code,403)
                server=works.PREVIEWS.pop(str(root.resolve()));server.shutdown();server.server_close()


class TestSourceContract(unittest.TestCase):
    def test_cover_rules_and_full_index_preserved(self):
        from desk import indexapi,indexdb
        from unittest.mock import patch
        candidates = [
            ("qr", "封面二维码", "/publish/cover-qr.png", "2026-11-12"),
            ("shot", "封面截图", "/publish/cover-screenshot.png", "2026-11-11"),
            ("preview", "preview.png", "/publish/preview.png", "2026-11-10"),
            ("final", "cover.jpg", "/publish/cover.jpg", "2026-11-09"),
            ("old", "海报终稿", "/output/poster.png", "2026-11-08"),
        ]
        with tempfile.TemporaryDirectory() as d, patch.object(indexdb, "DB", Path(d)/"index.db"):
            with indexdb.connect() as c:
                for key,title,target,date in candidates:
                    c.execute("INSERT INTO artifacts(id,title,target,kind,updated) VALUES(?,?,?,'image',?)",
                              (key,title,target,date))
                self.assertEqual(indexapi.cover_snapshot(c)["item"]["id"], "final")
                self.assertEqual(c.execute("SELECT count(*) FROM artifacts").fetchone()[0], 5)
                c.execute("DELETE FROM artifacts WHERE id IN ('final','old')")
                self.assertIsNone(indexapi.cover_snapshot(c)["item"])
        self.assertFalse(indexapi.cover_candidate({"title":"final.png","target":"/tmp/final.png"}))
        self.assertFalse(indexapi.cover_candidate({"title":"image","target":"/图片产物/%E6%88%AA%E5%9B%BE.png"}))
        self.assertFalse(indexapi.cover_candidate({"title":"unknown.png","target":"/publish/unknown.png"}))
        self.assertTrue(indexapi.cover_candidate({"title":"钟离月历","target":"/图片产物/月历.png"}))


    def test_today_includes_workbuddy_count(self):
        from unittest.mock import patch
        from desk import indexapi,indexdb
        with tempfile.TemporaryDirectory() as d, patch.object(indexdb,'DB',Path(d)/'index.db'):
            snapshot=indexapi.today_snapshot()
            self.assertEqual(snapshot['counts']['workbuddy'],0)


class TestSessionBoard(unittest.TestCase):
    def test_new_dialogue_reopens_without_erasing_completion(self):
        from unittest.mock import patch
        from datetime import timezone, timedelta
        from desk import indexdb
        with tempfile.TemporaryDirectory() as d, patch.object(indexdb, "DB", Path(d) / "index.db"):
            now = datetime.now(timezone.utc)
            first = (now - timedelta(minutes=2)).isoformat()
            second = (now - timedelta(minutes=1)).isoformat()
            with indexdb.connect() as c:
                c.execute("INSERT INTO sessions(id,engine,title,workspace,updated) VALUES(?,?,?,?,?)",
                          ("s", "codex", "task", "", first))
                c.execute("INSERT INTO messages VALUES(?,?,?,?,?)", ("s", 0, "user", first, "first"))
            path = Path(d) / "todos.jsonl"
            board = Todos(path, True)
            key = "indexed-session:s"
            board.op({"op": "done", "id": key})
            original = path.read_bytes()
            self.assertEqual(Todos(path, True)._items()[key]["state"], "done")
            with indexdb.connect() as c:
                c.execute("UPDATE sessions SET title='renamed',updated=?", (second,))
            self.assertEqual(board._items()[key]["state"], "done")
            with indexdb.connect() as c:
                c.execute("INSERT INTO messages VALUES(?,?,?,?,?)", ("s", 1, "assistant", second, "new reply"))
            self.assertEqual(Todos(path, True)._items()[key]["state"], "open")
            self.assertEqual(path.read_bytes(), original)
            board.op({"op": "done", "id": key})
            self.assertEqual(Todos(path, True)._items()[key]["state"], "done")
            with indexdb.connect() as c:
                c.execute("UPDATE messages SET text='new reply continued' WHERE seq=1")
            self.assertEqual(board._items()[key]["state"], "open")
            self.assertEqual(len(path.read_text().splitlines()), 2)
            self.assertTrue(path.read_bytes().startswith(original))
            board.op({"op": "drop", "id": key})
            with indexdb.connect() as c:
                c.execute("UPDATE messages SET text='more' WHERE seq=1")
            self.assertEqual(board._items()[key]["state"], "dropped")


    def test_window_dedup_and_persistent_completion(self):
        from unittest.mock import patch
        from desk import indexdb, store
        with tempfile.TemporaryDirectory() as d:
            db = Path(d) / "index.db"
            with patch.object(indexdb, "DB", db):
                with indexdb.connect() as c:
                    for sid, ts in [("old", "2026-11-10T15:59:59Z"),
                                    ("yesterday", "2026-11-10T16:00:00Z"),
                                    ("both", "2026-11-11T17:00:00Z")]:
                        c.execute("INSERT INTO sessions(id,engine,title,workspace,updated) VALUES(?,?,?,?,?)",
                                  (sid, "codex", sid, "", ts))
                    c.execute("INSERT INTO messages VALUES(?,?,?,?,?)",
                              ("both", 0, "user", "2026-11-11T01:00:00Z", "yesterday"))
                tasks = store.session_tasks("2026-11-12")
                self.assertEqual(len(tasks), 2)
                self.assertNotIn("indexed-session:old", tasks)
                self.assertEqual(tasks["indexed-session:yesterday"]["day"], "2026-11-11")
                self.assertEqual(tasks["indexed-session:both"]["day"], "2026-11-12")
                log = Path(d) / "todos.jsonl"
                with patch.object(store, "session_tasks", return_value=tasks):
                    board = Todos(log, include_sessions=True)
                    self.assertEqual(len(board._items()), 2)
                    from datetime import timezone, timedelta
                    current = datetime.now(timezone(timedelta(hours=8))).date()
                    tasks["indexed-session:both"]["day"] = current.isoformat()
                    tasks["indexed-session:yesterday"]["day"] = (current - timedelta(days=1)).isoformat()
                    self.assertEqual(len(board.list()["today_open"]), 1)
                    self.assertEqual(len(board.list()["carry"]), 1)
                    board.op({"op": "done", "id": "indexed-session:yesterday"})
                    self.assertEqual(Todos(log, True)._items()["indexed-session:yesterday"]["state"], "done")
                    tasks["indexed-session:yesterday"]["day"] = "2026-11-12"
                    self.assertEqual(Todos(log, True)._items()["indexed-session:yesterday"]["state"], "done")
                    board.op({"op": "reopen", "id": "indexed-session:yesterday"})
                    self.assertEqual(board._items()["indexed-session:yesterday"]["state"], "open")
                with indexdb.connect() as c:
                    self.assertEqual(c.execute("SELECT count(*) FROM sessions").fetchone()[0], 3)
                self.assertEqual(len(log.read_text().splitlines()), 2)


class TestNotes(unittest.TestCase):
    def test_add_edit_delete_restore(self):
        with tempfile.TemporaryDirectory() as d:
            n = Notes(Path(d) / "notes.jsonl")
            b = n.op({"op": "add", "text": "一", "id": "a"})
            self.assertEqual(b["board"][0]["text"], "一")
            n.op({"op": "edit", "id": "a", "text": "二"})
            self.assertEqual(n.list()["board"][0]["text"], "二")
            n.op({"op": "del", "id": "a"})
            self.assertEqual(len(n.list()["board"]), 0)
            self.assertEqual(len(n.list()["archive"]), 1)
            n.op({"op": "restore", "id": "a"})
            self.assertEqual(n.list()["board"][0]["text"], "二")


class TestTodos(unittest.TestCase):
    def test_old_completion_hidden_but_persisted(self):
        from datetime import timezone, timedelta
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "todos.jsonl"
            t = Todos(path)
            t.op({"op": "add", "id": "y", "text": "昨日完成"})
            yesterday = datetime.now(timezone(timedelta(hours=8))) - timedelta(days=1)
            with path.open("a") as f:
                f.write(json.dumps({"op": "done", "id": "y", "at": yesterday.isoformat()}) + "\n")
            before = path.read_bytes()
            board = Todos(path).list()
            self.assertEqual(board["done_today"], [])
            self.assertEqual(board["today_open"], [])
            self.assertEqual(board["carry"], [])
            self.assertEqual(Todos(path)._items()["y"]["state"], "done")
            self.assertEqual(path.read_bytes(), before)

    def test_add_done_reopen(self):
        with tempfile.TemporaryDirectory() as d:
            t = Todos(Path(d) / "todos.jsonl")
            t.op({"op": "add", "text": "做事", "id": "x"})
            self.assertEqual(len(t.list()["today_open"]), 1)
            t.op({"op": "done", "id": "x"})
            b = t.list()
            self.assertEqual(len(b["today_open"]), 0)
            self.assertEqual(len(b["done_today"]), 1)
            t.op({"op": "reopen", "id": "x"})
            self.assertEqual(len(t.list()["today_open"]), 1)


class TestAdapters(unittest.TestCase):
    def test_claude_and_codex(self):
        with tempfile.TemporaryDirectory() as d:
            day = datetime.now().strftime("%Y-%m-%d")
            p = Path(d) / "claude" / "proj"
            p.mkdir(parents=True)
            rows = [
                {"type": "user", "message": {"role": "user", "content": [{"type": "text", "text": "整理索引"}]}, "timestamp": f"{day}T09:00:00+08:00"},
                {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "好"}]}, "timestamp": f"{day}T09:01:00+08:00"},
            ]
            (p / "s1.jsonl").write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in rows), encoding="utf-8")
            q = Path(d) / "codex" / day
            q.mkdir(parents=True)
            rows2 = [
                {"timestamp": f"{day}T10:00:00+08:00", "type": "response_item", "payload": {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "看 todo"}]}},
                {"timestamp": f"{day}T10:01:00+08:00", "type": "event_msg", "payload": {"type": "agent_message", "message": "还差一条"}},
            ]
            (q / "r1.jsonl").write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in rows2), encoding="utf-8")
            s = adapters.scan_sessions({"transcriptRoots": [d]})
            self.assertEqual(len(s), 2)
            src = {x["source"] for x in s}
            self.assertEqual(src, {"claude", "codex"})
            t = adapters.build_today(s)
            self.assertEqual(len(t["items"]), 2)
            self.assertEqual(t["stats"]["replied"], 2)


class TestBuild(unittest.TestCase):
    def test_inject_index(self):
        content = {"books": [], "videos": {"sites": []}, "watchlist": {}, "showcase": {}, "pc": {"stats": []}}
        links = [{"id": "x", "label": "X", "group": "G", "type": "url", "target": "https://example.com"}]
        c = builder._inject_index(content, links)
        self.assertEqual(c["books"][0]["link"], "https://example.com")
        self.assertEqual(c["watchlist"]["items"][0]["url"], "https://example.com")
        self.assertEqual(c["showcase"]["works"][0]["slug"], "x")

    def test_data_js_is_valid_js(self):
        content = builder._inject_index(builder.load_content(), builder.load_links().get("links", []))
        js = builder.build_data_js(content)
        self.assertIn("window.DESK_DATA", js)
        self.assertIn("window.DESK_LABELS", js)


if __name__ == "__main__":
    unittest.main()
