import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
from desk import indexdb as db,indexapi,sessionopen

class SessionOpenTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.c=db.connect(self.root/'index.db')
    def tearDown(self): self.c.close();self.tmp.cleanup()
    def test_codex_and_cohub_open_original_urls(self):
        for engine,uri in [('codex','codex://threads/test'),('cohub','https://cohub.live/spaces/test/sessions/test')]:
            db.upsert(self.c,engine+':test',engine,uri=uri)
            with patch.object(indexapi.subprocess,'run',return_value=SimpleNamespace(returncode=0)) as run:
                self.assertTrue(indexapi.opened(self.c,{'kind':'session','id':engine+':test'})['ok'])
                self.assertEqual(run.call_args.args[0],['open',uri])
    def test_host_origin_uses_mirasim_by_default(self):
        db.upsert(self.c,'codex:test','codex',uri='codex://threads/test')
        db.upsert(self.c,'codex:test','codex',source='mirasim',native_id='codex:test')
        with patch.object(sessionopen,'open_mirasim',return_value={'ok':True,'opened_in':'Mirasim'}) as run:
            self.assertEqual(indexapi.opened(self.c,{'kind':'session','id':'codex:test'})['opened_in'],'Mirasim')
            run.assert_called_once_with('codex:test')
    def test_mirasim_switches_local_and_checks_ack(self):
        responses=[{'window':'main:cloud','data':{'locale':'zh-CN'}},{},{'elements':[{'role':'button','text':'本机订阅','enabled':True,'selector':'wrong'},{'role':'menuitem','text':'本机默认','enabled':True,'selector':'local-menu'}]},{'matched':1},*([{'window':'main'}]*3),{'window':'main','result':'codex:test'},{},{'window':'main','data':{'activeIndex':0,'panes':[{'sessionKey':'codex:test'}]}}]
        with patch.object(db,'mirasim_args',return_value=['ui-cli']),patch.object(db,'run_json',side_effect=responses) as run,patch.object(sessionopen.subprocess,'run',return_value=SimpleNamespace(returncode=0)):
            self.assertTrue(sessionopen.open_mirasim('codex:test')['ok'])
            self.assertIn(['ui-cli','click','--selector','local-menu'],[x.args[1] for x in run.call_args_list])
            self.assertIn(['ui-cli','ui','pane.open','--value','codex:test','--window','main'],[x.args[1] for x in run.call_args_list])
    def test_mirasim_wrong_ack_is_not_success(self):
        responses=[{'data':{'locale':'zh-CN'}},{},{'elements':[{'role':'button','text':'本机订阅','enabled':True,'selector':'wrong'},{'role':'menuitem','text':'本机默认','enabled':True,'selector':'local-menu'}]},{'matched':1},*([{'window':'main'}]*3),{'window':'main:cloud','result':'codex:test'}]
        with patch.object(db,'mirasim_args',return_value=['ui-cli']),patch.object(db,'run_json',side_effect=responses),patch.object(sessionopen.subprocess,'run',return_value=SimpleNamespace(returncode=0)):
            with self.assertRaises(RuntimeError): sessionopen.open_mirasim('codex:test')
    def test_mirasim_active_pane_must_match(self):
        responses=[{'data':{'locale':'zh-CN'}},{},{'elements':[{'role':'button','text':'本机订阅','enabled':True,'selector':'wrong'},{'role':'menuitem','text':'本机默认','enabled':True,'selector':'local-menu'}]},{'matched':1},*([{'window':'main'}]*3),{'window':'main','result':'codex:test'},{},{'window':'main','data':{'activeIndex':0,'panes':[{'sessionKey':'codex:other'}]}}]
        with patch.object(db,'mirasim_args',return_value=['ui-cli']),patch.object(db,'run_json',side_effect=responses),patch.object(sessionopen.subprocess,'run',return_value=SimpleNamespace(returncode=0)),patch.object(sessionopen.time,'sleep'):
            with self.assertRaises(RuntimeError): sessionopen.open_mirasim('codex:test')
    def test_claude_explicit_source_bypasses_host(self):
        db.upsert(self.c,'claude:test','claude',source='mirasim',native_id='claude:test')
        with patch.object(sessionopen,'open_claude',return_value={'ok':True}) as native,patch.object(sessionopen,'open_mirasim') as host:
            self.assertTrue(indexapi.opened(self.c,{'kind':'session','id':'claude:test','source':'claude'})['ok'])
            native.assert_called_once();host.assert_not_called()
    def test_claude_resume_has_no_prompt_and_quotes_directory(self):
        native='837000df-8408-4ad5-8249-c7e51ea25bfd';cwd=self.root/"a ' $(touch BAD)";cwd.mkdir()
        db.upsert(self.c,'claude:'+native,'claude',workspace=str(cwd),native_id=native)
        with patch.object(db,'BASE',self.root),patch.object(sessionopen.shutil,'which',return_value='/opt/homebrew/bin/claude'),patch.object(sessionopen.subprocess,'run',return_value=SimpleNamespace(returncode=0)) as run:
            result=indexapi.opened(self.c,{'kind':'session','id':'claude:'+native})
            self.assertEqual(result['opened_in'],'Claude Code 终端')
            script=Path(run.call_args.args[0][-1]).read_text()
            import shlex
            self.assertIn('cd -- '+shlex.quote(str(cwd)),script)
            self.assertIn('exec /opt/homebrew/bin/claude --resume '+native,script)
            self.assertNotIn('--print',script)
    def test_invalid_claude_id_is_not_executed(self):
        db.upsert(self.c,'claude:bad','claude',workspace=str(self.root),native_id='bad; touch BAD')
        with patch.object(sessionopen.subprocess,'run') as run:
            with self.assertRaises(ValueError): indexapi.opened(self.c,{'kind':'session','id':'claude:bad'})
            run.assert_not_called()

if __name__=='__main__':unittest.main()
