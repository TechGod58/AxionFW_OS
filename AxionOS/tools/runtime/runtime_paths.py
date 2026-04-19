from __future__ import annotations

from pathlib import Path
import sys

TOOLS_DIR = Path(__file__).resolve().parents[1]
if str(TOOLS_DIR) not in sys.path:
    sys.path.append(str(TOOLS_DIR))

from common.pathing import axion_path as _axion_path


def axion_path(*parts: str) -> Path:
    return _axion_path(*parts)


def axion_path_str(*parts: str) -> str:
    return str(_axion_path(*parts))


AXION_ROOT = _axion_path()
RUNTIME_OUT = _axion_path("out", "runtime")
RUNTIME_OUT.mkdir(parents=True, exist_ok=True)
