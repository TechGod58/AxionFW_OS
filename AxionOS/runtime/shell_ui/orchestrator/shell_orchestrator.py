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
import sys
from pathlib import Path
import json
from datetime import datetime, timezone

BASE = Path(axion_path_str('runtime', 'shell_ui'))
for p in ['event_bus', 'taskbar_host', 'start_menu_host', 'tray_host', 'settings_host', 'desktop_host', 'action_contract']:
    pp = str(BASE / p)
    if pp not in sys.path:
        sys.path.append(pp)

from event_bus import subscribe, publish, snapshot_subscribers
import taskbar_host as taskbar
import settings_host as settings
import tray_host as tray
import start_menu_host as start
import desktop_host as desktop
from shell_action_contract import dispatch_ui_action

HOTKEY_CFG_PATH = Path(axion_path_str('config', 'shell_hotkeys.json'))
BOSS_STATE_PATH = Path(axion_path_str('out', 'runtime', 'boss_button_state.json'))
BOSS_AUDIT_PATH = Path(axion_path_str('out', 'runtime', 'boss_button_audit.jsonl'))


def _now_iso():
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def _chord_from_event(key: str, ctrl=False, alt=False, shift=False) -> str:
    parts = []
    if ctrl: parts.append('Ctrl')
    if alt: parts.append('Alt')
    if shift: parts.append('Shift')
    parts.append(str(key).upper())
    return '+'.join(parts)


def _normalize_chord(ch: str) -> str:
    if not isinstance(ch, str):
        return ''
    parts = [p.strip() for p in ch.split('+') if p.strip()]
    if not parts:
        return ''
    mods=[]
    key=parts[-1].upper()
    for p in parts[:-1]:
        q=p.lower()
        if q in ('ctrl','control'): mods.append('Ctrl')
        elif q=='alt': mods.append('Alt')
        elif q=='shift': mods.append('Shift')
    out=[]
    for m in ('Ctrl','Alt','Shift'):
        if m in mods: out.append(m)
    out.append(key)
    return '+'.join(out)


def _load_hotkeys():
    if not HOTKEY_CFG_PATH.exists():
        return [{'action_id':'boss_button','chord':'Ctrl+Z','enabled':True,'context':'global','suppress_in_input_focus':True}]
    obj = json.loads(HOTKEY_CFG_PATH.read_text(encoding='utf-8-sig'))
    # schema v2 style
    if isinstance(obj, dict) and isinstance(obj.get('hotkeys'), list):
        out=[]
        for h in obj.get('hotkeys', []):
            if not isinstance(h, dict):
                continue
            out.append({
                'action_id': h.get('action_id',''),
                'chord': _normalize_chord(h.get('chord','')),
                'enabled': bool(h.get('enabled', True)),
                'context': h.get('context','global'),
                'suppress_in_input_focus': bool(h.get('suppress_in_input_focus', True)),
            })
        return out
    # legacy style
    if isinstance(obj, dict) and 'boss_button' in obj and isinstance(obj['boss_button'], dict):
        bb=obj['boss_button']
        return [{'action_id':'boss_button','chord':_normalize_chord(bb.get('chord','Ctrl+Z')),'enabled':bool(bb.get('enabled',True)),'context':'global','suppress_in_input_focus':bool(bb.get('suppress_in_input_focus',True))}]
    return []


def _find_binding(action_id: str):
    for b in _load_hotkeys():
        if b.get('action_id') == action_id:
            return b
    return None


def _read_boss_state():
    if BOSS_STATE_PATH.exists():
        return json.loads(BOSS_STATE_PATH.read_text(encoding='utf-8-sig'))
    return {"boss_active": False, "safe_screen": "status_dashboard", "prior_view": None, "prior_state": None}


def _write_boss_state(state: dict):
    BOSS_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    BOSS_STATE_PATH.write_text(json.dumps(state, indent=2), encoding='utf-8')


def _audit_boss_toggle(from_state: str, to_state: str, focus_context: str, corr: str = None):
    evt = {"event": "BOSS_BUTTON_TOGGLED", "timestamp_utc": _now_iso(), "from_state": from_state, "to_state": to_state, "focus_context": focus_context, "corr": corr}
    BOSS_AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with BOSS_AUDIT_PATH.open('a', encoding='utf-8') as f: f.write(json.dumps(evt) + "\n")
    publish('shell.boss_button.toggled', evt, corr=corr, source='shell_orchestrator')


def bootstrap_subscriptions():
    subscribe('shell.settings.changed', 'shell_orchestrator')
    subscribe('shell.startmenu.opened', 'shell_orchestrator')
    subscribe('shell.notifications.push', 'shell_orchestrator')


