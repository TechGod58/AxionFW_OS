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
from pathlib import Path
STATE = Path(axion_path_str('data', 'apps', 'registry_editor', 'registry.json'))
STATE.parent.mkdir(parents=True, exist_ok=True)
if not STATE.exists():
    STATE.write_text(json.dumps({'HKCU': {}, 'HKLM': {}}), encoding='utf-8')

def snapshot():
    return json.loads(STATE.read_text(encoding='utf-8-sig'))

def set_value(hive: str, key: str, value):
    s = snapshot()
    s.setdefault(hive, {})[key] = value
    STATE.write_text(json.dumps(s, indent=2), encoding='utf-8')
    return {'ok': True, 'code': 'REGEDIT_SET_OK'}

if __name__ == '__main__':
    print(json.dumps(snapshot(), indent=2))

