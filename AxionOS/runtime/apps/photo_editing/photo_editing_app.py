import json
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


SHARED = Path(axion_path_str("runtime", "apps", "_shared"))
if str(SHARED) not in sys.path:
    sys.path.append(str(SHARED))

from media_engine import apply_filter_image, ensure_deterministic_image

ROOT = Path(axion_path_str("data", "apps", "photo_editing"))
ROOT.mkdir(parents=True, exist_ok=True)
PROFILE_PHOTOS = Path(axion_path_str("data", "profiles", "p1", "Photos"))
PROFILE_PHOTOS.mkdir(parents=True, exist_ok=True)


def apply_filter(file_id: str, filter_name: str, source_path: str = None, strength: float = 1.0):
    base_id = str(file_id or "demo").strip() or "demo"
    source = Path(source_path) if source_path else (PROFILE_PHOTOS / f"{base_id}.png")
    ensure_deterministic_image(source)
    out_path = ROOT / f"{base_id}_{str(filter_name or 'contrast').strip().lower() or 'contrast'}.png"
    edited = apply_filter_image(source, out_path, filter_name=filter_name, strength=float(strength))
    return {
        "ok": bool(edited.get("ok")),
        "code": "PHOTO_EDIT_OK" if bool(edited.get("ok")) else str(edited.get("code")),
        "file": str(out_path),
        "source": str(source),
        "filter": str(filter_name),
        "strength": float(strength),
        "output": edited.get("output"),
    }


def snapshot():
    outputs = sorted(ROOT.glob("*.png"))
    return {
        "app": "Photo Editing",
        "engine": "pillow_opencv",
        "count": len(outputs),
        "outputs": [str(path) for path in outputs[-8:]],
    }


if __name__ == "__main__":
    print(json.dumps(apply_filter("demo", "contrast"), indent=2))
