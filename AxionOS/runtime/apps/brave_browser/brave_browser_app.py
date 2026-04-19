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

ROOT = Path(axion_path_str('data', 'apps', 'brave_browser'))
ROOT.mkdir(parents=True, exist_ok=True)
STATE = ROOT / 'state.json'
BROWSER_STATE = Path(axion_path_str('config', 'BROWSER_EXPERIENCE_STATE_V1.json'))


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _load_browser_state():
    if not BROWSER_STATE.exists():
        return {}
    try:
        obj = json.loads(BROWSER_STATE.read_text(encoding='utf-8-sig'))
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def snapshot():
    browser = _load_browser_state()
    default_browser = dict(browser.get('default_browser') or {})
    first_boot = dict(browser.get('first_boot') or {})
    base = {
        'app': 'Brave Browser',
        'app_id': 'brave_browser',
        'ready': True,
        'preinstalled': True,
        'default_selected': str(default_browser.get('app_id') or '') == 'brave_browser',
        'first_boot_choice_completed': bool(first_boot.get('completed', False)),
        'updated_utc': _now_iso(),
    }
    if STATE.exists():
        try:
            existing = json.loads(STATE.read_text(encoding='utf-8-sig'))
            if isinstance(existing, dict):
                base.update(existing)
        except Exception:
            pass
    STATE.write_text(json.dumps(base, indent=2) + '\n', encoding='utf-8')
    return base


if __name__ == '__main__':
    print(json.dumps(snapshot(), indent=2))
