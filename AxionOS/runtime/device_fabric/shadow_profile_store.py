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

SHADOW = Path(axion_path_str('data', 'device_shadow', 'profiles.json'))


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def _load():
    if SHADOW.exists():
        return json.loads(SHADOW.read_text(encoding='utf-8-sig'))
    return {"profiles": {}}


def save_profile(device_id: str, profile: dict):
    data = _load()
    data['profiles'][device_id] = {"profile": profile, "ts": now_iso()}
    SHADOW.parent.mkdir(parents=True, exist_ok=True)
    SHADOW.write_text(json.dumps(data, indent=2), encoding='utf-8')
    return {"ok": True, "code": "DRV_SHADOW_SAVE_OK"}


def load_profile(device_id: str):
    data = _load()
    if device_id in data['profiles']:
        return {"ok": True, "code": "DRV_SHADOW_RESTORE_OK", "data": data['profiles'][device_id]}
    return {"ok": False, "code": "DRV_SHADOW_RESTORE_STALE"}

