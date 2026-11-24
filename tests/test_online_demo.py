"""在线样例版 demo/：只含虚构样例、不带本机路径、每页都先加载垫片、垫片不连别处。"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / 'demo'


@unittest.skipUnless((DEMO / '_demo' / 'shim.js').exists(), '还没生成 demo/')
class TestOnlineDemo(unittest.TestCase):
    def test_pages_load_shim_first(self):
        pages = [p for p in DEMO.rglob('*.html') if '_rec' not in p.parts and 'samples' not in p.parts]
        self.assertTrue(pages)
        for p in pages:
            head = p.read_text(encoding='utf-8')[:600]
            self.assertIn('_demo/shim.js', head, p)

    def test_no_local_paths_or_server_root_paths(self):
        for p in DEMO.rglob('*'):
            if p.suffix not in {'.html', '.js', '.css', '.json'}:
                continue
            text = p.read_text(encoding='utf-8')
            for bad in ('/tmp/', '/data/home', '/Users/', 'comicdesk-demo-'):
                self.assertFalse(bad in text, f'{p}: {bad}')
            # 作品预览原本走本机临时端口，静态版里不该再出现；默认 7777 只是说明文字
            self.assertFalse(re.search(r'127\.0\.0\.1:(?!7777)\d+', text), f'{p}: 临时端口')
            self.assertFalse(re.search(r'["\'`]/(?:api|desk-v2)/', text), f'{p}: 根路径接口')

    def test_shim_offline(self):
        src = (ROOT / 'tools' / 'online_demo_shim.js').read_text(encoding='utf-8')
        urls = set(re.findall(r'https?://[^\s\'"<>]+', src))
        self.assertEqual(urls, {'https://github.com/Onlyaguest/comic-desk-local'})
        for bad in ('sendBeacon', 'XMLHttpRequest', 'WebSocket'):
            self.assertNotIn(bad, src)


if __name__ == '__main__':
    unittest.main()
