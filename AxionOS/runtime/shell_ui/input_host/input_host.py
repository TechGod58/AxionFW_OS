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

BUS = Path(axion_path_str('runtime', 'shell_ui', 'event_bus'))
if str(BUS) not in sys.path:
    sys.path.append(str(BUS))

from event_bus import publish

STATE_PATH = Path(axion_path_str('config', 'KEYBOARD_LAYOUTS_STATE_V1.json'))


def _now():
    return datetime.now(timezone.utc).isoformat()


def _load():
    return json.loads(STATE_PATH.read_text(encoding='utf-8-sig'))


def _save(s):
    STATE_PATH.write_text(json.dumps(s, indent=2), encoding='utf-8')


def snapshot(corr='corr_input_snap_001'):
    s = _load()
    publish('shell.input.refreshed', {'ok': True}, corr=corr, source='input_host')
    return {'ts': _now(), 'corr': corr, **s}


def add_layout(layout: str, corr='corr_input_add_001'):
    s = _load()
    if layout not in s['layouts']:
        s['layouts'].append(layout)
        _save(s)
    publish('shell.input.layout.added', {'layout': layout}, corr=corr, source='input_host')
    return {'ok': True, 'code': 'INPUT_LAYOUT_ADD_OK', 'layout': layout}


def remove_layout(layout: str, corr='corr_input_remove_001'):
    s = _load()
    if layout == s['primary']:
        return {'ok': False, 'code': 'INPUT_LAYOUT_REMOVE_PRIMARY_DENY'}
    s['layouts'] = [x for x in s['layouts'] if x != layout]
    if s['active'] == layout:
        s['active'] = s['primary']
    _save(s)
    publish('shell.input.layout.removed', {'layout': layout}, corr=corr, source='input_host')
    return {'ok': True, 'code': 'INPUT_LAYOUT_REMOVE_OK', 'layout': layout}


def set_primary(layout: str, corr='corr_input_primary_001'):
    s = _load()
    if layout not in s['layouts']:
        s['layouts'].append(layout)
    s['primary'] = layout
    s['active'] = layout
    _save(s)
    publish('shell.input.layout.primary.changed', {'primary': layout}, corr=corr, source='input_host')
    return {'ok': True, 'code': 'INPUT_LAYOUT_PRIMARY_SET_OK', 'primary': layout}


def set_active(layout: str, corr='corr_input_active_001'):
    s = _load()
    if layout not in s['layouts']:
        return {'ok': False, 'code': 'INPUT_LAYOUT_UNKNOWN'}
    s['active'] = layout
    _save(s)
    publish('shell.input.layout.active.changed', {'active': layout}, corr=corr, source='input_host')
    return {'ok': True, 'code': 'INPUT_LAYOUT_ACTIVE_SET_OK', 'active': layout}


if __name__ == '__main__':
    print(json.dumps(snapshot(), indent=2))

