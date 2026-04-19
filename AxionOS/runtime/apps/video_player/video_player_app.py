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

from media_engine import (
    ensure_deterministic_video,
    extract_video_thumbnail,
    inspect_video,
    resolve_ffmpeg,
)

CODECS = Path(axion_path_str("config", "MEDIA_CODECS_V1.json"))
DEFAULT_MEDIA = Path(axion_path_str("data", "profiles", "p1", "Videos"))
DEFAULT_MEDIA.mkdir(parents=True, exist_ok=True)


def _load_codecs():
    return json.loads(CODECS.read_text(encoding="utf-8-sig"))


def open_media(path: str = None):
    codec_cfg = _load_codecs()
    media_path = Path(path) if path else DEFAULT_MEDIA / "sample_video.mp4"
    created = ensure_deterministic_video(media_path)
    if not bool(created.get("ok")):
        return {
            "ok": False,
            "code": str(created.get("code")),
            "file": str(media_path),
            "error": created,
            "ffmpeg": resolve_ffmpeg(),
        }

    inspected = inspect_video(media_path)
    thumbnail_path = media_path.parent / f"{media_path.stem}_thumb.png"
    thumb = extract_video_thumbnail(media_path, thumbnail_path)
    container = media_path.suffix.lstrip(".") or "mp4"
    supported = codec_cfg.get("containers", {}).get(container, {})
    return {
        "ok": bool(inspected.get("ok")),
        "code": "VIDEO_PLAYER_OPEN_OK" if bool(inspected.get("ok")) else str(inspected.get("code")),
        "file": str(media_path),
        "container": container,
        "supported_codecs": supported,
        "video": inspected,
        "thumbnail": thumb.get("thumbnail"),
        "media_signature": str((inspected or {}).get("media_signature", "")),
        "ffmpeg": resolve_ffmpeg(),
    }


def snapshot():
    cfg = _load_codecs()
    ffmpeg = resolve_ffmpeg()
    return {
        "app": "Video Player",
        "containers": sorted(cfg.get("containers", {}).keys()),
        "engine": "ffmpeg_opencv",
        "ffmpeg_available": bool(ffmpeg.get("available")),
        "ffmpeg_source": ffmpeg.get("source"),
    }


if __name__ == "__main__":
    print(json.dumps(open_media(), indent=2))
