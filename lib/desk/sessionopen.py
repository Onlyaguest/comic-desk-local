"""Open an indexed native Claude conversation in an interactive terminal, without sending a prompt."""
import os
import shlex
import shutil
import subprocess
import uuid
from pathlib import Path
from . import indexdb
import threading,time
MIRASIM_OPEN_LOCK=threading.Lock()

def open_mirasim(native):
    with MIRASIM_OPEN_LOCK:
        cfg=indexdb.config();args=indexdb.mirasim_args(cfg);cmd=cfg['mirasimCommand']
        def run(*parts): return indexdb.run_json(cmd,[*args,*parts])
        def activate():
            if subprocess.run(['open','-a','Mirasim'],capture_output=True,timeout=15).returncode:
                raise RuntimeError('无法激活 Mirasim App')
        activate()
        state=run('ui','ui.state')
        locale=(state.get('data') or {}).get('locale','')
        if not locale.startswith(('zh','en')):
            raise RuntimeError('当前 Mirasim 界面语言尚未适配空间定位，请先切换到本机后在原应用打开')
        # session open targets the front space, not necessarily this local host.
        # Switch through the registered space menu, then activate the local window.
        if state.get('window')!='main':
            run('ui','host.panel','--value','open')
            menu=run('dom','--selector','[role="menu"]')
            labels={'本机','本机默认'} if locale.startswith('zh') else {'Local','LocalDefault','Local Default'}
            entries=[e for e in menu.get('elements',[]) if e.get('role')=='menuitem' and e.get('enabled') and e.get('text','').strip() in labels]
            if len(entries)!=1 or not entries[0].get('selector'):
                raise RuntimeError('无法唯一定位空间菜单中的本机入口')
            clicked=run('click','--selector',entries[0]['selector'])
            if clicked.get('matched')!=1: raise RuntimeError('无法唯一定位 Mirasim 本机空间')
        # Do not activate again: macOS may refocus the previous cloud window.
        # Wait for the renderer route to settle before dispatching pane.open.
        stable=0
        for attempt in range(20):
            state=run('ui','ui.state')
            stable=stable+1 if state.get('window')=='main' else 0
            if stable>=3: break
            time.sleep(.3)
        else: raise RuntimeError('Mirasim 尚未切到本机，未在其他空间打开会话')
        result=run('ui','pane.open','--value',native,'--window','main')
        if result.get('window')!='main' or result.get('result')!=native:
            raise RuntimeError('Mirasim 未确认在本机打开指定会话')
        run('navigate','--to','sessions')
        view=run('ui','workspace.state','--window','main')
        data=view.get('data') or {};panes=data.get('panes') or [];active=data.get('activeIndex',-1)
        if view.get('window')!='main' or not isinstance(active,int) or not 0<=active<len(panes) or panes[active].get('sessionKey')!=native:
            raise RuntimeError('Mirasim 当前面板不是目标会话，请重试')
        return {'ok':True,'opened_in':'Mirasim','verified_session':native}

def open_claude(c,row):
    origin=c.execute("SELECT native_id FROM origins WHERE session_id=? AND source='claude'",(row['id'],)).fetchone()
    if not origin: raise ValueError('此记录没有 Claude 原生会话入口')
    try: native=str(uuid.UUID(origin[0]))
    except (ValueError,TypeError): raise ValueError('这条记录不是可恢复的 Claude 主会话，请查看索引详情')
    if row['parent']: raise ValueError('Claude 子会话不能独立恢复，请回主会话打开')
    cwd=Path(row['workspace'])
    if not cwd.is_absolute() or not cwd.is_dir(): raise ValueError('原项目目录已不存在，无法在原位置恢复 Claude')
    binary=shutil.which('claude')
    if not binary: raise RuntimeError('本机未找到 Claude Code CLI')
    folder=indexdb.BASE/'data/session-launchers';folder.mkdir(parents=True,exist_ok=True,mode=0o700)
    launcher=folder/(native+'.command')
    command=' '.join(shlex.quote(x) for x in (binary,'--resume',native))
    launcher.write_text('#!/bin/zsh\n# 仅打开交互式会话；不传入任务或自动发送消息。\n'
                        +'export PATH='+shlex.quote(os.environ.get('PATH','/opt/homebrew/bin:/usr/bin:/bin'))+'\n'
                        +'cd -- '+shlex.quote(str(cwd))+' || exit 1\nexec '+command+'\n')
    launcher.chmod(0o700)
    result=subprocess.run(['open','-a','Terminal',str(launcher)],capture_output=True,timeout=15)
    if result.returncode: raise RuntimeError('无法打开终端中的 Claude 会话')
    return {'ok':True,'opened_in':'Claude Code 终端'}
