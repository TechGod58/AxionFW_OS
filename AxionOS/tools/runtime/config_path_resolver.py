from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable

from runtime_paths import AXION_ROOT

_AXION_TOKEN_RE = re.compile(r"(?i)^axion_root:[\\/]*(.*)$")
_LEGACY_ROOT_RE = re.compile(r"(?i)^c:[\\/]+axionos(?:[\\/](.*))?$")


def _join_under_root(relative_fragment: str) -> Path:
    root = AXION_ROOT.resolve()
    normalized = relative_fragment.replace("\\", "/").strip("/")
    parts = [part for part in normalized.split("/") if part and part != "."]
    candidate = root.joinpath(*parts).resolve()
    candidate.relative_to(root)
    return candidate


def resolve_config_path_value(value: Any) -> Any:
    if not isinstance(value, str):
        return value

    raw = value.strip()
    if not raw:
        return value

    token_match = _AXION_TOKEN_RE.match(raw)
    if token_match:
        return _join_under_root(token_match.group(1))

    legacy_match = _LEGACY_ROOT_RE.match(raw)
    if legacy_match:
        return _join_under_root(legacy_match.group(1) or "")

    path = Path(raw).expanduser()
    if path.is_absolute():
        return path.resolve()

    return _join_under_root(raw)


def resolve_config_path_fields(config: dict[str, Any], path_fields: Iterable[str]) -> tuple[dict[str, Any], dict[str, str]]:
    resolved = dict(config)
    resolved_paths: dict[str, str] = {}
    for field in path_fields:
        if field not in resolved:
            continue
        path_value = resolve_config_path_value(resolved[field])
        if isinstance(path_value, Path):
            resolved[field] = str(path_value)
            resolved_paths[field] = str(path_value)
    return resolved, resolved_paths
