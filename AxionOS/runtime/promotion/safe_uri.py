import re
from pathlib import Path, PureWindowsPath
from typing import Any

TRAVERSAL = re.compile(r"(^|[\\/])\.\.([\\/]|$)")
DRIVE = re.compile(r"^[a-zA-Z]:")
UNC = re.compile(r"^\\\\")
AXION_ROOT = Path(__file__).resolve().parents[2]


def _mime_allowed(mime_type: str, allowed: list[Any]) -> bool:
    if not allowed:
        return True
    mt = mime_type.strip().lower()
    if not mt:
        return False
    for rule in allowed:
        r = str(rule).strip().lower()
        if not r:
            continue
        if r.endswith("/"):
            if mt.startswith(r):
                return True
        elif mt == r:
            return True
    return False


def _policy_check(zone_cfg: dict[str, Any], rel: str, meta: dict[str, Any] | None) -> str:
    if meta is None:
        return "MAP_OK"

    rel_norm = rel.replace("/", "\\").lower()
    for ext in zone_cfg.get("blockedExtensions", []):
        ext_s = str(ext).strip().lower()
        if ext_s and rel_norm.endswith(ext_s):
            return "MAP_FAIL_POLICY_TYPE"

    if not _mime_allowed(str(meta.get("mimeType", "")), list(zone_cfg.get("allowedMimePrefixes", []))):
        return "MAP_FAIL_POLICY_TYPE"

    max_bytes = zone_cfg.get("maxBytes")
    if max_bytes is not None:
        try:
            max_bytes_i = int(max_bytes)
        except Exception:
            return "MAP_FAIL_POLICY_SIZE"
        try:
            size_v = meta.get("sizeBytes")
            if isinstance(size_v, bool):
                return "MAP_FAIL_POLICY_SIZE"
            size_i = int(size_v)
        except Exception:
            return "MAP_FAIL_POLICY_SIZE"
        if size_i < 0 or size_i > max_bytes_i:
            return "MAP_FAIL_POLICY_SIZE"

    return "MAP_OK"


def _resolve_policy_root(raw_root: str) -> Path:
    text = str(raw_root or "").strip()
    if not text:
        return AXION_ROOT / "data"

    pure = PureWindowsPath(text)
    if pure.is_absolute():
        parts = pure.parts
        if len(parts) >= 2 and parts[0].lower().startswith("c:") and parts[1].lower() == "axionos":
            tail = list(parts[2:])
            return AXION_ROOT.joinpath(*tail) if tail else AXION_ROOT
        return Path(text)
    return AXION_ROOT.joinpath(*Path(text).parts)


def resolve_safe_uri(uri: str, policy: dict, meta: dict[str, Any] | None = None):
    if not uri.startswith("safe://"):
        return False, "MAP_FAIL_SCHEME", None
    rest = uri[len("safe://") :]
    if "/" not in rest:
        return False, "MAP_FAIL_PATH_EMPTY", None
    zone, rel = rest.split("/", 1)
    if zone in policy.get("disallowedZones", []):
        return False, "MAP_FAIL_ZONE", None
    zones = policy.get("zones", {})
    z = zones.get(zone)
    if not z or not z.get("enabled", False):
        return False, "MAP_FAIL_ZONE", None
    if not rel:
        return False, "MAP_FAIL_PATH_EMPTY", None
    if TRAVERSAL.search(rel) or DRIVE.search(rel) or UNC.search(rel) or rel.startswith("/") or rel.startswith("\\"):
        return False, "MAP_FAIL_TRAVERSAL", None

    root = _resolve_policy_root(str(z.get("root", "")))
    resolved = (root / rel.replace("/", "\\")).resolve()
    try:
        resolved.relative_to(root.resolve())
    except Exception:
        return False, "MAP_FAIL_ESCAPE_DETECTED", None

    policy_code = _policy_check(z, rel, meta)
    if policy_code != "MAP_OK":
        return False, policy_code, None

    return True, "MAP_OK", str(resolved)
