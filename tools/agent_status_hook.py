#!/usr/bin/env python3
"""Claude Code / Codex 钩子：AI 状态一变，往工作台本机账本追加一行。

用法（由 tools/agent_hooks.py install 写进钩子配置，不必手动调用）：
    python3 tools/agent_status_hook.py claude   < 钩子 JSON
    python3 tools/agent_status_hook.py codex    < 钩子 JSON

只追加 data/fusion/agent-status.jsonl；不记提示词和回复正文。
永远不写 stdout（Claude Code 会把 UserPromptSubmit 的 stdout 当上下文），任何错误都 exit 0。
"""
import json, os, sys, time
from pathlib import Path

LEDGER = Path(__file__).resolve().parents[1] / 'data' / 'fusion' / 'agent-status.jsonl'
WAITING_NOTICES = ('permission_prompt', 'idle_prompt', 'elicitation_dialog')
EVENTS = {
    'claude': {'UserPromptSubmit': 'working', 'Notification': 'waiting', 'PermissionRequest': 'waiting',
               'Stop': 'done', 'StopFailure': 'error'},
    'codex': {'UserPromptSubmit': 'working', 'PermissionRequest': 'waiting', 'Interrupt': 'waiting',
              'Stop': 'done'},
}


def record(agent, payload, now=None):
    """钩子输入 → 一行账本；不认识的事件返回 None。"""
    event = str(payload.get('hook_event_name') or '')
    state = EVENTS.get(agent, {}).get(event)
    if not state:
        return None
    if event == 'Notification' and payload.get('notification_type') not in WAITING_NOTICES:
        return None
    sid = str(payload.get('session_id') or '')
    if not sid:
        return None
    detail = ''
    if state == 'waiting':
        detail = str(payload.get('message') or payload.get('tool_name') or ('被打断' if event == 'Interrupt' else ''))
    elif state == 'error':
        detail = str(payload.get('error') or payload.get('error_type') or '')
    return {'at': int((now or time.time()) * 1000), 'agent': agent, 'session': sid, 'event': event,
            'state': state, 'cwd': str(payload.get('cwd') or ''), 'detail': detail[:80]}


def append(row, ledger=None):
    ledger = Path(ledger or LEDGER)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    line = (json.dumps(row, ensure_ascii=False) + '\n').encode('utf-8')
    fd = os.open(ledger, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    try:
        os.write(fd, line)  # 一行一次 O_APPEND 写入，多个会话同时写也不会把行写乱
    finally:
        os.close(fd)


def main(argv):
    try:
        agent = argv[1] if len(argv) > 1 else ''
        payload = json.loads(sys.stdin.read(1 << 20) or '{}')
        row = record(agent, payload) if isinstance(payload, dict) else None
        if row:
            append(row)
    except Exception:
        pass  # 报状态失败不能拖累 AI 干活
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
