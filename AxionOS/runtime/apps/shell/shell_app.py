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
from datetime import datetime, timezone
from pathlib import Path

DELEGATE = Path(axion_path_str("runtime", "apps", "powershell"))
if str(DELEGATE) not in sys.path:
    sys.path.append(str(DELEGATE))

from powershell_app import snapshot as _delegate_snapshot


def snapshot():
    out = _delegate_snapshot()
    return {
        "app": "Shell",
        "delegate": "powershell",
        "delegate_snapshot": out,
    }


if __name__ == '__main__':
    print(json.dumps(snapshot(), indent=2))
