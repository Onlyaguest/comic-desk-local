"""点星提示只是一条链接：不联网、不上报，只在浏览器本地计数。"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = ROOT / 'app' / 'fusion' / 'star-nudge.js'


class TestStarNudge(unittest.TestCase):
    def test_offline_only(self):
        src = JS.read_text(encoding='utf-8')
        for bad in ('fetch(', 'XMLHttpRequest', 'sendBeacon', 'WebSocket', 'EventSource', 'new Image', 'import('):
            self.assertNotIn(bad, src, bad)
        urls = set(re.findall(r'https?://[^\s\'"<>]+', src))
        self.assertEqual(urls, {'https://github.com/Onlyaguest/comic-desk-local'})
        self.assertIn('localStorage', src)
        self.assertIn('别再提示', src)

    def test_loaded_on_desk(self):
        html = (ROOT / 'app' / 'index.html').read_text(encoding='utf-8')
        self.assertIn('/desk-v2/star-nudge.js', html)


if __name__ == '__main__':
    unittest.main()
