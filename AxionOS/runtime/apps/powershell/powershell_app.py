import json
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[3] / 'data' / 'apps' / 'powershell'
ROOT.mkdir(parents=True, exist_ok=True)
HISTORY = ROOT / 'history.ndjson'

_BLOCKED = ('remove-item ', 'format-volume', 'clear-disk', 'stop-computer', 'shutdown')


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _append_history(entry: dict):
    with HISTORY.open('a', encoding='utf-8') as f:
        f.write(json.dumps(entry) + "\n")


def run_command(command: str):
    cmd = str(command or '').strip()
    lower = cmd.lower()
    if not cmd:
        return {'ok': False, 'code': 'POWERSHELL_EMPTY_COMMAND'}
    if any(lower.startswith(x) for x in _BLOCKED):
        out = {'ok': False, 'code': 'POWERSHELL_BLOCKED_COMMAND', 'command': cmd}
        _append_history({'ts': _now_iso(), 'command': cmd, 'result': out['code']})
        return out

    if lower in ('get-date', 'date'):
        stdout = _now_iso()
        code = 'POWERSHELL_EXECUTION_OK'
    elif lower in ('get-process', 'ps'):
        stdout = 'systemd\naxion-shell\ncommand-capsule'
        code = 'POWERSHELL_EXECUTION_OK'
    elif lower.startswith('get-childitem') or lower.startswith('ls'):
        stdout = 'Program Files\nProgram Modules\nSandbox Projections'
        code = 'POWERSHELL_EXECUTION_OK'
    else:
        stdout = 'Simulated PowerShell execution in Axion capsule.'
        code = 'POWERSHELL_EXECUTION_SIMULATED'

    out = {'ok': True, 'code': code, 'command': cmd, 'stdout': stdout}
    _append_history({'ts': _now_iso(), 'command': cmd, 'result': out['code']})
    return out


def snapshot():
    count = 0
    if HISTORY.exists():
        with HISTORY.open('r', encoding='utf-8') as f:
            for _ in f:
                count += 1
    return {
        'app': 'PowerShell',
        'profile': 'powershell',
        'history_count': count,
    }


if __name__ == '__main__':
    print(json.dumps(snapshot(), indent=2))
