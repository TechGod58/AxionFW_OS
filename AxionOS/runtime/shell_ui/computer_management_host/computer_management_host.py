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

STATE_PATH = Path(axion_path_str('config', 'COMPUTER_MANAGEMENT_STATE_V1.json'))


def _now():
    return datetime.now(timezone.utc).isoformat()


def _load():
    return json.loads(STATE_PATH.read_text(encoding='utf-8-sig'))


def snapshot(corr='corr_cm_001'):
    s = _load()
    out = {'ts': _now(), 'corr': corr, **s}
    publish('shell.computer_management.refreshed', {'ok': True}, corr=corr, source='computer_management_host')
    return out


def open_node(node_id: str, corr='corr_cm_open_001'):
    s = _load()
    for group in s.get('leftNav', []):
        for item in group.get('items', []):
            if item.get('id') == node_id:
                publish('shell.computer_management.node.opened', {'node_id': node_id, 'target': item.get('target')}, corr=corr, source='computer_management_host')
                return {'ok': True, 'code': 'COMPUTER_MANAGEMENT_NODE_OPEN_OK', 'group': group.get('group'), **item}
    return {'ok': False, 'code': 'COMPUTER_MANAGEMENT_NODE_UNKNOWN'}


if __name__ == '__main__':
    print(json.dumps(snapshot(), indent=2))

