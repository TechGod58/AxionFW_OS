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
from pathlib import Path

ROOT = Path(axion_path_str('data', 'profiles', 'p1', 'Photos'))
ROOT.mkdir(parents=True, exist_ok=True)


def capture_photo(name: str = None):
    ts = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    p = ROOT / (name or f'photo_{ts}.json')
    p.write_text(json.dumps({'captured_at': ts, 'kind': 'photo', 'saved_to': 'Photos'}), encoding='utf-8')
    return {'ok': True, 'code': 'CAMERA_CAPTURE_OK', 'file': str(p), 'target_folder': 'Photos'}


def snapshot():
    return {'app': 'Camera', 'count': len(list(ROOT.glob('*.json'))), 'target_folder': 'Photos'}


if __name__ == '__main__':
    capture_photo()
    print(json.dumps(snapshot(), indent=2))

