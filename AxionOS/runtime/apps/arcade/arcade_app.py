import sys
from pathlib import Path

_TOOLS_DIR = None
for _parent in Path(__file__).resolve().parents:
    if (_parent / "tools" / "common" / "pathing.py").exists():
        _TOOLS_DIR = _parent / "tools"
        break
if _TOOLS_DIR and str(_TOOLS_DIR) not in sys.path:
    sys.path.append(str(_TOOLS_DIR))

from common.pathing import axion_path


def axion_path_str(*parts):
    return str(axion_path(*parts))


import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(axion_path_str('data', 'apps', 'arcade'))
ROOT.mkdir(parents=True, exist_ok=True)
STATE = ROOT / 'state.json'


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def snapshot():
    base = {
        'app': 'Arcade',
        'app_id': 'arcade',
        'ready': True,
        'updated_utc': _now_iso(),
    }
    if STATE.exists():
        try:
            existing = json.loads(STATE.read_text(encoding='utf-8-sig'))
            if isinstance(existing, dict):
                base.update(existing)
        except Exception:
            pass
    STATE.write_text(json.dumps(base, indent=2) + '\n', encoding='utf-8')
    return base


if __name__ == '__main__':
    print(json.dumps(snapshot(), indent=2))
