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
from datetime import datetime, timezone, timedelta
from pathlib import Path

STATE_PATH = Path(axion_path_str('data', 'apps', 'clock', 'state.json'))

DEFAULT = {
    "alarms": [],
    "timers": [],
    "world_clocks": ["UTC", "America/New_York"]
}


def _load():
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text(encoding='utf-8-sig'))
    return json.loads(json.dumps(DEFAULT))


def _save(state):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding='utf-8')


def add_alarm(label: str, iso_time: str):
    s = _load()
    s['alarms'].append({"label": label, "iso_time": iso_time, "enabled": True})
    _save(s)
    return {"ok": True, "code": "CLOCK_ALARM_ADD_OK"}


def add_timer(label: str, seconds: int):
    s = _load()
    end = (datetime.now(timezone.utc) + timedelta(seconds=int(seconds))).isoformat()
    s['timers'].append({"label": label, "seconds": int(seconds), "end": end, "enabled": True})
    _save(s)
    return {"ok": True, "code": "CLOCK_TIMER_ADD_OK", "end": end}


def snapshot():
    return _load()


if __name__ == '__main__':
    print(json.dumps(snapshot(), indent=2))

