import json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from desk import indexdb as db, cloudsync, indexapi, imagepreview

class IncrementalTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.c=db.connect(self.root/'test.sqlite');cloudsync.schema(self.c)
        self.sid='cohub:a:s';self.origin={'native_id':'s','data':json.dumps({'spaceId':'space'})}
        db.upsert(self.c,self.sid,'cohub','题目',updated='2026-11-11T01:00:00Z',source='cohub',data={'spaceId':'space'})
        self.c.commit()
    def tearDown(self): self.c.close();self.tmp.cleanup()
    def save(self,turns,full):
        s=dict(self.c.execute('select * from sessions where id=?',(self.sid,)).fetchone())
        cloudsync.save_session(self.c,s,self.origin,{'turns':turns,'files':[],'full':full,'file_limit':False})
    def turn(self,seq,text,status='completed'):
        return {'sequence':seq,'status':status,'updated':'2026-11-11T01:00:00Z','images':[],
                'messages':[{'role':'assistant','text':text,'ts':'2026-11-11T01:00:00Z'}]}
    def test_increment_replaces_tail_retains_history_and_search(self):
        self.save([self.turn(1,'历史'),self.turn(2,'未完成','running')],True)
        self.assertEqual(cloudsync.cursor_for(self.c,self.sid),1)
        self.save([self.turn(2,'新回复'),self.turn(3,'新增')],False)
        self.assertEqual([x['text'] for x in db.detail(self.c,self.sid)['messages']],['历史','新回复','新增'])
        self.assertEqual(db.query(self.c,q='未完成')['total'],0)
        self.assertEqual(db.query(self.c,q='新回复')['total'],1)
        self.assertEqual(cloudsync.cursor_for(self.c,self.sid),2)
        self.save([self.turn(2,'新回复'),self.turn(3,'新增')],False)
        self.assertEqual(db.detail(self.c,self.sid)['message_count'],3)
    def test_concurrent_catalog_change_does_not_mark_stale_body_current(self):
        s=dict(self.c.execute('select * from sessions where id=?',(self.sid,)).fetchone())
        s['_known_version']='old'
        db.checkpoint(self.c,'version:'+self.sid,'new');self.c.commit()
        cloudsync.save_session(self.c,s,self.origin,{'turns':[self.turn(1,'旧快照')],'files':[],'full':True,'file_limit':False})
        self.assertIsNone(db.checkpoint(self.c,'detail:'+self.sid))
        self.assertEqual(db.stats(self.c)['pending'],1)
    def test_newer_pagination_and_zero_cursor(self):
        responses=[{'files':[]},{'turns':[{'sequence':1,'assistantText':'一'}],'hasMore':True,'nextCursor':1},
                   {'turns':[{'sequence':2,'assistantText':'二'}],'hasMore':False}]
        with patch.object(db,'run_json',side_effect=responses) as call:
            result=cloudsync.fetch_session({'cohubCommand':'cli'}, {}, self.origin,0)
        self.assertFalse(result['full']);self.assertEqual(len(result['turns']),2)
        self.assertIn('newer',call.call_args_list[1].args[1]);self.assertIn('0',call.call_args_list[1].args[1])
    def test_file_permission_denial_preserves_readable_body_and_stops_background_retries(self):
        responses=[RuntimeError('forbidden'),{'turns':[{'sequence':1,'assistantText':'仍能读到正文'}],'hasMore':False}]
        with patch.object(db,'run_json',side_effect=responses):
            result=cloudsync.fetch_session({'cohubCommand':'cli'}, {}, self.origin)
        s=dict(self.c.execute('select * from sessions where id=?',(self.sid,)).fetchone())
        self.assertFalse(cloudsync.save_session(self.c,s,self.origin,result))
        self.assertEqual(db.stats(self.c)['pending_bodies'],0)
        self.assertEqual(db.stats(self.c)['blocked_files'],1)
        with patch.object(cloudsync,'fetch_session') as fetch:
            self.assertEqual(cloudsync.backfill(self.c,{}),{'processed':0,'failed':0})
            fetch.assert_not_called()
        self.assertEqual(db.detail(self.c,self.sid)['messages'][0]['text'],'仍能读到正文')
    def test_full_page_probes_cursor_even_when_server_has_more_is_false(self):
        responses=[{'files':[]},{'turns':[{'sequence':i} for i in range(48,148)],'hasMore':False,'nextCursor':48},
                   {'turns':[{'sequence':i} for i in range(1,48)],'hasMore':False,'nextCursor':1}]
        with patch.object(db,'run_json',side_effect=responses):
            result=cloudsync.fetch_session({'cohubCommand':'cli'}, {}, self.origin)
        self.assertEqual(len(result['turns']),147)
    def test_failed_session_keeps_old_body_and_next_session_runs(self):
        db.replace_messages(self.c,self.sid,[{'role':'user','text':'保留旧正文'}],'cohub')
        db.upsert(self.c,'cohub:a:good','cohub',source='cohub',data={'spaceId':'space'})
        self.c.commit()
        def fake(cfg,s,o,cursor):
            if s['id']==self.sid: raise RuntimeError('暂不可用')
            return {'turns':[],'files':[],'full':True,'file_limit':False}
        with patch.object(cloudsync,'fetch_session',side_effect=fake),patch.object(cloudsync.time,'sleep'):
            result=cloudsync.backfill(self.c,{'cohubCommand':'cli'})
        self.assertEqual(result,{'processed':2,'failed':1})
        self.assertEqual(db.detail(self.c,self.sid)['messages'][0]['text'],'保留旧正文')
        self.assertIsNone(db.checkpoint(self.c,'detail:'+self.sid))
        self.assertIsNotNone(db.checkpoint(self.c,'detail:cohub:a:good'))
    def test_catalog_stops_after_unchanged_pages_and_invalidates_same_time_edit(self):
        item={'id':'s','spaceId':'space','title':'题目','lastMessageAt':'2026-11-11T01:00:00Z','status':'unknown','lastMessageId':'a'}
        def run(cmd,args,*unused):
            if args[0]=='auth': return {'user':{'uuid':'a'}}
            if args[0]=='apps': return {'items':[],'pageInfo':{'hasMore':False}}
            if '--cursor' in args: return {'sessions':[],'pageInfo':{'hasMore':True,'nextCursor':'would-scan-history'}}
            return {'sessions':[item],'pageInfo':{'hasMore':True,'nextCursor':'page2'}}
        cfg={'cohubCommand':'cli','cohubEnabled':True}
        with patch.object(db,'run_json',side_effect=run) as call:
            db.sync_cohub(self.c,cfg)
            self.assertEqual(sum(x.args[1][0]=='me' for x in call.call_args_list),2)
            db.checkpoint(self.c,'detail:'+self.sid,'2026-11-11T01:00:00Z');self.c.commit()
            item['lastMessageId']='changed-in-same-second'
            # The changed page is followed by two unchanged pages.
            def changed(cmd,args,*unused):
                r=run(cmd,args)
                if '--cursor' in args: r['pageInfo']={'hasMore':False}
                return r
            call.side_effect=changed;db.sync_cohub(self.c,cfg)
        self.assertIsNone(db.checkpoint(self.c,'detail:'+self.sid))
    def test_today_counts_host_labels_and_beijing_boundary(self):
        from datetime import datetime,timezone,timedelta
        now=datetime.now(timezone(timedelta(hours=8)))
        ts=now.isoformat()
        db.upsert(self.c,'codex:a','codex',updated=ts)
        db.upsert(self.c,'codex:a','codex',updated=ts,source='mirasim')
        db.upsert(self.c,'claude:a','claude',updated=ts)
        self.c.commit()
        with patch.object(db,'DB',self.root/'test.sqlite'):
            today=indexapi.today_snapshot()
        self.assertEqual(today['counts']['codex'],1);self.assertEqual(today['counts']['mirasim'],1)
        self.assertEqual(today['counts']['claude'],1)
        self.assertEqual(len([x for x in today['items'] if x['id']=='codex:a']),1)
    def test_preview_only_registered_images_and_checks_magic(self):
        p=self.root/'image.png';p.write_bytes(b'\x89PNG\r\n\x1a\nfixture')
        aid=db.artifact(self.c,'图片',str(p),'codex','fixture')
        data,mime=imagepreview.resolve(self.c,aid);self.assertEqual(mime,'image/png')
        with self.assertRaises(ValueError): imagepreview.resolve(self.c,'unknown')
        p.write_text('<html>not an image</html>')
        with self.assertRaises(ValueError): imagepreview.resolve(self.c,aid)
    def test_remote_preview_rejects_private_network(self):
        with self.assertRaises(ValueError): imagepreview.public_url('http://127.0.0.1/private.png')
        with self.assertRaises(ValueError): imagepreview.public_url('file:///etc/passwd')

if __name__=='__main__': unittest.main()
