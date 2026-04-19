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


def append_allocation(record, path=axion_path_str('data', 'audit', 'allocator.ndjson')):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    if 'ts' not in record:
        record['ts'] = datetime.now(timezone.utc).isoformat()
    with p.open('a', encoding='utf-8') as f:
        f.write(json.dumps(record) + '\n')

