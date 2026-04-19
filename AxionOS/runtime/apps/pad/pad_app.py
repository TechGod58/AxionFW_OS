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

ROOT = Path(axion_path_str('data', 'apps', 'pad'))
ROOT.mkdir(parents=True, exist_ok=True)


def _now():
    return datetime.now(timezone.utc).isoformat()


def _file(file_id: str):
    return ROOT / f"{file_id}.txt"


def create(file_id: str, content: str = ""):
    p = _file(file_id)
    p.write_text(content, encoding='utf-8')
    return {"ok": True, "code": "PAD_CREATE_OK", "file": str(p)}


def open_doc(file_id: str):
    p = _file(file_id)
    if not p.exists():
        return {"ok": False, "code": "PAD_OPEN_MISSING"}
    return {"ok": True, "code": "PAD_OPEN_OK", "file": str(p), "content": p.read_text(encoding='utf-8')}


def save(file_id: str, content: str):
    p = _file(file_id)
    p.write_text(content, encoding='utf-8')
    return {"ok": True, "code": "PAD_SAVE_OK", "file": str(p), "bytes": p.stat().st_size, "ts": _now()}


def snapshot():
    files = [f.name for f in ROOT.glob('*.txt')]
    return {"files": files, "count": len(files)}


if __name__ == '__main__':
    # demo pass
    create('demo_note', 'Axion Pad first pass')
    save('demo_note', 'Axion Pad first pass\nUpdated line.')
    print(json.dumps(snapshot(), indent=2))

