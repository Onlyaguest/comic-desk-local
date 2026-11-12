"""Serve only registered image artifacts. Cache by target + source revision."""
import hashlib
import ipaddress
import mimetypes
import re
import socket
import subprocess
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path
from . import indexdb as db

MAX_BYTES=60*1024*1024

def public_url(url):
    p=urllib.parse.urlparse(url)
    if p.scheme not in ('http','https') or p.username or p.password or not p.hostname:
        raise ValueError('图片地址无效')
    for address in socket.getaddrinfo(p.hostname,p.port or (443 if p.scheme=='https' else 80)):
        if not ipaddress.ip_address(address[4][0]).is_global:
            raise ValueError('远端图片地址不能指向本机或内网')
    return url

class PublicRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        public_url(newurl)
        return super().redirect_request(req,fp,code,msg,headers,newurl)

def mime(data):
    if data.startswith(b'\x89PNG\r\n\x1a\n'): return 'image/png'
    if data.startswith(b'\xff\xd8\xff'): return 'image/jpeg'
    if data[:6] in (b'GIF87a',b'GIF89a'): return 'image/gif'
    if data[:4]==b'RIFF' and data[8:12]==b'WEBP': return 'image/webp'
    if data[:2]==b'BM': return 'image/bmp'
    if data[4:8]==b'ftyp' and b'avif' in data[8:32]: return 'image/avif'
    if re.match(br'\s*(?:<\?xml[^>]*>\s*)?(?:<!--.*?-->\s*)*<svg(?:\s|>)',data[:4096],re.S): return 'image/svg+xml'
    return None

def resolve(c,key):
    row=c.execute('SELECT * FROM artifacts WHERE id=?',(key,)).fetchone()
    if not row: raise ValueError('图片未登记')
    target=row['target'];p=urllib.parse.urlparse(target)
    suffix=Path(urllib.parse.unquote(p.path)).suffix.lower()
    if row['kind']!='image' and suffix not in ('.png','.jpg','.jpeg','.gif','.webp','.avif','.svg','.bmp','.heic','.tiff','.tif'):
        raise ValueError('这条产物不是图片')
    revision=hashlib.sha256((target+'|'+(row['updated'] or '')).encode()).hexdigest()[:20]
    folder=db.BASE/'data/image-cache'/key/revision
    dest=folder/('image'+(suffix if re.fullmatch(r'\.[a-z0-9]{1,6}',suffix) else '.bin'))
    if p.scheme in ('http','https','cohub-file'):
        if not dest.exists():
            folder.mkdir(parents=True,exist_ok=True); temp=None
            try:
                with tempfile.NamedTemporaryFile(dir=folder,delete=False) as f:
                    temp=Path(f.name)
                    if p.scheme=='cohub-file':
                        remote=urllib.parse.unquote(p.path).lstrip('/')
                        if '..' in Path(remote).parts or not p.netloc: raise ValueError('云端图片路径无效')
                        import os
                        proc=subprocess.run([db.config()['cohubCommand'],'-s',p.netloc,'spaces','files','cat',remote],
                                            stdout=f,stderr=subprocess.PIPE,timeout=120,env={**os.environ,'COHUB_CLI_AUTO_UPDATE':'0'})
                        if proc.returncode: raise RuntimeError('云端原图暂不可读，可能已移动、删除或无权访问')
                    else:
                        request=urllib.request.Request(public_url(target),headers={'User-Agent':'LocalDesk-ImagePreview/1.0'})
                        with urllib.request.build_opener(PublicRedirect).open(request,timeout=30) as response:
                            size=0
                            while True:
                                block=response.read(256*1024)
                                if not block: break
                                size+=len(block)
                                if size>MAX_BYTES: raise ValueError('图片超过 60 MB，请打开原件')
                                f.write(block)
                if temp.stat().st_size>MAX_BYTES: raise ValueError('图片超过 60 MB，请打开原件')
                temp.replace(dest)
            finally:
                if temp and temp.exists(): temp.unlink()
        source=dest
    elif not p.scheme or p.scheme=='file': source=Path(urllib.parse.unquote(p.path))
    else: raise ValueError('不支持此图片地址')
    if not source.is_file(): raise ValueError('本机原图已移动或删除')
    if source.stat().st_size>MAX_BYTES: raise ValueError('图片超过 60 MB，请打开原件')
    data=source.read_bytes();content_type=mime(data)
    if not content_type and suffix in ('.heic','.tif','.tiff'):
        folder.mkdir(parents=True,exist_ok=True);converted=folder/'preview.png'
        if not converted.exists():
            proc=subprocess.run(['sips','-s','format','png',str(source),'--out',str(converted)],capture_output=True,timeout=30)
            if proc.returncode: raise RuntimeError('Mac 无法转换此图片')
        data=converted.read_bytes();content_type=mime(data)
    if not content_type: raise ValueError('原件不是可识别的图片，可能链接已失效')
    return data,content_type

def serve(handler,c,key):
    data,content_type=resolve(c,key)
    handler.send_response(200)
    handler.send_header('Content-Type',content_type)
    handler.send_header('Content-Length',str(len(data)))
    handler.send_header('Cache-Control','private, max-age=60')
    handler.send_header('X-Content-Type-Options','nosniff')
    handler.send_header('Content-Security-Policy',"default-src 'none'; style-src 'unsafe-inline'; sandbox")
    handler.end_headers();handler.wfile.write(data)
