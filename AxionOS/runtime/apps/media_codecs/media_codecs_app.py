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

STATE = Path(axion_path_str('config', 'MEDIA_CODECS_V1.json'))


def snapshot():
    return json.loads(STATE.read_text(encoding='utf-8-sig'))


if __name__ == '__main__':
    print(json.dumps(snapshot(), indent=2))

