from __future__ import annotations

import os
from pathlib import Path


def _env_path(name: str) -> Path | None:
    value = os.getenv(name, "").strip()
    if not value:
        return None
    p = Path(value).expanduser()
    if p.exists():
        return p.resolve()
    return None


def axion_os_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "tools").is_dir() and (parent / "runtime").is_dir() and (parent / "config").is_dir():
            return parent

    env_root = _env_path("AXIONOS_ROOT")
    if env_root is not None:
        return env_root

    legacy = Path(os.getenv("SystemDrive", "C:")) / "AxionOS"
    if legacy.exists():
        return legacy.resolve()

    raise RuntimeError("Unable to locate AxionOS root. Set AXIONOS_ROOT to the workspace path.")


def axion_path(*parts: str) -> Path:
    return axion_os_root().joinpath(*parts)
