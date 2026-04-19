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

STATE_PATH = Path(axion_path_str('data', 'state', 'shell_ui_state.json'))


def _now():
    return datetime.now(timezone.utc).isoformat()


def save_state(module: str, state: dict, corr: str = None):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    current = {}
    if STATE_PATH.exists():
        current = json.loads(STATE_PATH.read_text(encoding='utf-8-sig'))

    current[module] = {
        "ts": _now(),
        "corr": corr,
        "state": state
    }
    STATE_PATH.write_text(json.dumps(current, indent=2), encoding='utf-8')
    return {"ok": True, "code": "STATE_SAVE_OK", "module": module}


def load_state(module: str):
    if not STATE_PATH.exists():
        return {"ok": False, "code": "STATE_MISSING"}
    current = json.loads(STATE_PATH.read_text(encoding='utf-8-sig'))
    if module not in current:
        return {"ok": False, "code": "STATE_MODULE_MISSING"}
    return {"ok": True, "code": "STATE_LOAD_OK", "module": module, "data": current[module]}

