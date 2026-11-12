#!/usr/bin/env python3
"""Incrementally register explicitly selected images/HTML; no directory crawl or AI."""
import argparse,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'lib'))
from desk import indexdb
from desk.paths import iso
p=argparse.ArgumentParser(description=__doc__);p.add_argument('files',nargs='+');args=p.parse_args()
changed=0
with indexdb.connect() as c:
    for value in args.files:
        path=Path(value).expanduser().resolve()
        if not path.is_file() or path.suffix.lower() not in ('.html','.htm','.png','.jpg','.jpeg','.svg','.webp','.gif'):
            raise SystemExit('只支持现有图片 / HTML 文件：'+str(path))
        stat=path.stat(); fp=f'{stat.st_mtime_ns}:{stat.st_size}'
        key='manual:'+str(path)
        if indexdb.checkpoint(c,key)==fp: continue
        indexdb.artifact(c,path.name,str(path),'manual','手动登记',updated=iso())
        indexdb.checkpoint(c,key,fp);changed+=1
    c.commit()
print(f'新增或变化 {changed} 个文件；原文件保持原位。刷新作品展台即可。')
