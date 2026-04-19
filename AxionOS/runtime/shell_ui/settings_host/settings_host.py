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
if str(EVENT_BUS_DIR) not in sys.path:
    sys.path.append(str(EVENT_BUS_DIR))

from event_bus import publish
from state_bridge import save_state

STATE = {
    "active_category": "System",
    "search_query": "",
    "breadcrumbs": ["Settings", "System"],
    "categories": [
        "System", "Bluetooth & Devices", "Network & Internet", "Personalization", "Apps", "Accounts",
        "Time & Language", "Gaming/Media", "Accessibility", "Privacy & Security", "Update & Recovery", "Services"
    ],
    "prefs": {
        "theme": "dark", "accent": "axion_blue", "taskbar_alignment": "center", "reduced_motion": False,
        "high_contrast": False, "notifications": True, "wifi": True, "bluetooth": False, "vpn_quick_toggle": True, "visual_effects": False
    },
    "recent_changes": []
}


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def _emit(topic, payload, corr=None):
    publish(topic, payload, corr=corr, source='settings_host')
    save_state('settings_host', snapshot(), corr=corr)


def _record_change(key, old, new, corr=None):
    STATE["recent_changes"].insert(0, {"key": key, "old": old, "new": new, "corr": corr, "ts": now_iso()})
    STATE["recent_changes"] = STATE["recent_changes"][:200]


def open_category(name: str, corr: str = None):
    if name not in STATE["categories"]:
        return {"ok": False, "code": "SETTINGS_BAD_CATEGORY"}
    STATE["active_category"] = name
    STATE["breadcrumbs"] = ["Settings", name]
    _emit('shell.settings.category.opened', {'category': name}, corr)
    return {"ok": True, "code": "SETTINGS_CATEGORY_OPEN", "category": name}


def set_search(query: str, corr: str = None):
    STATE["search_query"] = query or ""
    _emit('shell.settings.search', {'query': STATE['search_query']}, corr)
    return {"ok": True, "code": "SETTINGS_SEARCH_SET", "query": STATE["search_query"]}


def set_pref(key: str, value, corr: str = None):
    if key not in STATE["prefs"]:
        return {"ok": False, "code": "SETTINGS_PREF_UNKNOWN"}
    if key == "taskbar_alignment" and value not in ("center", "left"):
        return {"ok": False, "code": "SETTINGS_PREF_INVALID"}
    if key in ("reduced_motion", "high_contrast", "notifications", "wifi", "bluetooth", "vpn_quick_toggle"):
        value = bool(value)

    old = STATE["prefs"][key]
    STATE["prefs"][key] = value
    _record_change(key, old, value, corr)
    _emit('shell.settings.changed', {'key': key, 'old': old, 'new': value}, corr)
    return {"ok": True, "code": "SETTINGS_PREF_SET", "key": key, "value": value}


def get_pref(key: str):
    if key not in STATE["prefs"]:
        return {"ok": False, "code": "SETTINGS_PREF_UNKNOWN"}
    return {"ok": True, "code": "SETTINGS_PREF_GET", "key": key, "value": STATE["prefs"][key]}


def snapshot():
    return json.loads(json.dumps(STATE))


if __name__ == '__main__':
    print(json.dumps(snapshot(), indent=2))



