"""融合入口：只绑定本机，复用离线优先的索引与账本。"""
import html, os, urllib.parse
from desk.paths import ROOT as HERE, APP
from desk.server import Handler as OriginalHandler, _json
from . import bridge, session_board, bounded_sync, image_catalog, governance


class Handler(OriginalHandler):
    def allowed(self):
        return self.headers.get('Host', '').split(':')[0] in ('127.0.0.1', 'localhost')

    def do_GET(self):
        if not self.allowed():
            return _json(self, 403, {'error': '仅本机访问'})
        path = urllib.parse.urlparse(self.path).path
        if path == '/api/health':
            return _json(self, 200, {'ok': True, 'root': str(HERE), 'version': 'desk-fusion-release', 'revision':'2.2', 'pid': os.getpid()})
        if path == '/api/desk/images':
            q=urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            one=lambda k,d='':q.get(k,[d])[0]
            try:return _json(self,200,image_catalog.catalog(one('q'),one('source'),one('status'),one('offset',0),one('limit',24)))
            except (ValueError,OSError):return _json(self,400,{'error':'图片查询参数无效'})
        if path in ('/api/desk/image','/api/index/image'):
            q=urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query);key=q.get('id',[''])[0]
            try:return image_catalog.serve(self,key,q.get('mode',['thumb'])[0])
            except (ValueError,RuntimeError,OSError) as e:
                try:image_catalog.FAILURES[key]={'reason':str(e)[:150],'at':__import__('time').time(),'revision':image_catalog.revision(image_catalog.row_for(key))}
                except ValueError:pass
                return _json(self,422,{'error':str(e)[:150]})
        if path == '/api/index/cover':return _json(self,200,image_catalog.cover())
        if path == '/api/desk/evidence':
            q=urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            try:
                p=governance.registered_evidence(q.get('receipt',[''])[0],int(q.get('index',['0'])[0]));data=p.read_bytes()
                if p.suffix!='.html':data=('<!doctype html><html lang=zh-CN><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>回写核对依据</title><body style="max-width:900px;margin:30px auto;padding:20px;color:#302519;background:#fff6df;font:15px/1.8 -apple-system,PingFang SC,sans-serif"><h1>'+html.escape(p.name)+'</h1><pre style="white-space:pre-wrap;overflow-wrap:anywhere">'+html.escape(data.decode('utf-8',errors='replace'))+'</pre></body></html>').encode()
                self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store');self.send_header('Content-Security-Policy',"default-src 'none'; img-src data: 'self'; style-src 'unsafe-inline'; sandbox");self.end_headers();self.wfile.write(data);return
            except ValueError as e:return _json(self,404,{'error':str(e)})
        if path == '/api/desk/card':
            q=urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            try:return _json(self,200,session_board.card_detail(q.get('id',[''])[0]))
            except ValueError as e:return _json(self,404,{'error':str(e)})
        if path == '/api/desk/board':
            q=urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            raw=q.get('days',['7'])[0]
            days={'7':7,'30':30,'all':0}.get(raw,7)
            pins=q.get('pin',[])[:12]
            return _json(self,200,session_board.snapshot(days=days,pins=pins))
        if path == '/api/desk/space':
            return _json(self, 200, bridge.state())
        if path in ('/', '/index.html'):
            return self._static('index.html')
        if path.startswith('/desk-v2/'):
            return self.version_file(path[len('/desk-v2/'):])
        if path == '/js/index-refresh.js':return self.version_file('index-refresh.js')
        if path == '/original.html':
            return self._static('original.html')
        # v2/data、源码和凭据均不作为静态资源暴露。
        return super().do_GET()

    def version_file(self, rel):
        p = (APP / 'fusion' / rel).resolve()
        if not p.is_relative_to((APP / 'fusion').resolve()) or not p.is_file():
            return _json(self, 404, {'error': '没有这个文件'})
        body = p.read_bytes()
        mime = {'.html': 'text/html', '.css': 'text/css', '.js': 'application/javascript'}.get(p.suffix, 'application/octet-stream')
        self.send_response(200)
        self.send_header('Content-Type', mime + '; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        route=urllib.parse.urlparse(self.path).path
        if route not in ('/api/desk/space/refresh','/api/desk/sync-index','/api/desk/image-fetch','/api/desk/image-cover'):
            return super().do_POST()
        if not self.allowed():
            return _json(self, 403, {'error': '仅本机访问'})
        origin = self.headers.get('Origin')
        if (origin and origin != 'http://' + self.headers.get('Host', '')) or self.headers.get('Sec-Fetch-Site') == 'cross-site':
            return _json(self, 403, {'error': '仅接受同源操作'})
        if int(self.headers.get('Content-Length', '0')) > 512:
            return _json(self, 400, {'error': '刷新不接受远端地址或命令参数'})
        raw=self.rfile.read(int(self.headers.get('Content-Length','0')))
        if route in ('/api/desk/image-fetch','/api/desk/image-cover'):
            try:
                body=__import__('json').loads(raw or '{}')
                result=image_catalog.fetch(str(body.get('id','')),bool(body.get('retry'))) if route.endswith('fetch') else image_catalog.set_cover(str(body.get('id','')))
                return _json(self,200 if result.get('ok') else 422,result)
            except (ValueError,RuntimeError):return _json(self,400,{'error':'图片未登记或当前不可读取'})
        if route == '/api/desk/sync-index':
            result=bounded_sync.run()
            return _json(self,200 if result.get('ok') else 502,result)
        result = bridge.refresh()
        return _json(self, 200 if result['ok'] and not result['error'] else 502, result)
