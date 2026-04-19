import json
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[3] / 'data' / 'apps' / 'command_prompt'
ROOT.mkdir(parents=True, exist_ok=True)
HISTORY = ROOT / 'history.ndjson'

_BLOCKED = ('del ', 'format ', 'shutdown ', 'rd /s', 'erase ')
_ALLOWED_PREFIXES = ('echo ', 'dir', 'cd ', 'type ', 'cls', 'ver', 'help')


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _append_history(entry: dict):
    with HISTORY.open('a', encoding='utf-8') as f:
        f.write(json.dumps(entry) + "\n")


def run_command(command: str):
    cmd = str(command or '').strip()
    lowered = cmd.lower()
    if not cmd:
        return {'ok': False, 'code': 'CMD_EMPTY_COMMAND'}
    if any(lowered.startswith(x) for x in _BLOCKED):
        out = {'ok': False, 'code': 'CMD_BLOCKED_COMMAND', 'command': cmd}
        _append_history({'ts': _now_iso(), 'command': cmd, 'result': out['code']})
        return out
    if not any(lowered.startswith(prefix) for prefix in _ALLOWED_PREFIXES):
        out = {'ok': True, 'code': 'CMD_EXECUTION_SIMULATED', 'command': cmd, 'stdout': 'Simulated execution in Axion command capsule.'}
        _append_history({'ts': _now_iso(), 'command': cmd, 'result': out['code']})
        return out

    stdout = ''
    if lowered == 'dir':
        stdout = 'Program Files\nProgram Files (86)\nProgram Modules\nSandbox Projections'
    elif lowered.startswith('echo '):
        stdout = cmd[5:]
    elif lowered == 'ver':
        stdout = 'AxionOS Command Runtime 1.0.0'
    elif lowered == 'help':
        stdout = 'Supported: dir, echo, cd, type, cls, ver, help'
    elif lowered == 'cls':
        stdout = ''
    else:
        stdout = 'Command accepted.'

    out = {'ok': True, 'code': 'CMD_EXECUTION_OK', 'command': cmd, 'stdout': stdout}
    _append_history({'ts': _now_iso(), 'command': cmd, 'result': out['code']})
    return out


def snapshot():
    count = 0
    if HISTORY.exists():
        with HISTORY.open('r', encoding='utf-8') as f:
            for _ in f:
                count += 1
    return {
        'app': 'Command Prompt',
        'profile': 'cmd',
        'history_count': count,
    }


if __name__ == '__main__':
    print(json.dumps(snapshot(), indent=2))
