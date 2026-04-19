import json
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[3] / 'data' / 'apps' / 'run_dialog'
ROOT.mkdir(parents=True, exist_ok=True)
HISTORY = ROOT / 'history.ndjson'


_ALIAS = {
    'cmd': 'command_prompt',
    'powershell': 'powershell',
    'regedit': 'registry_editor',
    'cleanmgr': 'disk_cleanup',
}


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _append(entry: dict):
    with HISTORY.open('a', encoding='utf-8') as f:
        f.write(json.dumps(entry) + "\n")


def submit(command: str):
    cmd = str(command or '').strip()
    if not cmd:
        return {'ok': False, 'code': 'RUN_DIALOG_EMPTY'}

    token = cmd.split()[0].strip().lower()
    app_id = _ALIAS.get(token)
    out = {
        'ok': True,
        'code': 'RUN_DIALOG_ROUTED' if app_id else 'RUN_DIALOG_UNKNOWN_TARGET',
        'command': cmd,
        'token': token,
        'app_id': app_id,
    }
    _append({'ts': _now_iso(), **out})
    return out


def snapshot():
    count = 0
    if HISTORY.exists():
        with HISTORY.open('r', encoding='utf-8') as f:
            for _ in f:
                count += 1
    return {
        'app': 'Run Dialog',
        'history_count': count,
        'known_aliases': sorted(_ALIAS.keys()),
    }


if __name__ == '__main__':
    print(json.dumps(snapshot(), indent=2))
