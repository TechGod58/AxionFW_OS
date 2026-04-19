import json
import os
from pathlib import Path

DEFAULT_SCAN_MAX_BYTES = 64 * 1024 * 1024


def _scan_max_bytes() -> int:
    raw = os.getenv("AXION_PROMOTION_SCAN_MAX_BYTES", "").strip()
    if not raw:
        return DEFAULT_SCAN_MAX_BYTES
    try:
        value = int(raw)
    except Exception:
        return DEFAULT_SCAN_MAX_BYTES
    if value <= 0:
        return DEFAULT_SCAN_MAX_BYTES
    return value


def _has_executable_magic(head: bytes) -> bool:
    if head.startswith(b"MZ"):
        return True
    if head.startswith(b"\x7fELF"):
        return True
    if head.startswith(b"\xcf\xfa\xed\xfe") or head.startswith(b"\xfe\xed\xfa\xcf"):
        return True
    return False


def _validate_json(path: Path) -> bool:
    try:
        json.loads(path.read_text(encoding="utf-8-sig"))
        return True
    except Exception:
        return False


def _validate_text_utf8(path: Path) -> bool:
    try:
        path.read_text(encoding="utf-8-sig")
        return True
    except Exception:
        return False


def scan_artifact(path, meta):
    p = Path(path)
    if not p.exists() or not p.is_file():
        return False, "SCAN_FAIL_MISSING"

    size = p.stat().st_size
    expected_size = meta.get("sizeBytes") if isinstance(meta, dict) else None
    if expected_size is not None:
        try:
            if isinstance(expected_size, bool):
                return False, "SCAN_FAIL_SIZE_MISMATCH"
            expected_i = int(expected_size)
        except Exception:
            return False, "SCAN_FAIL_SIZE_MISMATCH"
        if expected_i != size:
            return False, "SCAN_FAIL_SIZE_MISMATCH"

    if size > _scan_max_bytes():
        return False, "SCAN_FAIL_TOO_LARGE"

    with p.open("rb") as f:
        head = f.read(4096)
    if _has_executable_magic(head):
        return False, "SCAN_FAIL_EXECUTABLE_MAGIC"

    mime_type = ""
    if isinstance(meta, dict):
        mime_type = str(meta.get("mimeType", "")).strip().lower()

    if mime_type == "application/json" and not _validate_json(p):
        return False, "SCAN_FAIL_JSON_PARSE"
    if mime_type.startswith("text/") and not _validate_text_utf8(p):
        return False, "SCAN_FAIL_TEXT_ENCODING"

    return True, "SCAN_OK"

