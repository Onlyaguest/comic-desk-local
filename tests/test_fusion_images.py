import tempfile,unittest,json,sys,sqlite3,io,threading
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'lib'))
try:
 from PIL import Image
except ImportError:Image=None
from desk.fusion import image_catalog as g
@unittest.skipIf(Image is None,'可选Pillow未安装，SVG黑盒测试仍覆盖核心图片API')
class ImageTests(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.base=Path(self.t.name);self.db=self.base/'db.sqlite3';c=sqlite3.connect(self.db);c.execute('create table artifacts(id text,title text,target text,kind text,source text,updated text)')
  self.im=self.base/'large.png';Image.new('RGB',(2000,1000),'red').save(self.im)
  rows=[('good','图',str(self.im),'image','codex','1'),('bad','坏图',str(self.base/'gone.png'),'image','codex','1'),('remote','云图','https://example.com/a.png','image','cohub','1')]
  c.executemany('insert into artifacts values(?,?,?,?,?,?)',rows);c.commit();c.close();self.patches=[patch.object(g.db,'DB',self.db),patch.object(g,'ROOT',self.base/'cache'),patch.object(g.db,'BASE',self.base),patch.object(g.db,'config',return_value={'demo':False})];[p.start() for p in self.patches];g.FAILURES.clear()
 def tearDown(self):[p.stop() for p in self.patches];self.t.cleanup()
 def test_all_pages_and_statuses(self):
  a=g.catalog(limit=1);b=g.catalog(offset=1,limit=1);self.assertEqual(a['registered'],3);self.assertEqual(a['counts'],{'ready':1,'remote':1,'missing':1,'failed':0});self.assertNotEqual(a['items'][0]['id'],b['items'][0]['id']);self.assertEqual(a['metrics']['thisCatalogRemoteReads'],0)
 def test_catalog_can_reach_beyond_first_hundred(self):
  c=sqlite3.connect(self.db);c.executemany('insert into artifacts values(?,?,?,?,?,?)',[(f'extra-{i:03}','分页样例',str(self.im),'image','codex','1') for i in range(110)]);c.commit();c.close()
  result=g.catalog(offset=100,limit=24);self.assertEqual(result['registered'],113);self.assertEqual(len(result['items']),13);self.assertFalse(result['hasMore'])
 def test_real_thumbnail_small_and_cache(self):
  a,typ=g.resolve('good');self.assertEqual(typ,'image/webp');im=Image.open(io.BytesIO(a));self.assertLessEqual(max(im.size),480);b,_=g.resolve('good');self.assertEqual(a,b)
 def test_cloud_not_auto_fetched(self):
  with patch.object(g.urllib.request,'Request',side_effect=AssertionError('不应联网')):
   with self.assertRaises(ValueError):g.resolve('remote')
 def test_unregistered_path_rejected(self):
  with self.assertRaises(ValueError):g.resolve('../../etc/passwd')
 def test_failure_cached_no_auto_retry(self):
  with patch.object(g.imagepreview,'public_url',side_effect=ValueError('受限地址')) as m:
   a=g.fetch('remote');b=g.fetch('remote');self.assertFalse(a['ok']);self.assertTrue(b['cooldown']);self.assertEqual(m.call_count,1)
 def test_original_stays_full_size(self):
  raw,_=g.resolve('good','full');self.assertEqual(Image.open(io.BytesIO(raw)).size,(2000,1000))