def handle_settings_changed(payload: dict, corr: str = None):
    key = payload.get('key'); new = payload.get('new')
    if key == 'taskbar_alignment': taskbar.set_alignment(new, corr=corr)
    if key in ('wifi', 'bluetooth', 'vpn_quick_toggle'):
        map_key = 'vpn' if key == 'vpn_quick_toggle' else key
        tray.set_toggle(map_key, bool(new), corr=corr)
    if key in ('reduced_motion', 'high_contrast', 'theme', 'accent'):
        desktop.set_graphics('reducedMotion', bool(new) if key == 'reduced_motion' else desktop.snapshot()['graphics'].get('reducedMotion'))
    publish('shell.orchestrator.settings.applied', {'key': key, 'new': new}, corr=corr, source='shell_orchestrator')


def handle_startmenu_opened(payload: dict, corr: str = None):
    taskbar.app_started('axion-launch', 'Axion Launch', corr=corr)
    publish('shell.orchestrator.startmenu.synced', payload, corr=corr, source='shell_orchestrator')


def handle_notification_push(payload: dict, corr: str = None):
    publish('shell.orchestrator.notification.synced', payload, corr=corr, source='shell_orchestrator')


def dispatch_shell_action(host: str, action: str, payload: dict | None = None, corr: str = None):
    payload = payload or {}
    result = dispatch_ui_action(
        host=host,
        action=action,
        item=payload.get('item'),
        args=payload.get('args', {}),
        corr=corr,
    )
    out = {
        'ok': bool(result.get('ok')),
        'code': 'ORCH_ACTION_DISPATCHED' if bool(result.get('ok')) else str(result.get('code')),
        'host': result.get('host', host),
        'action': action,
        'result': result,
    }
    topic = 'shell.orchestrator.action.dispatched' if out['ok'] else 'shell.orchestrator.action.failed'
    publish(topic, out, corr=corr, source='shell_orchestrator')
    return out


def toggle_boss_button(current_view: str, focus_context: str = 'non-input', ui_state: dict = None, corr: str = None):
    cfg = _find_binding('boss_button') or {'suppress_in_input_focus':True}
    if cfg.get('suppress_in_input_focus', True) and focus_context == 'input':
        return {'ok': True, 'code': 'BOSS_BUTTON_SUPPRESSED_INPUT_FOCUS', 'suppressed': True, 'view': current_view}
    st = _read_boss_state(); safe_screen = st.get('safe_screen', 'status_dashboard')
    if not st.get('boss_active', False):
        st['boss_active'] = True; st['prior_view'] = current_view; st['prior_state'] = ui_state or {}
        _write_boss_state(st); _audit_boss_toggle('normal', 'safe_screen', focus_context, corr=corr)
        return {'ok': True, 'code': 'BOSS_BUTTON_ON', 'view': safe_screen, 'restorable': True}
    restored = st.get('prior_view') or 'home'
    st['boss_active']=False; st['prior_view']=None; st['prior_state']=None
    _write_boss_state(st); _audit_boss_toggle('safe_screen','normal',focus_context,corr=corr)
    return {'ok': True, 'code': 'BOSS_BUTTON_OFF', 'view': restored, 'restored': True}


def handle_hotkey(key: str, ctrl=False, alt=False, shift=False, focus_context='non-input', current_view='home', ui_state=None, corr=None):
    chord = _normalize_chord(_chord_from_event(key, ctrl=ctrl, alt=alt, shift=shift))
    b=_find_binding('boss_button')
    if b and b.get('enabled',True) and chord == _normalize_chord(b.get('chord','')):
        return toggle_boss_button(current_view=current_view, focus_context=focus_context, ui_state=ui_state or {}, corr=corr)
    return {'ok': False, 'code': 'HOTKEY_UNMAPPED', 'chord': chord}


def run_demo(corr='corr_shell_orch_001'):
    bootstrap_subscriptions(); desktop.apply_defaults(); settings.set_pref('taskbar_alignment', 'left', corr=corr)
    handle_settings_changed({'key': 'taskbar_alignment', 'new': 'left'}, corr=corr)
    start.open_menu(corr=corr); handle_startmenu_opened({'open': True}, corr=corr)
    tray.push_notification('Axion', 'Orchestrator bridge online', corr=corr); handle_notification_push({'title': 'Axion'}, corr=corr)
    return {'corr': corr, 'subs': snapshot_subscribers(), 'taskbar': taskbar.snapshot(), 'start': start.snapshot(), 'tray': tray.snapshot(), 'settings': settings.snapshot(), 'desktop': desktop.snapshot()}

if __name__ == '__main__':
    print(json.dumps(run_demo(), indent=2))

