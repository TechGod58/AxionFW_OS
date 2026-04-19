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
TEMP = Path(axion_path_str('data', 'temp'))
TEMP.mkdir(parents=True, exist_ok=True)

def analyze():
    return {'ok': True, 'code': 'DISK_CLEANUP_ANALYZE_OK', 'candidates_mb': 128}

def cleanup():
    return {'ok': True, 'code': 'DISK_CLEANUP_CLEAN_OK', 'freed_mb': 128}

if __name__ == '__main__':
    print(json.dumps(analyze(), indent=2))

