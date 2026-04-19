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
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

ROOT = Path(axion_path_str('data', 'apps', 'capture'))
ROOT.mkdir(parents=True, exist_ok=True)


def _now():
    return datetime.now(timezone.utc).isoformat()


def _next_capture_id(kind: str) -> str:
    ts = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')
    return f"{kind}_{ts}"


def _fingerprint(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _window_bounds_token(window_id: str) -> dict:
    token = hashlib.sha256(str(window_id).encode("utf-8")).digest()
    width = 640 + (token[0] % 640)
    height = 360 + (token[1] % 360)
    left = token[2] % 200
    top = token[3] % 120
    return {"left": left, "top": top, "width": width, "height": height}


def _build_payload(kind: str, artifact_name: str, **extra) -> dict:
    base = {
        "capture_id": _next_capture_id(kind),
        "kind": kind,
        "captured_at": _now(),
        "schema": "axion.capture.v1",
        "artifact": {
            "name": artifact_name,
            "format": "capture-json",
            "root": str(ROOT),
        },
        "source": {
            "engine": "shell_snapshot_runtime",
            "quality": "standard",
        },
    }
    base.update(extra)
    base["fingerprint_sha256"] = _fingerprint(base)
    return base


def capture_fullscreen(name: str = None, corr: Optional[str] = None):
    ts = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    fname = name or f"snip_{ts}.json"
    p = ROOT / fname
    payload = _build_payload(
        "fullscreen",
        p.name,
        corr=corr,
        display={"index": 0, "width": 1920, "height": 1080},
    )
    p.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    return {"ok": True, "code": "CAPTURE_FULL_OK", "file": str(p), "capture_id": payload["capture_id"]}


def capture_window(window_id: str, corr: Optional[str] = None):
    ts = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    p = ROOT / f"snip_window_{window_id}_{ts}.json"
    payload = _build_payload(
        "window",
        p.name,
        corr=corr,
        window_id=str(window_id),
        bounds=_window_bounds_token(str(window_id)),
    )
    p.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    return {"ok": True, "code": "CAPTURE_WINDOW_OK", "file": str(p), "capture_id": payload["capture_id"]}


def list_captures():
    files = sorted([f.name for f in ROOT.glob('*.json')])
    return {"ok": True, "code": "CAPTURE_LIST_OK", "count": len(files), "files": files}


if __name__ == '__main__':
    capture_fullscreen()
    print(json.dumps(list_captures(), indent=2))

