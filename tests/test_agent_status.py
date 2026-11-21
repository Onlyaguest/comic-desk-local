"""AI 自己报状态：钩子只追加、不输出；读账本只看尾部；自报优先于推断；装卸钩子不碰用户自己的配置。"""
import io,json,os,subprocess,sys,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'lib'));sys.path.insert(0,str(ROOT/'tools'))
import agent_status_hook as hook, agent_hooks
from desk.fusion import agent_status as st, session_board as board

# 输入形状对照本机 Claude Code 2.1.322 与 Codex 0.171.0 的钩子定义（字段同名）
CLAUDE={'UserPromptSubmit':{'hook_event_name':'UserPromptSubmit','session_id':'c-1','cwd':'/w/desk','prompt':'私密需求','transcript_path':'/t.jsonl'},
        'Notification':{'hook_event_name':'Notification','session_id':'c-1','cwd':'/w/desk','notification_type':'permission_prompt','message':'Claude needs your permission to use Bash'},
        'Stop':{'hook_event_name':'Stop','session_id':'c-1','cwd':'/w/desk','last_assistant_message':'私密回复','stop_hook_active':False},
        'StopFailure':{'hook_event_name':'StopFailure','session_id':'c-1','cwd':'/w/desk','error':'rate_limit'}}
CODEX={'UserPromptSubmit':{'hook_event_name':'UserPromptSubmit','session_id':'x-1','cwd':'/w/app','model':'m','permission_mode':'default','prompt':'私密','turn_id':'t'},
       'PermissionRequest':{'hook_event_name':'PermissionRequest','session_id':'x-1','cwd':'/w/app','model':'m','permission_mode':'default','tool_name':'shell','turn_id':'t'},
       'Interrupt':{'hook_event_name':'Interrupt','session_id':'x-1','cwd':'/w/app','model':'m','permission_mode':'default','transcript_path':None,'turn_id':'t'},
       'Stop':{'hook_event_name':'Stop','session_id':'x-1','cwd':'/w/app','model':'m','permission_mode':'default','last_assistant_message':'私密','stop_hook_active':False,'turn_id':'t'}}

class HookTests(unittest.TestCase):
    def test_event_mapping_both_agents(self):
        self.assertEqual({e:hook.record('claude',p)['state'] for e,p in CLAUDE.items()},{'UserPromptSubmit':'working','Notification':'waiting','Stop':'done','StopFailure':'error'})
        self.assertEqual({e:hook.record('codex',p)['state'] for e,p in CODEX.items()},{'UserPromptSubmit':'working','PermissionRequest':'waiting','Interrupt':'waiting','Stop':'done'})
    def test_no_prompt_or_reply_text_kept(self):
        for agent,events in (('claude',CLAUDE),('codex',CODEX)):
            for p in events.values():self.assertNotIn('私密',json.dumps(hook.record(agent,p),ensure_ascii=False))
    def test_ignored_inputs(self):
        self.assertIsNone(hook.record('claude',{**CLAUDE['Notification'],'notification_type':'auth_success'}))
        self.assertIsNone(hook.record('claude',{'hook_event_name':'PreToolUse','session_id':'c'}))
        self.assertIsNone(hook.record('claude',{'hook_event_name':'Stop'}))
        self.assertIsNone(hook.record('other',CLAUDE['Stop']))
    def test_script_is_silent_and_never_fails(self):
        with tempfile.TemporaryDirectory() as d:
            ledger=Path(d)/'s.jsonl'
            with patch.object(hook,'LEDGER',ledger),patch('sys.stdin',io.StringIO(json.dumps(CLAUDE['Stop']))),patch('sys.stdout',new_callable=io.StringIO) as out:
                self.assertEqual(hook.main(['x','claude']),0);self.assertEqual(out.getvalue(),'')
            self.assertEqual(json.loads(ledger.read_text())['state'],'done')
        for bad in ('not json','[]',''):
            r=subprocess.run([sys.executable,str(ROOT/'tools'/'agent_status_hook.py'),'claude'],input=bad,capture_output=True,text=True,timeout=10)
            self.assertEqual((r.returncode,r.stdout,r.stderr),(0,'',''))

