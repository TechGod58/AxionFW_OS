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

STATE_PATH = Path(axion_path_str('config', 'ADVANCED_SYSTEM_STATE_V1.json'))


def _now():
    return datetime.now(timezone.utc).isoformat()


def _load():
    return json.loads(STATE_PATH.read_text(encoding='utf-8-sig'))


def snapshot(corr='corr_adv_001'):
    s = _load()
    out = {'ts': _now(), 'corr': corr, **s}
    publish('shell.advanced_system.refreshed', {'ok': True}, corr=corr, source='advanced_system_host')
    return out


def open_tab(tab_id: str, corr='corr_adv_open_001'):
    s = _load()
    for tab in s.get('tabs', []):
        if tab.get('id') == tab_id:
            publish('shell.advanced_system.tab.opened', {'tab_id': tab_id}, corr=corr, source='advanced_system_host')
            return {'ok': True, 'code': 'ADVANCED_SYSTEM_TAB_OPEN_OK', **tab}
    return {'ok': False, 'code': 'ADVANCED_SYSTEM_TAB_UNKNOWN'}


if __name__ == '__main__':
    print(json.dumps(snapshot(), indent=2))

