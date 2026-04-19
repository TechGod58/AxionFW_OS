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
ACTION_CONTRACT_DIR = Path(axion_path_str('runtime', 'shell_ui', 'action_contract'))
PROFILE_PATH = Path(axion_path_str('config', 'SHELL_UI_PROFILE_V1.json'))
FOLDERS_PATH = Path(axion_path_str('config', 'PROFILE_SHELL_FOLDERS_V1.json'))
if str(EVENT_BUS_DIR) not in sys.path:
    sys.path.append(str(EVENT_BUS_DIR))
if str(ACTION_CONTRACT_DIR) not in sys.path:
    sys.path.append(str(ACTION_CONTRACT_DIR))

from event_bus import publish
from state_bridge import save_state
from shell_action_contract import dispatch_ui_action

STATE = {
    "style": "windows7_classic",
    "is_open": False,
    "query": "",
    "search_box_position": "bottom",
    "pinned": [],
    "recent_programs": [],
    "right_column_links": [],
    "quick_actions": [],
    "power_actions": ["sleep", "restart", "shutdown"],
    "default_power_action": "shutdown",
    "last_opened_at": None
}


def load_profile():
    return json.loads(PROFILE_PATH.read_text(encoding='utf-8-sig'))


def load_folders():
    return json.loads(FOLDERS_PATH.read_text(encoding='utf-8-sig'))


def _folder_aliases(meta: dict):
    aliases = [
        str(meta.get('displayName') or ''),
        str(meta.get('pathSegment') or ''),
        str(meta.get('legacyAlias') or ''),
        str(meta.get('windowsBehavior') or ''),
    ]
    for field in ('aliases', 'displayAliases', 'pathSegmentAliases'):
        values = meta.get(field)
        if isinstance(values, list):
            aliases.extend(str(x) for x in values)
    return [x.strip().lower() for x in aliases if str(x).strip()]


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def _emit(topic, payload, corr=None):
    publish(topic, payload, corr=corr, source='start_menu_host')
    save_state('start_menu_host', snapshot(), corr=corr)


def apply_profile(corr: str = None):
    profile = load_profile().get('startMenu', {})
    folders = load_folders()
    folder_map = {}
    for meta in folders.get('folders', {}).values():
        if not isinstance(meta, dict):
            continue
        for alias in _folder_aliases(meta):
            folder_map[alias] = meta
    STATE['style'] = profile.get('style', 'windows7_classic')
    STATE['search_box_position'] = profile.get('searchBoxPosition', 'bottom')
    STATE['default_power_action'] = profile.get('defaultPowerAction', 'shutdown')
    STATE['right_column_links'] = [
        folder_map.get(str(name).strip().lower(), {'displayName': name})
        for name in profile.get('rightColumnLinks', [])
    ]
    STATE['quick_actions'] = []
    for qa in profile.get('quickActions', []):
        if not isinstance(qa, dict):
            continue
        STATE['quick_actions'].append({
            'id': str(qa.get('id', '')),
            'label': str(qa.get('label', qa.get('id', 'Quick Action'))),
            'host': str(qa.get('host', 'control_panel')),
            'item': str(qa.get('item', '')),
            'action': str(qa.get('action', '')),
            'defaults': qa.get('defaults', {}) if isinstance(qa.get('defaults', {}), dict) else {}
        })
    if corr is not None:
        _emit('shell.startmenu.profile.applied', {'style': STATE['style']}, corr)
    return {"ok": True, "code": "STARTMENU_PROFILE_APPLIED", "state": snapshot()}


def open_menu(corr: str = None):
    STATE["is_open"] = True
    STATE["last_opened_at"] = now_iso()
    _emit('shell.startmenu.opened', {'open': True}, corr)
    return {"ok": True, "code": "STARTMENU_OPEN_OK"}


def close_menu(corr: str = None):
    STATE["is_open"] = False
    _emit('shell.startmenu.closed', {'open': False}, corr)
    return {"ok": True, "code": "STARTMENU_CLOSE_OK"}


def set_query(text: str, corr: str = None):
    STATE["query"] = text or ""
    _emit('shell.startmenu.query', {'query': STATE['query']}, corr)
    return {"ok": True, "code": "STARTMENU_QUERY_SET", "query": STATE["query"]}


def pin_app(app_id: str, label: str, corr: str = None):
    if any(a["app_id"] == app_id for a in STATE["pinned"]):
        return {"ok": True, "code": "STARTMENU_PIN_EXISTS"}
    STATE["pinned"].append({"app_id": app_id, "label": label})
    _emit('shell.startmenu.pin', {'app_id': app_id, 'label': label}, corr)
    return {"ok": True, "code": "STARTMENU_PIN_OK"}


def unpin_app(app_id: str, corr: str = None):
    before = len(STATE["pinned"])
    STATE["pinned"] = [a for a in STATE["pinned"] if a["app_id"] != app_id]
    _emit('shell.startmenu.unpin', {'app_id': app_id}, corr)
    return {"ok": True, "code": "STARTMENU_UNPIN_OK" if len(STATE["pinned"]) < before else "STARTMENU_UNPIN_NOOP"}


def add_recent_program(app_id: str, label: str, reason: str = "recent", corr: str = None):
    item = {"app_id": app_id, "label": label, "reason": reason, "ts": now_iso()}
    STATE["recent_programs"] = [r for r in STATE["recent_programs"] if r["app_id"] != app_id]
    STATE["recent_programs"].insert(0, item)
    STATE["recent_programs"] = STATE["recent_programs"][:12]
    _emit('shell.startmenu.recent_program', item, corr)
    return {"ok": True, "code": "STARTMENU_RECENT_PROGRAM_ADD"}


def invoke_power(action: str, corr: str = None):
    if action not in STATE["power_actions"]:
        return {"ok": False, "code": "STARTMENU_POWER_BAD_ACTION"}
    _emit('shell.startmenu.power.requested', {'action': action}, corr)
    return {"ok": True, "code": "STARTMENU_POWER_REQUESTED", "action": action}


def invoke_quick_action(action_id: str, args: dict | None = None, corr: str = None):
    action_id = str(action_id or "").strip()
    selected = next((x for x in STATE.get('quick_actions', []) if x.get('id') == action_id), None)
    if not selected:
        return {"ok": False, "code": "STARTMENU_QUICK_ACTION_UNKNOWN", "action_id": action_id}
    merged_args = {}
    merged_args.update(selected.get('defaults', {}))
    if isinstance(args, dict):
        merged_args.update(args)
    dispatch = dispatch_ui_action(
        host=selected.get('host'),
        action=selected.get('action'),
        item=selected.get('item'),
        args=merged_args,
        corr=corr,
    )
    out = {
        "ok": bool(dispatch.get('ok')),
        "code": "STARTMENU_QUICK_ACTION_OK" if bool(dispatch.get('ok')) else "STARTMENU_QUICK_ACTION_FAIL",
        "action_id": action_id,
        "dispatch": dispatch,
    }
    _emit('shell.startmenu.quick_action.invoked', out, corr)
    return out


def snapshot():
    return json.loads(json.dumps(STATE))


if __name__ == '__main__':
    print(json.dumps(apply_profile(), indent=2))

