import json, sys, tempfile, unittest, subprocess, shutil
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'lib'))
from desk import indexdb as db

class IndexTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.root=Path(self.temp.name)
        self.c=db.connect(self.root/'index.sqlite3')
    def tearDown(self): self.c.close(); self.temp.cleanup()
    def test_mirasim_deduplicates_native_and_preserves_content(self):
        db.upsert(self.c,'codex:abc','codex','原题',path='/original',coverage='正文已索引')
        db.upsert(self.c,'codex:abc','codex','宿主题',source='mirasim',native_id='codex:abc')
        self.assertEqual(db.stats(self.c)['sessions'],1)
        d=db.detail(self.c,'codex:abc'); self.assertEqual(len(d['origins']),2)
        self.assertEqual(d['session']['path'],'/original')
        self.assertEqual(d['session']['coverage'],'正文已索引')
    def test_parser_ignores_mirror_tools_and_injected_instructions(self):
        p=self.root/'sample.jsonl'
        rows=[{'type':'session_meta','payload':{'id':'abc','cwd':'/tmp/project'}},
          {'type':'response_item','payload':{'type':'message','role':'user','content':[{'type':'input_text','text':'# AGENTS.md instructions irrelevant'}]}},
          {'type':'response_item','timestamp':'2026-11-11T01:00:00Z','payload':{'type':'message','role':'user','content':[{'type':'input_text','text':'帮我检索'}]}},
          {'type':'event_msg','payload':{'type':'user_message','message':'帮我检索'}},
          {'type':'response_item','payload':{'type':'message','role':'assistant','phase':'commentary','content':[{'type':'output_text','text':'进行中'}]}},
          {'type':'response_item','payload':{'type':'message','role':'assistant','phase':'final_answer','content':[{'type':'output_text','text':'完成回复'}]}}]
        p.write_text('\n'.join(map(json.dumps,rows)))
        meta,msgs,bad=db.parse_transcript(p,'codex'); self.assertEqual(meta['id'],'abc')
        self.assertEqual([m['text'] for m in msgs],['帮我检索','完成回复'])
        if shutil.which('zstd'):
            subprocess.run(['zstd','-q',str(p),'-o',str(p)+'.zst'],check=True)
            self.assertEqual(db.parse_transcript(Path(str(p)+'.zst'),'codex')[1],msgs)
    def test_artifact_reference_missing_file_and_unsafe_uri(self):
        db.upsert(self.c,'claude:1','claude','目录')
        text='[报告](/tmp/报告.md) [站点](https://example.com) [危险](javascript:alert)'
        db.replace_messages(self.c,'claude:1',[{'role':'assistant','text':text}],'claude')
        arts=db.detail(self.c,'claude:1')['artifacts'];self.assertEqual(len(arts),2)
        self.assertTrue(any(a['available']=='路径已失效' for a in arts))
        db.replace_messages(self.c,'claude:1',[{'role':'assistant','text':text}],'claude')
        self.assertEqual(len(db.detail(self.c,'claude:1')['artifacts']),2)
    def test_search_chinese_source_filter_paging_and_updated_replacement(self):
        db.upsert(self.c,'codex:a','codex','标题')
        db.replace_messages(self.c,'codex:a',[{'role':'user','text':'研究索引数据'}],'codex')
        self.assertEqual(db.query(self.c,q='索引')['total'],1)
        self.assertEqual(db.query(self.c,q='索引',source='claude')['total'],0)
        db.replace_messages(self.c,'codex:a',[{'role':'user','text':'完全新内容'}],'codex')
        self.assertEqual(db.query(self.c,q='索引')['total'],0)
        self.assertEqual(db.detail(self.c,'codex:a')['message_count'],1)
    def test_malformed_line_does_not_destroy_valid_message(self):
        p=self.root/'claude.jsonl';p.write_text('{broken\n'+json.dumps({'sessionId':'a','message':{'role':'user','content':'真实提问'}}))
        meta,msgs,bad=db.parse_transcript(p,'claude');self.assertEqual(bad,1);self.assertEqual(len(msgs),1)
    def test_cohub_workspace_reference_uses_remote_origin(self):
        db.upsert(self.c,'cohub:a:s','cohub','云端',source='cohub',data={'spaceId':'space-1'})
        db.artifact(self.c,'报告','/workspace/out/report.md','cohub','正文引用',sid='cohub:a:s')
        a=db.detail(self.c,'cohub:a:s')['artifacts'][0]
        self.assertEqual(a['target'],'cohub-file://space-1/out/report.md')
    def test_redacts_credentials_and_beijing_date_boundary(self):
        self.assertNotIn('abcdef',db.redact('https://example.com?token=abcdef'))
        db.upsert(self.c,'codex:d','codex','date',updated='2026-11-10T17:00:00Z')
        self.assertEqual(db.query(self.c,date_from='2026-11-11',date_to='2026-11-11')['total'],1)
        self.assertEqual(db.query(self.c,date_from='2026-11-10',date_to='2026-11-10')['total'],0)
    def test_local_metadata_name_and_incremental_cache(self):
        import sqlite3
        codex=self.root/'codex'; codex.mkdir()
        log=codex/'a.jsonl'
        log.write_text(json.dumps({'type':'session_meta','payload':{'id':'a','cwd':'/tmp'}})+'\n'+json.dumps({'type':'response_item','payload':{'type':'message','role':'user','content':[{'type':'input_text','text':'提问'}]}}))
        with sqlite3.connect(codex/'state_5.sqlite') as c:
            c.execute('create table threads(id,title,name,cwd,rollout_path,updated_at,archived)')
            c.execute('insert into threads values(?,?,?,?,?,?,?)',('a','原提问','用户命名','/tmp',str(log),1794358800,0))
        cfg={'codexHome':str(codex),'claudeHome':str(self.root/'empty')}
        first=db.sync_local(self.c,cfg); second=db.sync_local(self.c,cfg)
        self.assertEqual(first['parsed'],1); self.assertEqual(second['cached'],1)
        self.assertEqual(db.detail(self.c,'codex:a')['session']['title'],'用户命名')
    def test_build_never_overwrites_homepage(self):
        from desk import build
        from desk.paths import APP
        original=(APP/'index.html').read_bytes(); build.build()
        self.assertEqual((APP/'index.html').read_bytes(),original)
        self.assertFalse((APP/'catalog.html').samefile(APP/'index.html'))

if __name__=='__main__': unittest.main()
