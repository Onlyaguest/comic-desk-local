"""发稿台：离线样例不调用外部命令、外改对比与采用、路径边界、个人模式命令。"""
import json, sys, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'lib'))
from desk import publish as pub


class PublishTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.data = Path(self.temp.name) / 'data'
        self.patches = [patch.object(pub, 'DATA', self.data), patch.object(pub, 'CONF', self.data / 'publish/config.local.json'),
                        patch.object(pub, 'DEMO', self.data / 'publish/demo')]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.temp.cleanup()

    def test_demo_copies_samples_and_never_runs_commands(self):
        with patch('subprocess.run', side_effect=AssertionError('样例模式不应启动进程')):
            s = pub.state()
            self.assertEqual(s['mode'], 'demo')
            self.assertEqual(len(s['posts']), 4)
            d = pub.post('sample-desk-intro')
            self.assertEqual([x['id'] for x in d['siblings']], ['sample-desk-intro-v2'])
            self.assertEqual(d['commands'], [])
            with self.assertRaises(ValueError):
                pub.run(pub.find('sample-desk-intro'), 'preview')
        self.assertTrue((self.data / 'publish/demo/posts.json').exists())

    def test_steps_cover_the_whole_flow(self):
        labels = [s['label'] for s in pub.post('sample-desk-intro')['steps']]
        self.assertEqual(labels, ['写稿', '验收', '我来改', '外部改', '挑这版', '发出去', '归档'])

    def test_compare_then_adopt(self):
        x = pub.find('sample-desk-intro')
        c = pub.compare(x)
        self.assertEqual(c['changed'], 3)
        self.assertFalse(c['localMoved'])
        kinds = [b['t'] for b in c['blocks'] if b['t'] != 'same']
        self.assertEqual(kinds, ['edit', 'add', 'del'])
        before = pub.body_path(x).read_text(encoding='utf-8')
        r = pub.adopt(x)
        after = pub.body_path(x).read_text(encoding='utf-8')
        self.assertIn('像收拾书桌一样', after)
        self.assertNotIn('你可以照着搭', after)
        self.assertTrue(after.startswith('---\ntitle: 样例 · 我给自己搭了一张本地桌子'))
        self.assertIn('![从写好到发出去](imgs/flow.svg)', after)
        backup = pub.where()[1] / r['backup'] / 'article.md'
        self.assertEqual(backup.read_text(encoding='utf-8'), before)
        self.assertEqual(pub.compare(x)['changed'], 0)

    def test_cloud_doc_head_maps_title_and_images(self):
        x = pub.find('sample-desk-intro')
        d = pub.desk_dir(x)
        body = pub.split_front(pub.body_path(x).read_text(encoding='utf-8'))[2]
        body = body.replace('imgs/flow.svg', 'https://cloud.example/file/abc')
        (d / '外改.md').write_text('# 云文档里改的标题\n\n![封面](https://cloud.example/file/c)\n\n> 作者：样例作者  \n> 摘要：新摘要\n\n' + body, encoding='utf-8')
        c = pub.compare(x)
        self.assertEqual(c['changed'], 0)
        pub.adopt(x)
        after = pub.body_path(x).read_text(encoding='utf-8')
        self.assertIn('title: 云文档里改的标题', after)
        self.assertIn('digest: 新摘要', after)
        self.assertIn('(imgs/flow.svg)', after)
        self.assertNotIn('cloud.example', after)

    def test_local_moved_is_reported(self):
        x = pub.find('sample-desk-intro')
        p = pub.body_path(x)
        p.write_text(p.read_text(encoding='utf-8') + '\n导出以后定稿又加了一段。\n', encoding='utf-8')
        self.assertTrue(pub.compare(x)['localMoved'])

    def test_paths_stay_inside(self):
        pub.state()
        with self.assertRaises(ValueError):
            pub.file_bytes('sample-desk-intro', '../posts.json')
        with self.assertRaises(ValueError):
            pub.file_bytes('sample-desk-intro', 'packs/2026-11-01_desk-intro/article.md')
        with self.assertRaises(ValueError):
            pub.inside(pub.where()[1], '../../etc/passwd')
        self.assertTrue(pub.file_bytes('sample-desk-intro', 'packs/2026-11-01_desk-intro/imgs/flow.svg').is_file())

    def test_note_keeps_words_and_gives_prompt(self):
        x = pub.find('sample-desk-intro')
        n = pub.add_note(x, 'rewrite', '开头用我这段：我先叠个甲。')
        self.assertIn('开头用我这段：我先叠个甲。', n['prompt'])
        self.assertIn('article.md', n['prompt'])
        self.assertEqual(pub.notes(x)[0]['text'], '开头用我这段：我先叠个甲。')
        with self.assertRaises(ValueError):
            pub.add_note(x, 'rm -rf', 'x')
        with self.assertRaises(ValueError):
            pub.add_note(x, 'patch', '  ')

    def test_update_validates(self):
        pub.state()
        with self.assertRaises(ValueError):
            pub.update('sample-desk-intro', {'url': 'javascript:alert(1)'})
        with self.assertRaises(ValueError):
            pub.update('sample-desk-intro', {'status': '随便'})
        x = pub.update('sample-desk-intro', {'status': '已发出', 'url': 'https://example.com/p'})
        self.assertEqual(x['status'], '已发出')
        self.assertFalse(x['picked'])
        self.assertTrue((self.data / 'publish/changes.jsonl').exists())

    def test_personal_mode_fetch_command(self):
        root = Path(self.temp.name) / 'mine'
        (root / 'p1').mkdir(parents=True)
        (root / 'p1/a.md').write_text('---\ntitle: 我的稿\n---\n\n第一段。\n\n第二段。\n', encoding='utf-8')
        (root / 'posts.json').write_text(json.dumps([{'id': 'p1', 'title': '我的稿', 'status': '草稿', 'pack': 'p1', 'body': 'p1/a.md'}]), encoding='utf-8')
        code = "print('第一段。\\n\\n第二段，在别处改过。')"
        pub.CONF.parent.mkdir(parents=True, exist_ok=True)
        pub.CONF.write_text(json.dumps({'posts': str(root / 'posts.json'), 'commands': {'fetch': [sys.executable, '-c', code]}}), encoding='utf-8')
        self.assertEqual(pub.mode(), 'personal')
        x = pub.find('p1')
        pub.export(x)
        r = pub.run(x, 'fetch')
        self.assertTrue(r['ok'], r)
        c = pub.compare(x)
        self.assertEqual(c['changed'], 1)
        with self.assertRaises(ValueError):
            pub.run(x, 'push')


if __name__ == '__main__':
    unittest.main()
