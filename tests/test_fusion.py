"""融合发布版：离线隔离、状态证据、身份边界与回写核对。"""
import hashlib,json,sqlite3,sys,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'lib'))
from desk import indexdb
from desk.fusion import bridge,governance as g,session_board as board,bounded_sync as sync,observations as obs


class FusionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
    def tearDown(self):self.temp.cleanup()
    def registry(self,**kw):
        with patch.object(g,'context',return_value=kw):return g.Registry()
    def test_registry_does_not_read_home(self):
        with patch.object(Path,'home',side_effect=AssertionError('禁止读取HOME')),patch.object(g,'context',return_value={}):
            self.assertEqual(g.Registry().aliases,{})
    def test_explicit_aliases_merge_only_same_machine(self):
        r=self.registry(aliases={'codex:host':'codex:native'})
        self.assertEqual(r.canonical('codex:host'),'codex:native')
        self.assertEqual(r.canonical('codex:host',[{'data':'{"spaceNodeId":"other"}'}]),'other|codex:host')
        self.assertIn('codex:host',r.ids_for('codex:native'))
    def test_dedup_preserves_pin_alias(self):
        r=self.registry(aliases={'codex:host':'codex:native'});p=self.root/'index.db'
        with indexdb.connect(p) as c:
            for sid,path in [('codex:host',''),('codex:native','native.jsonl')]:
                indexdb.upsert(c,sid,'codex',title='同名样例',updated='2026-11-18',path=path)
            rows,n=board.canonical_sessions(c,c.execute('SELECT * FROM sessions').fetchall(),r)
            self.assertEqual(n,1);self.assertEqual(rows[0]['id'],'codex:native');self.assertIn('session:codex:host',rows[0]['_aliases'])
    def test_title_similarity_does_not_merge(self):
        r=self.registry();p=self.root/'index.db'
        with indexdb.connect(p) as c:
            for sid in ('codex:a','codex:b'):indexdb.upsert(c,sid,'codex',title='同名',updated='2026-11-18')
            rows,n=board.canonical_sessions(c,c.execute('SELECT * FROM sessions').fetchall(),r)
            self.assertEqual(n,0);self.assertEqual(len(rows),2)
    def test_directory_newer_than_body_is_unknown(self):
        self.assertEqual(board.classify({'native_status':'active'},None,None,{},False,int(time.time()*1000))[0],'unknown')
    def test_reply_is_not_task_acceptance(self):
        self.assertEqual(board.classify({'native_status':'completed'},True,None,{},True,int(time.time()*1000))[0],'me')
    def test_stale_running_is_unknown(self):
        now=int(time.time()*1000)
        self.assertEqual(board.classify({},None,None,{'hostState':'running','hostAt':now-3600000},True,now)[0],'unknown')
    def test_freshness_per_source(self):
        now=int(time.time()*1000);rows=[{'name':'claude','synced':now/1000}]
        f=board.freshness({'checkedAt':now,'stale':True},rows,now)
        self.assertEqual(len(f),4);self.assertTrue(f[0]['stale']);self.assertFalse(next(x for x in f if x['id']=='claude')['stale'])
    def test_bridge_never_runs_platform_command(self):
        with patch('subprocess.run',side_effect=AssertionError('不应启动进程')):
            s=bridge.refresh();self.assertTrue(s['demo']);self.assertEqual(len(s['board']['cards']),6)
    def test_bridge_restricted_card_and_script_url(self):
        b={'v':1,'day':'sample','projects':[],'today':[],'cards':[{'id':'a','state':'me','open':False,'text':'hidden','todoNext':'hidden','originUrl':'javascript:alert(1)'}]}
        c=bridge.validate(b)['cards'][0];self.assertEqual(c['text'],'');self.assertEqual(c['todoNext'],'');self.assertEqual(c['originUrl'],'')
    def test_bridge_rejects_bad_shape(self):
        with self.assertRaises(ValueError):bridge.validate({'cards':{}})
    def test_explicit_role_only(self):
        r=self.registry(roles={'sample':{'name':'示例','duty':'核对'}},tasks={'codex:test':{'assistant':'sample','taskRef':'test:task'}})
        self.assertTrue(g.role_for({'source':'codex','sessionId':'codex:test'},registry=r)['identified'])
        self.assertFalse(g.role_for({'source':'cohub','sessionId':'missing'},registry=r)['identified'])
    def test_declaration_ignores_code_and_quotes(self):
        self.assertEqual(g.declaration('> 回写：假\n```text\n回写：假\n```\n**回写：** 说明已改'),'回写： 说明已改')
    def test_matching_task_statement_and_file_required(self):
        p=self.root/'proof.md';p.write_text('内容');line='回写：说明已改'
        receipt={'id':'proof','taskRef':'task','statementHash':g.statement_hash(line),'evidence':[{'path':'proof.md','sha256':hashlib.sha256(p.read_bytes()).hexdigest()}]}
        with patch.object(g,'PROJECT',self.root):
            self.assertEqual(g.writeback(line,'task',receipts=[])['state'],'declared')
            self.assertEqual(g.writeback(line,'task',receipts=[receipt])['state'],'verified')
            self.assertEqual(g.writeback(line,'other',receipts=[receipt])['state'],'declared')
            self.assertEqual(g.writeback(line+'新版本','task',receipts=[receipt])['state'],'declared')
            p.write_text('改变');self.assertEqual(g.writeback(line,'task',receipts=[receipt])['state'],'declared')
    def test_evidence_cannot_escape_project(self):
        self.assertFalse(g.verify_files([{'path':'../outside.md','contains':['内容']}],self.root)[0]['ok'])
        with patch.object(g,'PROJECT',self.root),patch.object(g,'receipt_rows',return_value=[{'id':'bad','evidence':[{'path':'../outside.md'}]}]):
            with self.assertRaises(ValueError):g.registered_evidence('bad',0)
    def test_hash_failure_not_overridden_by_contains(self):
        p=self.root/'proof.md';p.write_text('内容')
        self.assertFalse(g.verify_files([{'path':'proof.md','sha256':'wrong','contains':['内容']}],self.root)[0]['ok'])
    def test_demo_refresh_cannot_scan_or_call_cli(self):
        cfg={'demo':True,'localEnabled':True,'cohubEnabled':True}
        with patch.object(indexdb,'config',return_value=cfg),patch.object(indexdb,'DB',self.root/'index.db'),patch.object(sync,'LEDGER',self.root/'ledger.json'),patch.object(indexdb,'sync_local',side_effect=AssertionError('私有扫描')),patch.object(sync,'cli_json',side_effect=AssertionError('外部CLI')):
            r=sync.run();self.assertTrue(r['ok'],r);self.assertEqual(r['cloudCliCalls'],0)
    def test_disabled_local_is_respected_outside_demo(self):
        with patch.object(indexdb,'config',return_value={'demo':False,'localEnabled':False,'cohubEnabled':False}),patch.object(indexdb,'DB',self.root/'index.db'),patch.object(sync,'LEDGER',self.root/'ledger.json'),patch.object(indexdb,'sync_local',side_effect=AssertionError('禁止扫描')):
            self.assertTrue(sync.run()['ok'])
    def test_claude_usage_never_invents_total_or_keeps_thinking(self):
        p=self.root/'claude.jsonl';p.write_text(json.dumps({'type':'assistant','timestamp':'2026-11-18T10:00:00Z','message':{'usage':{'input_tokens':20,'output_tokens':3,'cache_read_input_tokens':9},'content':[{'type':'thinking','thinking':'hidden-thought'},{'type':'text','text':'交付\n回写：说明已改'}],'stop_reason':'end_turn'}})+'\n')
        a,n,_=obs.read(p,engine='claude');self.assertNotIn('total_tokens',a['usage']['tokens']);self.assertEqual(a['usage']['tokens']['cached_input_tokens'],9)
        self.assertNotIn('hidden-thought',json.dumps(a));b,n,hit=obs.read(p,a,engine='claude');self.assertTrue(hit);self.assertEqual(n,0)
    def test_sample_back_has_verified_evidence_without_home(self):
        with patch.object(Path,'home',side_effect=AssertionError('禁止读取HOME')):
            d=g.details({'id':'sample:review','source':'mirasim','whoId':'sample-assistant','open':True},[],'',None)
        self.assertEqual(d['writeback']['state'],'verified');self.assertTrue(d['responsibility']['identified']);self.assertEqual(len(d['feedback']),1)

if __name__=='__main__':unittest.main()
