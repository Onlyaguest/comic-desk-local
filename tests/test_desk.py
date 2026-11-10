"""本地工作台的最小回归测试。运行：python3 -m unittest discover -s tests -v"""
import json, os, sys, tempfile, unittest
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))

from desk.store import Notes, Todos
from desk import adapters, build as builder


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
