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
import sys
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(axion_path_str('runtime', 'shell_ui'))
for p in ['event_bus', 'settings_host', 'tray_host', 'privacy_security_host']:
    pp = str(BASE / p)
    if pp not in sys.path:
        sys.path.append(pp)

from event_bus import publish
import settings_host as settings
import tray_host as tray
import privacy_security_host as privacy_security

STATE_PATH = Path(axion_path_str('data', 'state', 'home_hub_state.json'))


def _now():
    return datetime.now(timezone.utc).isoformat()


def _save(state):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding='utf-8')


def _read_location_toggle(default: bool = False) -> bool:
    try:
        snap = privacy_security.snapshot(corr='corr_home_location_read_001')
    except Exception:
        return bool(default)
    privacy = dict(snap.get('privacy') or {})
    return bool(privacy.get('location', default))


def build_home(corr='corr_home_001'):
    s = settings.snapshot()
    t = tray.snapshot()
    location_toggle = _read_location_toggle(default=False)
    out = {
        'ts': _now(),
        'corr': corr,
        'health': {'cpu_pct': 8, 'mem_pct': 23, 'storage_pct': 41, 'security': 'good'},
        'quick_toggles': {
            'wifi': t['toggles']['wifi'],
            'bluetooth': t['toggles']['bluetooth'],
            'vpn': t['toggles']['vpn'],
            'location': location_toggle,
            'notifications': s['prefs']['notifications']
        },
        'recent_changes': s.get('recent_changes', [])[:5],
        'updates': {'channel': 'dev', 'status': 'up_to_date'}
    }
    _save(out)
    publish('shell.home.refreshed', {'ok': True}, corr=corr, source='home_host')
    return out


def quick_toggle(name: str, value: bool, corr='corr_home_toggle_001'):
    if name in ('wifi', 'bluetooth', 'vpn'):
        tray.set_toggle(name, value, corr=corr)
    elif name == 'notifications':
        settings.set_pref('notifications', value, corr=corr)
    elif name == 'location':
        out = privacy_security.set_privacy_toggle('location', bool(value), corr=f"{corr}_location")
        if not out.get('ok'):
            return {'ok': False, 'code': out.get('code', 'HOME_TOGGLE_LOCATION_FAIL'), 'name': name, 'value': bool(value)}
    publish('shell.home.toggle.changed', {'name': name, 'value': bool(value)}, corr=corr, source='home_host')
    return {'ok': True, 'code': 'HOME_TOGGLE_SET', 'name': name, 'value': bool(value)}


if __name__ == '__main__':
    print(json.dumps(build_home(), indent=2))