class LedgerTests(unittest.TestCase):
    def setUp(self):self.t=tempfile.TemporaryDirectory();self.ledger=Path(self.t.name)/'s.jsonl';self.now=int(time.time()*1000)
    def tearDown(self):self.t.cleanup()
    def write(self,*rows):
        with self.ledger.open('a') as f:
            for r in rows:f.write((r if isinstance(r,str) else json.dumps(r))+'\n')
    def test_latest_per_session_skips_bad_lines(self):
        self.write({'at':self.now-5000,'agent':'claude','session':'a','state':'working'},'{broken',{'at':self.now,'agent':'claude','session':'a','state':'waiting'},{'at':self.now,'agent':'codex','session':'a','state':'done'},{'at':self.now,'agent':'evil','session':'z','state':'done'})
        got=st.latest(self.ledger)
        self.assertEqual(sorted(got),['claude:a','codex:a']);self.assertEqual(got['claude:a']['state'],'waiting')
    def test_reads_only_tail(self):
        self.write(*[{'at':self.now,'agent':'claude','session':'old%d'%i,'state':'done','detail':'x'*60} for i in range(6000)])
        self.write({'at':self.now,'agent':'claude','session':'new','state':'waiting'})
        got=st.latest(self.ledger);self.assertIn('claude:new',got);self.assertNotIn('claude:old0',got)
    def test_bad_timestamp_line_is_skipped(self):
        self.write({'at':'昨天','agent':'claude','session':'a','state':'waiting'},{'at':True,'agent':'claude','session':'b','state':'waiting'},{'at':self.now,'agent':'claude','session':'c','state':'done'})
        self.assertEqual(sorted(st.latest(self.ledger)),['claude:c']);self.assertEqual(len(st.summary(self.ledger)['items']),1)
    def test_missing_ledger(self):self.assertEqual(st.latest(self.ledger),{});self.assertEqual(st.summary(self.ledger)['items'],[])
    def test_stale_working_is_unknown(self):
        self.assertEqual(st.lane({'state':'working','at':self.now-31*60000},self.now)[0],'unknown')
        self.assertEqual(st.lane({'state':'working','at':self.now},self.now)[0],'ai')
        self.assertEqual([st.lane({'state':s,'at':self.now},self.now)[0] for s in ('waiting','done','error')],['wait','me','stuck'])
    def test_summary_orders_waiting_first_and_drops_old(self):
        self.write({'at':self.now-1000,'agent':'claude','session':'d','state':'done','cwd':'/w/a'},{'at':self.now-2000,'agent':'codex','session':'w','state':'waiting','cwd':'/w/b','detail':'shell'},{'at':self.now-3*86400000,'agent':'claude','session':'old','state':'error'})
        s=st.summary(self.ledger,self.now)
        self.assertEqual([x['id'] for x in s['items']],['session:codex:w','session:claude:d'])
        self.assertEqual((s['counts']['waiting'],s['counts']['error']),(1,0));self.assertEqual(s['items'][0]['project'],'b')

class BoardTests(unittest.TestCase):
    def test_report_overrides_inference_only_when_not_older(self):
        import sqlite3
        from desk import indexdb
        with tempfile.TemporaryDirectory() as d:
            db=Path(d)/'i.db';now=int(time.time()*1000)
            with indexdb.connect(db) as c:
                for sid in ('claude:fresh','claude:stale'):indexdb.upsert(c,sid,'claude',title=sid,updated=time.strftime('%Y-%m-%dT%H:%M:%S',time.gmtime())+'Z',native_status='有回复')
            rep={'claude:fresh':{'agent':'claude','session':'fresh','state':'waiting','at':now,'detail':'要你批准'},'claude:stale':{'agent':'claude','session':'stale','state':'waiting','at':now-3600000}}
            with patch.object(st,'latest',return_value=rep):snap=board.snapshot(db=db,cache=Path(d)/'obs.json')
            cards={c['id']:c for c in snap['board']['cards']}
            self.assertEqual(cards['session:claude:fresh']['state'],'wait');self.assertIn('AI 钩子自报',cards['session:claude:fresh']['why'])
            self.assertNotIn('AI 钩子自报',cards['session:claude:stale']['why'])

class InstallTests(unittest.TestCase):
    def test_install_keeps_user_hooks_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as d,patch.dict(os.environ,{'CLAUDE_CONFIG_DIR':d+'/c','CODEX_HOME':d+'/x'}),patch('sys.stdout',new_callable=io.StringIO):
            cfg=Path(d)/'c'/'settings.json';cfg.parent.mkdir()
            mine={'model':'opus','hooks':{'Stop':[{'hooks':[{'type':'command','command':'say done'}]}]}}
            cfg.write_text(json.dumps(mine))
            agent_hooks.main(['x','install','claude','codex']);agent_hooks.main(['x','install','claude','codex'])
            got=json.loads(cfg.read_text())
            self.assertEqual(got['model'],'opus');self.assertEqual(len(got['hooks']['Stop']),2)
            self.assertEqual(sorted(got['hooks']),sorted(agent_hooks.EVENTS['claude']))
            codex=json.loads((Path(d)/'x'/'hooks.json').read_text());self.assertEqual(sorted(codex['hooks']),sorted(agent_hooks.EVENTS['codex']))
            self.assertTrue(list(cfg.parent.glob('settings.json.bak-*')))
            agent_hooks.main(['x','uninstall','claude','codex'])
            self.assertEqual(json.loads(cfg.read_text()),mine);self.assertEqual(json.loads((Path(d)/'x'/'hooks.json').read_text()),{})
    def test_unknown_hook_shape_left_alone(self):
        with tempfile.TemporaryDirectory() as d,patch.dict(os.environ,{'CLAUDE_CONFIG_DIR':d}),patch('sys.stdout',new_callable=io.StringIO):
            cfg=Path(d)/'settings.json';odd={'hooks':{'Stop':{'weird':True}}};cfg.write_text(json.dumps(odd))
            self.assertEqual(agent_hooks.main(['x','install','claude']),1);self.assertEqual(agent_hooks.main(['x','uninstall','claude']),0)
            self.assertEqual(json.loads(cfg.read_text()),odd);self.assertEqual(list(Path(d).glob('*.bak-*')),[])
    def test_show_writes_nothing(self):
        with tempfile.TemporaryDirectory() as d,patch.dict(os.environ,{'CLAUDE_CONFIG_DIR':d+'/c','CODEX_HOME':d+'/x'}),patch('sys.stdout',new_callable=io.StringIO) as out:
            agent_hooks.main(['x','show'])
            self.assertIn('agent_status_hook.py',out.getvalue());self.assertEqual(list(Path(d).iterdir()),[])

if __name__=='__main__':unittest.main()
