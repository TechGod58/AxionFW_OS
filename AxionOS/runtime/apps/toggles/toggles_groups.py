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
from pathlib import Path

STATE_PATH = Path(axion_path_str('config', 'TOGGLES_STATE_V1.json'))

GROUPS = {
    "connectivity": ["wifi","bluetooth","vpn","airplane_mode","metered_network"],
    "privacy": ["location","camera_access","microphone_access","clipboard_history","telemetry_mode_local_only"],
    "security": ["firewall_strict_mode","lockdown_mode","threat_scan_mode_quick"],
    "system": ["notifications","background_apps","autostart_permission"],
    "accessibility": ["reduced_motion","high_contrast","live_captions","on_screen_keyboard"],
    "personalization": ["visual_effects","night_light"],
    "developer": ["developer_mode"]
}


def load_state():
    return json.loads(STATE_PATH.read_text(encoding='utf-8-sig'))


def grouped_snapshot():
    s = load_state().get('toggles', {})
    out = {}
    for g, keys in GROUPS.items():
        out[g] = {k: s.get(k) for k in keys}
    return out


if __name__ == '__main__':
    print(json.dumps(grouped_snapshot(), indent=2))

