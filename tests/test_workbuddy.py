import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
from desk import indexdb as db,indexapi,workbuddy

class WorkBuddyTests(unittest.TestCase):
    def test_incremental_body_artifacts_and_image(self):
        with tempfile.TemporaryDirectory() as tmp:
            h=Path(tmp);p=h/'projects/p/s.jsonl';p.parent.mkdir(parents=True)
            image=h/'picture.png';image.write_bytes(b'image')
            rows=[{'type':'ai-title','aiTitle':'样本','sessionId':'s','cwd':str(h)},
                  {'type':'message','id':'1','role':'user','timestamp':1782802294146,'content':[{'type':'input_text','text':'<system-reminder>ignore literal <user_query> marker</system-reminder><user_query>真实问题</user_query>'}]},
                  {'type':'message','id':'2','role':'assistant','timestamp':'1782802295146','content':[{'type':'output_text','text':'结果'}]}]
            p.write_text('\n'.join(map(json.dumps,rows))+'\n')
            a=h/'artifact-index/s.json';a.parent.mkdir();a.write_text(json.dumps({'artifacts':[{'uri':image.as_uri(),'title':'图片'}]}))
            c=db.connect(h/'index.db');cfg={'workbuddyHome':str(h)}
            self.assertEqual(workbuddy.sync(c,cfg)['parsed'],1)
            self.assertEqual(c.execute("select text from messages where role='user'").fetchone()[0],'真实问题')
            self.assertEqual(c.execute('select kind from artifacts').fetchone()[0],'image')
            self.assertTrue(c.execute('select updated from sessions').fetchone()[0].startswith('2026-'))
            with patch.object(workbuddy,'parse',side_effect=AssertionError('unchanged parsed')):
                self.assertEqual(workbuddy.sync(c,cfg)['cached'],2)
            a.write_text(json.dumps({'artifacts':[{'uri':image.as_uri(),'title':'新标题'}]}))
            self.assertEqual(workbuddy.sync(c,cfg)['artifact_files'],1)
            rows.append({'type':'message','id':'3','role':'user','timestamp':1782802296146,'content':'新增'})
            p.write_text('\n'.join(map(json.dumps,rows))+'\n')
            self.assertEqual(workbuddy.sync(c,cfg)['parsed'],1)
            self.assertEqual(c.execute('select count(*) from messages').fetchone()[0],3)
            with patch.object(indexapi.subprocess,'run',return_value=SimpleNamespace(returncode=0)) as run:
                indexapi.opened(c,{'kind':'app','id':'workbuddy:s','source':'workbuddy'})
                self.assertEqual(run.call_args.args[0],['open','workbuddy://home'])
                with self.assertRaises(ValueError): indexapi.opened(c,{'kind':'session','id':'workbuddy:s'})
            c.close()

if __name__=='__main__':unittest.main()
