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
import sys
from pathlib import Path
import json

BASE = Path(axion_path_str('runtime', 'shell_ui'))
sys.path += [
    str(BASE / 'event_bus'),
    str(BASE / 'taskbar_host'),
    str(BASE / 'start_menu_host'),
    str(BASE / 'tray_host'),
    str(BASE / 'settings_host'),
]

from event_bus import subscribe, snapshot_subscribers
import taskbar_host as tb
import start_menu_host as sm
import tray_host as tr
import settings_host as st

corr = 'corr_shell_integrated_001'

subscribe('shell.settings.changed', 'taskbar_host')
subscribe('shell.startmenu.opened', 'taskbar_host')
subscribe('shell.notifications.push', 'start_menu_host')

st.set_pref('taskbar_alignment', 'left', corr=corr)
sm.open_menu(corr=corr)
tr.push_notification('Axion', 'Integrated shell event bus online', corr=corr)
tb.pin_app('axion-settings', 'Axion Settings', corr=corr)

print(json.dumps({
    'corr': corr,
    'subscribers': snapshot_subscribers(),
    'taskbar': tb.snapshot(),
    'start_menu': sm.snapshot(),
    'tray': tr.snapshot(),
    'settings': st.snapshot()
}, indent=2))

