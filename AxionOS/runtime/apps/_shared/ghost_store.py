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

POLICY = Path(axion_path_str('config', 'ELEVATION_AND_GHOST_POLICY_V1.json'))
ROOT = Path(axion_path_str('data', 'ghost'))


def _now():
    return datetime.now(timezone.utc).isoformat()


def _load_policy():
    return json.loads(POLICY.read_text(encoding='utf-8-sig'))


def _retention(app_class: str):
    p = _load_policy()
    return p["ghostRollback"]["retentionByClass"].get(app_class, p["ghostRollback"]["defaultRetention"])


def save_snapshot(app: str, app_class: str, file_id: str, payload: dict):
    d = ROOT / app / file_id
    d.mkdir(parents=True, exist_ok=True)
    ts = _now().replace(':', '-').replace('.', '-')
    snap = d / f"{ts}.json"
    snap.write_text(json.dumps({"ts": _now(), "payload": payload}, indent=2), encoding='utf-8')

    keep = _retention(app_class)
    snaps = sorted(d.glob('*.json'))
    while len(snaps) > keep:
      snaps[0].unlink(missing_ok=True)
      snaps = sorted(d.glob('*.json'))

    return {"ok": True, "code": "GHOST_SAVE_OK", "kept": len(snaps), "retention": keep}


def list_snapshots(app: str, file_id: str):
    d = ROOT / app / file_id
    if not d.exists():
        return []
    return [p.name for p in sorted(d.glob('*.json'))]

