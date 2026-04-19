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
from pathlib import Path
from datetime import datetime, timezone

STATE_PATH = Path(axion_path_str('config', 'TOGGLES_STATE_V1.json'))
AUDIT_PATH = Path(axion_path_str('data', 'audit', 'toggles.ndjson'))


def _now():
    return datetime.now(timezone.utc).isoformat()


def load_state():
    return json.loads(STATE_PATH.read_text(encoding='utf-8-sig'))


def _save(state):
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding='utf-8')


def _audit(evt):
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    evt['ts'] = evt.get('ts', _now())
    with AUDIT_PATH.open('a', encoding='utf-8') as f:
        f.write(json.dumps(evt) + '\n')


def set_toggle(name: str, value: bool, corr: str = 'corr_toggles_001'):
    s = load_state()
    t = s.get('toggles', {})
    if name not in t:
        out = {"ok": False, "code": "TOGGLE_UNKNOWN", "name": name}
        _audit({"corr": corr, "event": "toggle.set", **out})
        return out
    old = t[name]
    t[name] = bool(value)
    _save(s)
    out = {"ok": True, "code": "TOGGLE_SET_OK", "name": name, "old": old, "new": bool(value)}
    _audit({"corr": corr, "event": "toggle.set", **out})
    return out


def list_toggles():
    return load_state().get('toggles', {})


if __name__ == '__main__':
    print(json.dumps(list_toggles(), indent=2))

