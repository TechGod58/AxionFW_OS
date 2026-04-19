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
import sys
from pathlib import Path

EVENT_BUS_DIR = Path(axion_path_str('runtime', 'shell_ui', 'event_bus'))
PROFILE_PATH = Path(axion_path_str('config', 'SHELL_UI_PROFILE_V1.json'))
if str(EVENT_BUS_DIR) not in sys.path:
    sys.path.append(str(EVENT_BUS_DIR))

from event_bus import publish
from state_bridge import save_state

STATE = {
    "style": "windows7",
    "alignment": "left",
    "start_button": {"style": "orb_win7", "label": "Start"},
    "superbar": {},
    "notification_area": {},
    "backdrop": "glass",
    "animations": "aero",
    "pinned": [],
    "running": [],
    "tray": {
        "network": "unknown",
        "sound": "normal",
        "battery": "unknown",
        "clock": None
    }
}


def load_profile():
    return json.loads(PROFILE_PATH.read_text(encoding='utf-8-sig'))


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def _emit(topic, payload, corr=None):
    publish(topic, payload, corr=corr, source='taskbar_host')
    save_state('taskbar_host', snapshot(), corr=corr)


def apply_profile(corr: str = None):
    profile = load_profile().get('taskbar', {})
    STATE['style'] = profile.get('style', 'windows7')
    STATE['alignment'] = profile.get('alignment', 'left')
    STATE['start_button'] = profile.get('startButton', {'style': 'orb_win7', 'label': 'Start'})
    STATE['superbar'] = profile.get('superbar', {})
    STATE['notification_area'] = profile.get('notificationArea', {})
    STATE['backdrop'] = profile.get('backdrop', 'glass')
    STATE['animations'] = profile.get('animations', 'aero')
    if corr is not None:
        _emit('shell.taskbar.profile.applied', {'style': STATE['style'], 'alignment': STATE['alignment']}, corr)
    return {'ok': True, 'code': 'TASKBAR_PROFILE_APPLIED', 'state': snapshot()}


def set_alignment(mode: str, corr: str = None):
    if mode not in ("center", "left"):
        return {"ok": False, "code": "TASKBAR_BAD_ALIGNMENT"}
    STATE["alignment"] = mode
    _emit('shell.taskbar.alignment.changed', {'alignment': mode}, corr)
    return {"ok": True, "code": "TASKBAR_ALIGNMENT_SET", "alignment": mode}


def pin_app(app_id: str, label: str, corr: str = None):
    if any(a["app_id"] == app_id for a in STATE["pinned"]):
        return {"ok": True, "code": "TASKBAR_PIN_EXISTS"}
    STATE["pinned"].append({"app_id": app_id, "label": label})
    _emit('shell.taskbar.pin', {'app_id': app_id, 'label': label}, corr)
    return {"ok": True, "code": "TASKBAR_PIN_OK"}


def unpin_app(app_id: str, corr: str = None):
    before = len(STATE["pinned"])
    STATE["pinned"] = [a for a in STATE["pinned"] if a["app_id"] != app_id]
    _emit('shell.taskbar.unpin', {'app_id': app_id}, corr)
    return {"ok": True, "code": "TASKBAR_UNPIN_OK" if len(STATE["pinned"]) < before else "TASKBAR_UNPIN_NOOP"}


def app_started(app_id: str, label: str, corr: str = None):
    if not any(a["app_id"] == app_id for a in STATE["running"]):
        STATE["running"].append({"app_id": app_id, "label": label, "corr": corr, "started_at": now_iso()})
    _emit('shell.taskbar.app.started', {'app_id': app_id, 'label': label}, corr)
    return {"ok": True, "code": "TASKBAR_RUN_ADD"}


def app_stopped(app_id: str, corr: str = None):
    before = len(STATE["running"])
    STATE["running"] = [a for a in STATE["running"] if a["app_id"] != app_id]
    _emit('shell.taskbar.app.stopped', {'app_id': app_id}, corr)
    return {"ok": True, "code": "TASKBAR_RUN_REMOVE" if len(STATE["running"]) < before else "TASKBAR_RUN_NOOP"}


def update_tray(network=None, sound=None, battery=None, corr: str = None):
    if network is not None:
        STATE["tray"]["network"] = network
    if sound is not None:
        STATE["tray"]["sound"] = sound
    if battery is not None:
        STATE["tray"]["battery"] = battery
    STATE["tray"]["clock"] = now_iso()
    _emit('shell.taskbar.tray.updated', STATE['tray'], corr)
    return {"ok": True, "code": "TASKBAR_TRAY_UPDATED"}


def snapshot():
    return json.loads(json.dumps(STATE))


if __name__ == '__main__':
    print(json.dumps(apply_profile(), indent=2))

