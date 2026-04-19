import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

try:
    import cv2
except Exception:  # pragma: no cover - optional dependency fallback
    cv2 = None


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


MEDIA_RUNTIME_ROOT = Path(axion_path_str("data", "apps", "media_runtime"))
MEDIA_RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
THUMBNAILS_ROOT = MEDIA_RUNTIME_ROOT / "thumbnails"
THUMBNAILS_ROOT.mkdir(parents=True, exist_ok=True)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resolve_ffmpeg() -> dict:
    env_path = str(os.getenv("AXION_FFMPEG_BIN", "")).strip()
    if env_path:
        candidate = Path(env_path)
        if candidate.exists():
            return {"available": True, "path": str(candidate), "source": "env"}

    binary = shutil.which("ffmpeg")
    if binary:
        return {"available": True, "path": str(binary), "source": "path"}

    try:
        import imageio_ffmpeg

        discovered = Path(str(imageio_ffmpeg.get_ffmpeg_exe()))
        if discovered.exists():
            return {"available": True, "path": str(discovered), "source": "imageio_ffmpeg"}
    except Exception:
        pass

    return {"available": False, "path": None, "source": "missing"}


def _run_ffmpeg(args: list[str]) -> tuple[bool, str]:
    ffmpeg = resolve_ffmpeg()
    if not ffmpeg.get("available"):
        return False, "FFMPEG_UNAVAILABLE"
    cmd = [str(ffmpeg["path"])] + list(args)
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode == 0:
        return True, "OK"
    return False, (proc.stderr or proc.stdout or "ffmpeg_failed")[:600]


