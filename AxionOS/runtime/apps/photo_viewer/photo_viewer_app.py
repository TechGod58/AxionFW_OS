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

from media_engine import ensure_deterministic_image, inspect_image

PROFILE_PHOTOS = Path(axion_path_str("data", "profiles", "p1", "Photos"))
PROFILE_PHOTOS.mkdir(parents=True, exist_ok=True)


def _resolve_photo_path(name: str | None):
    filename = str(name or "sample_photo.png").strip() or "sample_photo.png"
    return PROFILE_PHOTOS / filename


def open_photo(name: str = "sample_photo.png"):
    path = _resolve_photo_path(name)
    created = ensure_deterministic_image(path)
    if not bool(created.get("ok")):
        return {"ok": False, "code": str(created.get("code")), "photo": str(name), "file": str(path)}
    inspected = inspect_image(path)
    return {
        "ok": bool(inspected.get("ok")),
        "code": "PHOTO_VIEW_OK" if bool(inspected.get("ok")) else str(inspected.get("code")),
        "photo": str(name),
        "file": str(path),
        "image": inspected,
        "engine": "pillow_opencv",
    }


def snapshot():
    sample = _resolve_photo_path("sample_photo.png")
    ensure_deterministic_image(sample)
    return {
        "app": "Photo Viewer",
        "engine": "pillow_opencv",
        "sample_photo": str(sample),
    }


if __name__ == "__main__":
    print(json.dumps(open_photo("sample_photo.png"), indent=2))
