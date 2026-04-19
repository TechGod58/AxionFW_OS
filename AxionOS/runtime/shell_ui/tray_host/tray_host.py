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
APP_RUNTIME_PATH = Path(axion_path_str('config', 'APP_RUNTIME_BEHAVIOR_V1.json'))
if str(EVENT_BUS_DIR) not in sys.path:
    sys.path.append(str(EVENT_BUS_DIR))

from event_bus import publish
from state_bridge import save_state

STATE = {
    "quick_settings_open": False,
    "notifications_open": False,
    "network": {"state": "unknown", "profile": None},
    "sound": {"level": 50, "muted": False},
    "battery": {"percent": None, "charging": None},
    "clock": {"iso": None},
    "toggles": {"wifi": True, "bluetooth": False, "airplane_mode": False, "night_light": False, "vpn": False},
    "running_apps": [],
    "app_runtime_policy": {
        "terminate_on_close": True,
        "keep_running_in_background_after_close": False,
        "show_running_apps_after_system_indicators": True
    },
    "notifications": []
}


def load_runtime_policy():
    return json.loads(APP_RUNTIME_PATH.read_text(encoding='utf-8-sig'))


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def _emit(topic, payload, corr=None):
    publish(topic, payload, corr=corr, source='tray_host')
    save_state('tray_host', snapshot(), corr=corr)


def apply_runtime_policy():
    policy = load_runtime_policy()
    STATE['app_runtime_policy'] = {
        'terminate_on_close': policy.get('close_behavior', {}).get('terminate_on_close', True),
        'keep_running_in_background_after_close': policy.get('close_behavior', {}).get('keep_running_in_background_after_close', False),
        'show_running_apps_after_system_indicators': policy.get('tray_behavior', {}).get('show_running_apps_after_system_indicators', True)
    }
    return {'ok': True, 'code': 'TRAY_RUNTIME_POLICY_APPLIED'}


def open_quick_settings(corr: str = None):
    STATE["quick_settings_open"] = True
    _emit('shell.tray.quicksettings.opened', {'open': True}, corr)
    return {"ok": True, "code": "TRAY_QS_OPEN_OK"}


def close_quick_settings(corr: str = None):
    STATE["quick_settings_open"] = False
    _emit('shell.tray.quicksettings.closed', {'open': False}, corr)
    return {"ok": True, "code": "TRAY_QS_CLOSE_OK"}


def open_notifications(corr: str = None):
    STATE["notifications_open"] = True
    _emit('shell.tray.notifications.opened', {'open': True}, corr)
    return {"ok": True, "code": "TRAY_NOTIF_OPEN_OK"}


def close_notifications(corr: str = None):
    STATE["notifications_open"] = False
    _emit('shell.tray.notifications.closed', {'open': False}, corr)
    return {"ok": True, "code": "TRAY_NOTIF_CLOSE_OK"}


def set_toggle(name: str, value: bool, corr: str = None):
    if name not in STATE["toggles"]:
        return {"ok": False, "code": "TRAY_TOGGLE_UNKNOWN"}
    STATE["toggles"][name] = bool(value)
    _emit('shell.tray.toggle.changed', {'toggle': name, 'value': bool(value)}, corr)
    return {"ok": True, "code": "TRAY_TOGGLE_SET", "toggle": name, "value": bool(value)}


def update_network(state: str, profile: str = None, corr: str = None):
    STATE["network"]["state"] = state
    STATE["network"]["profile"] = profile
    tick_clock()
    _emit('shell.tray.network.updated', STATE['network'], corr)
    return {"ok": True, "code": "TRAY_NETWORK_UPDATED"}


def update_sound(level: int = None, muted: bool = None, corr: str = None):
    if level is not None:
        STATE["sound"]["level"] = max(0, min(100, int(level)))
    if muted is not None:
        STATE["sound"]["muted"] = bool(muted)
    tick_clock()
    _emit('shell.tray.sound.updated', STATE['sound'], corr)
    return {"ok": True, "code": "TRAY_SOUND_UPDATED"}


def update_battery(percent: int = None, charging: bool = None, corr: str = None):
    if percent is not None:
        STATE["battery"]["percent"] = max(0, min(100, int(percent)))
    if charging is not None:
        STATE["battery"]["charging"] = bool(charging)
    tick_clock()
    _emit('shell.tray.battery.updated', STATE['battery'], corr)
    return {"ok": True, "code": "TRAY_BATTERY_UPDATED"}


def sync_running_apps(apps, corr: str = None):
    STATE['running_apps'] = list(apps or [])
    _emit('shell.tray.running_apps.synced', {'count': len(STATE['running_apps'])}, corr)
    return {'ok': True, 'code': 'TRAY_RUNNING_APPS_SYNCED', 'count': len(STATE['running_apps'])}


def tick_clock():
    STATE["clock"]["iso"] = now_iso()


def push_notification(title: str, body: str, level: str = "info", corr: str = None):
    STATE["notifications"].insert(0, {"title": title, "body": body, "level": level, "corr": corr, "ts": now_iso()})
    STATE["notifications"] = STATE["notifications"][:200]
    _emit('shell.notifications.push', {'title': title, 'level': level}, corr)
    return {"ok": True, "code": "TRAY_NOTIFICATION_PUSHED"}


def clear_notifications(corr: str = None):
    STATE["notifications"] = []
    _emit('shell.notifications.cleared', {}, corr)
    return {"ok": True, "code": "TRAY_NOTIFICATIONS_CLEARED"}


def snapshot():
    tick_clock()
    return json.loads(json.dumps(STATE))


if __name__ == '__main__':
    apply_runtime_policy()
    print(json.dumps(snapshot(), indent=2))