def ensure_deterministic_image(path: str | Path, *, width: int = 256, height: int = 144) -> dict:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        x = np.tile(np.arange(width, dtype=np.uint16), (height, 1))
        y = np.tile(np.arange(height, dtype=np.uint16).reshape(height, 1), (1, width))
        r = ((x + 17) % 256).astype(np.uint8)
        g = ((y + 61) % 256).astype(np.uint8)
        b = (((x // 2) + (y // 2) + 123) % 256).astype(np.uint8)
        rgb = np.stack([r, g, b], axis=2)
        Image.fromarray(rgb, mode="RGB").save(target, format="PNG")
    return inspect_image(target)


def inspect_image(path: str | Path) -> dict:
    target = Path(path)
    if not target.exists():
        return {"ok": False, "code": "IMAGE_MISSING", "file": str(target)}

    with Image.open(target) as img:
        rgb = img.convert("RGB")
        width, height = rgb.size
        arr = np.array(rgb)

    channels = int(arr.shape[2]) if arr.ndim == 3 else 1
    edge_ratio = 0.0
    if cv2 is not None:
        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
        edges = cv2.Canny(gray, 80, 160)
        edge_ratio = float((edges > 0).sum()) / float(edges.size) if edges.size else 0.0

    return {
        "ok": True,
        "code": "IMAGE_INSPECT_OK",
        "file": str(target),
        "width": int(width),
        "height": int(height),
        "channels": int(channels),
        "mode": "RGB",
        "edge_ratio": round(float(edge_ratio), 6),
        "bytes": int(target.stat().st_size),
        "sha256": _sha256(target),
    }


def apply_filter_image(
    source_path: str | Path,
    dest_path: str | Path,
    *,
    filter_name: str,
    strength: float = 1.0,
) -> dict:
    source = Path(source_path)
    dest = Path(dest_path)
    if not source.exists():
        return {"ok": False, "code": "PHOTO_EDIT_SOURCE_MISSING", "file": str(source)}

    dest.parent.mkdir(parents=True, exist_ok=True)
    strength = float(strength if strength > 0 else 1.0)
    filter_name = str(filter_name or "").strip().lower() or "contrast"

    img = Image.open(source).convert("RGB")
    arr = np.array(img)

    if filter_name == "grayscale":
        if cv2 is None:
            gray = ImageEnhance.Color(img).enhance(0.0)
            out = gray.convert("RGB")
        else:
            gray_arr = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
            out = Image.fromarray(cv2.cvtColor(gray_arr, cv2.COLOR_GRAY2RGB), mode="RGB")
    elif filter_name == "blur":
        if cv2 is None:
            out = img.filter(ImageFilter.GaussianBlur(radius=max(1.0, 1.8 * strength)))
        else:
            kernel = max(1, int(round(strength * 3.0)))
            if kernel % 2 == 0:
                kernel += 1
            blurred = cv2.GaussianBlur(arr, (kernel, kernel), 0)
            out = Image.fromarray(blurred, mode="RGB")
    elif filter_name == "sharpen":
        out = img.filter(ImageFilter.UnsharpMask(radius=max(1.0, 1.2 * strength), percent=170, threshold=2))
    elif filter_name == "edge":
        if cv2 is None:
            out = img.filter(ImageFilter.FIND_EDGES)
        else:
            gray_arr = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
            edges = cv2.Canny(gray_arr, 90, 180)
            out = Image.fromarray(cv2.cvtColor(edges, cv2.COLOR_GRAY2RGB), mode="RGB")
    else:
        # Default to contrast.
        out = ImageEnhance.Contrast(img).enhance(max(0.1, 1.0 + (0.25 * strength)))
        filter_name = "contrast"

    out.save(dest, format="PNG")
    inspected = inspect_image(dest)
    return {
        "ok": bool(inspected.get("ok")),
        "code": "PHOTO_EDIT_OK" if bool(inspected.get("ok")) else str(inspected.get("code")),
        "filter": filter_name,
        "strength": round(float(strength), 4),
        "output": inspected,
    }


def inspect_video(path: str | Path) -> dict:
    target = Path(path)
    if not target.exists():
        return {"ok": False, "code": "VIDEO_MISSING", "file": str(target)}

    if cv2 is None:
        return {
            "ok": True,
            "code": "VIDEO_INSPECT_PARTIAL",
            "file": str(target),
            "bytes": int(target.stat().st_size),
            "sha256": _sha256(target),
            "fps": 0.0,
            "frame_count": 0,
            "width": 0,
            "height": 0,
            "duration_sec": 0.0,
        }

    cap = cv2.VideoCapture(str(target))
    if not cap.isOpened():
        return {"ok": False, "code": "VIDEO_OPEN_FAILED", "file": str(target)}

    fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
    frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    cap.release()

    duration = (float(frames) / fps) if fps > 0 else 0.0
    signature = hashlib.sha256(
        f"{target.stat().st_size}:{width}:{height}:{frames}:{round(fps, 4)}".encode("utf-8")
    ).hexdigest()
    return {
        "ok": True,
        "code": "VIDEO_INSPECT_OK",
        "file": str(target),
        "bytes": int(target.stat().st_size),
        "fps": round(fps, 4),
        "frame_count": int(frames),
        "width": int(width),
        "height": int(height),
        "duration_sec": round(duration, 4),
        "sha256": _sha256(target),
        "media_signature": signature[:24],
    }


def ensure_deterministic_video(
    path: str | Path,
    *,
    width: int = 320,
    height: int = 180,
    fps: int = 12,
    duration_sec: int = 2,
) -> dict:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    should_generate = True
    if target.exists():
        current = inspect_video(target)
        if bool(current.get("ok")) and int(current.get("frame_count", 0)) > 0:
            should_generate = False
        else:
            target.unlink(missing_ok=True)

    if should_generate:
        ok, detail = _run_ffmpeg(
            [
                "-y",
                "-f",
                "lavfi",
                "-i",
                f"testsrc2=size={width}x{height}:rate={fps}",
                "-t",
                str(int(duration_sec)),
                "-pix_fmt",
                "yuv420p",
                "-c:v",
                "mpeg4",
                "-q:v",
                "4",
                "-metadata",
                "creation_time=1970-01-01T00:00:00Z",
                str(target),
            ]
        )
        if not ok:
            return {
                "ok": False,
                "code": "VIDEO_SYNTHESIS_FAILED",
                "file": str(target),
                "reason": detail,
                "ffmpeg": resolve_ffmpeg(),
            }
    inspected = inspect_video(target)
    if not bool(inspected.get("ok")):
        return inspected
    return {"ok": True, "code": "VIDEO_SYNTHESIS_OK", "file": str(target), "video": inspected}


def extract_video_thumbnail(video_path: str | Path, thumb_path: str | Path, *, at_seconds: float = 0.3) -> dict:
    video = Path(video_path)
    thumb = Path(thumb_path)
    thumb.parent.mkdir(parents=True, exist_ok=True)
    if not video.exists():
        return {"ok": False, "code": "VIDEO_MISSING", "file": str(video)}

    ok, _ = _run_ffmpeg(
        [
            "-y",
            "-ss",
            str(float(at_seconds)),
            "-i",
            str(video),
            "-frames:v",
            "1",
            str(thumb),
        ]
    )
    if not ok and cv2 is not None:
        cap = cv2.VideoCapture(str(video))
        if cap.isOpened():
            frame_index = max(0, int((cap.get(cv2.CAP_PROP_FPS) or 1.0) * float(at_seconds)))
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
            read_ok, frame = cap.read()
            cap.release()
            if read_ok:
                cv2.imwrite(str(thumb), frame)

    if not thumb.exists():
        return {"ok": False, "code": "VIDEO_THUMBNAIL_FAILED", "file": str(thumb)}

    inspected = inspect_image(thumb)
    return {"ok": bool(inspected.get("ok")), "code": "VIDEO_THUMBNAIL_OK", "thumbnail": inspected}
