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
from datetime import datetime, timezone

PROMOTED = Path(axion_path_str('data', 'drivers', 'promoted.json'))


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def _load():
    if PROMOTED.exists():
        return json.loads(PROMOTED.read_text(encoding='utf-8-sig'))
    return {"drivers": []}


def promote(device: dict, driver: dict):
    data = _load()
    entry = {
        "device": device,
        "driver_id": driver.get('driver_id'),
        "driver_version": driver.get('version'),
        "ts": now_iso()
    }
    data['drivers'].append(entry)
    PROMOTED.parent.mkdir(parents=True, exist_ok=True)
    PROMOTED.write_text(json.dumps(data, indent=2), encoding='utf-8')
    return {"ok": True, "code": "DRV_OK", "entry": entry}

