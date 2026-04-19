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

STATE_PATH = Path(axion_path_str('data', 'apps', 'calendar', 'state.json'))

DEFAULT = {"events": []}


def _load():
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text(encoding='utf-8-sig'))
    return json.loads(json.dumps(DEFAULT))


def _save(state):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding='utf-8')


def add_event(title: str, start_iso: str, end_iso: str, reminder_min: int = 15):
    s = _load()
    s['events'].append({
        "title": title,
        "start": start_iso,
        "end": end_iso,
        "reminder_min": int(reminder_min)
    })
    _save(s)
    return {"ok": True, "code": "CAL_EVENT_ADD_OK"}


def list_events():
    return _load()['events']


if __name__ == '__main__':
    print(json.dumps(_load(), indent=2))

