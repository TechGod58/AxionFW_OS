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


HOST = Path(axion_path_str("runtime", "shell_ui", "control_panel_host"))
if str(HOST) not in sys.path:
    sys.path.append(str(HOST))

import json
from control_panel_host import snapshot


if __name__ == "__main__":
    print(json.dumps(snapshot("corr_control_panel_app_001"), indent=2))
