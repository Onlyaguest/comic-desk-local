"""候选发布文件共用边界：包含未暂存源码，排除忽略数据，拒绝符号链接。"""
import shutil
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def candidates(root=ROOT):
    names=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=root).decode().split('\0')
    result=[]
    for name in sorted(set(names)-{''}):
        p=Path(root)/name
        if p.is_symlink():raise ValueError('候选文件含符号链接：'+name)
        if p.is_file():result.append(name)
    return result


def copy_candidate(target,root=ROOT):
    for name in candidates(root):
        dest=Path(target)/name;dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(Path(root)/name,dest)
