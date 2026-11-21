#!/usr/bin/env python3
"""给自己的 Claude Code / Codex 装上「AI 自己报状态」钩子。只有你跑这条命令才会改配置。

    python3 tools/agent_hooks.py show                 # 只打印要加的配置，不改任何文件
    python3 tools/agent_hooks.py install claude codex # 写进 ~/.claude/settings.json、~/.codex/hooks.json
    python3 tools/agent_hooks.py uninstall claude codex

改之前把原文件备份成 <文件>.bak-<时间>；只增删命令里带 agent_status_hook.py 的那几条，你自己的钩子原样保留。
重复 install 不会加出第二份。Codex 第一次启动会提示「Hooks need review」，选信任后才会生效。
"""
import json, os, shlex, sys, time
from pathlib import Path

HOOK = Path(__file__).resolve().with_name('agent_status_hook.py')
MARK = 'agent_status_hook.py'
EVENTS = {
    'claude': ['UserPromptSubmit', 'Notification', 'PermissionRequest', 'Stop', 'StopFailure'],
    'codex': ['UserPromptSubmit', 'PermissionRequest', 'Interrupt', 'Stop'],
}


def target(agent):
    if agent == 'claude':
        return Path(os.environ.get('CLAUDE_CONFIG_DIR') or Path.home() / '.claude') / 'settings.json'
    return Path(os.environ.get('CODEX_HOME') or Path.home() / '.codex') / 'hooks.json'


def command(agent):
    return ' '.join(shlex.quote(x) for x in (sys.executable or 'python3', str(HOOK), agent))


def ours(group):
    return any(MARK in str(h.get('command', '')) for h in group.get('hooks', []) if isinstance(h, dict))


def strip(config):
    hooks = config.get('hooks')
    if not isinstance(hooks, dict):
        return config  # 形状不认识就不碰
    for event in list(hooks):
        if not isinstance(hooks[event], list):
            continue
        groups = [g for g in hooks[event] if not (isinstance(g, dict) and ours(g))]
        if groups:
            hooks[event] = groups
        else:
            del hooks[event]
    if not hooks:
        config.pop('hooks', None)
    return config


def add(config, agent):
    strip(config)
    hooks = config.setdefault('hooks', {})
    if not isinstance(hooks, dict) or any(not isinstance(hooks.get(e, []), list) for e in EVENTS[agent]):
        raise ValueError('hooks 的格式和预期不一样，没有改动；请手动对照 show 的输出添加')
    for event in EVENTS[agent]:
        hooks.setdefault(event, []).append({'hooks': [{'type': 'command', 'command': command(agent), 'timeout': 5}]})
    return config


def load(path):
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding='utf-8') or '{}')
    if not isinstance(data, dict):
        raise ValueError(f'{path} 不是 JSON 对象，没有改动')
    return data


def save(path, config):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        backup = path.with_name(path.name + '.bak-' + time.strftime('%Y%m%d%H%M%S'))
        backup.write_bytes(path.read_bytes())
        print(f'  已备份 {backup}')
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(config, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    tmp.replace(path)


def main(argv):
    if len(argv) < 2 or argv[1] not in ('show', 'install', 'uninstall'):
        print(__doc__.strip())
        return 2
    agents = [a for a in argv[2:] if a in EVENTS] or list(EVENTS)
    for agent in agents:
        path = target(agent)
        if argv[1] == 'show':
            print(f'# {agent} → {path}')
            print(json.dumps(add({}, agent), ensure_ascii=False, indent=2))
            continue
        try:
            config = load(path)
        except ValueError as e:
            print(f'{agent}: {e}')
            return 1
        before = json.dumps(config, sort_keys=True)
        try:
            config = add(config, agent) if argv[1] == 'install' else strip(config)
        except ValueError as e:
            print(f'{agent}: {e}（{path}）')
            return 1
        if json.dumps(config, sort_keys=True) == before:
            print(f'{agent}: 无需改动（{path}）')
            continue
        save(path, config)
        print(f'{agent}: 已{"装上" if argv[1] == "install" else "去掉"}状态钩子 → {path}')
    if argv[1] == 'install':
        print('状态会追加到 data/fusion/agent-status.jsonl；工作台开页或点「更新」时读取，不轮询、不弹通知。')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
