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
import sys
from pathlib import Path
from datetime import datetime, timezone

BUS = Path(axion_path_str('runtime', 'shell_ui', 'event_bus'))
if str(BUS) not in sys.path:
    sys.path.append(str(BUS))

from event_bus import publish

STATE_PATH = Path(axion_path_str('config', 'PERSONALIZATION_STATE_V1.json'))


def _now():
    return datetime.now(timezone.utc).isoformat()


def _load():
    return json.loads(STATE_PATH.read_text(encoding='utf-8-sig'))


def _save(s):
    STATE_PATH.write_text(json.dumps(s, indent=2) + "\n", encoding='utf-8')


def snapshot(corr='corr_personal_snap_001'):
    s = _load()
    out = {
        'ts': _now(),
        'corr': corr,
        **s,
        'sections': ['Background', 'Colors', 'Themes', 'Lock Screen', 'Start', 'Taskbar', 'Fonts']
    }
    publish('shell.personalization.refreshed', {'ok': True}, corr=corr, source='personalization_host')
    return out


def set_theme(theme: str, corr='corr_personal_theme_001'):
    if theme not in ('light', 'dark', 'custom'):
        return {'ok': False, 'code': 'PERSONAL_THEME_BAD_VALUE'}
    s = _load(); old = s['theme']; s['theme'] = theme; _save(s)
    publish('shell.personalization.theme.changed', {'old': old, 'new': theme}, corr=corr, source='personalization_host')
    return {'ok': True, 'code': 'PERSONAL_THEME_SET_OK', 'theme': theme}


def set_accent(mode: str, accent: str = None, corr='corr_personal_accent_001'):
    if mode not in ('auto', 'manual'):
        return {'ok': False, 'code': 'PERSONAL_ACCENT_MODE_BAD'}
    s = _load(); s['accent_mode'] = mode
    if accent:
        s['accent'] = accent
    _save(s)
    publish('shell.personalization.accent.changed', {'mode': mode, 'accent': s['accent']}, corr=corr, source='personalization_host')
    return {'ok': True, 'code': 'PERSONAL_ACCENT_SET_OK'}


def set_wallpaper_pack(name: str, corr='corr_personal_wall_001'):
    s = _load(); s['wallpaper_pack'] = name; _save(s)
    publish('shell.personalization.wallpaper.changed', {'pack': name}, corr=corr, source='personalization_host')
    return {'ok': True, 'code': 'PERSONAL_WALLPAPER_SET_OK', 'pack': name}


def set_lock_screen_background(name: str, corr='corr_personal_lock_001'):
    s = _load(); s.setdefault('lock_screen', {})['background'] = name; _save(s)
    publish('shell.personalization.lock_screen.changed', {'background': name}, corr=corr, source='personalization_host')
    return {'ok': True, 'code': 'PERSONAL_LOCK_SCREEN_SET_OK'}


def set_desktop_icon(name: str, enabled: bool, corr='corr_personal_icons_001'):
    s = _load(); icons = s.get('desktop_icons', {})
    if name not in icons:
        return {'ok': False, 'code': 'PERSONAL_ICON_UNKNOWN'}
    icons[name] = bool(enabled); _save(s)
    publish('shell.personalization.desktop_icon.changed', {'name': name, 'enabled': bool(enabled)}, corr=corr, source='personalization_host')
    return {'ok': True, 'code': 'PERSONAL_ICON_SET_OK'}


def set_taskbar_alignment(mode: str, corr='corr_personal_taskbar_001'):
    if mode not in ('center', 'left'):
        return {'ok': False, 'code': 'PERSONAL_TASKBAR_BAD_VALUE'}
    s = _load(); s['taskbar_alignment'] = mode; _save(s)
    publish('shell.personalization.taskbar_alignment.changed', {'alignment': mode}, corr=corr, source='personalization_host')
    return {'ok': True, 'code': 'PERSONAL_TASKBAR_ALIGNMENT_SET_OK', 'alignment': mode}


def set_start_layout(name: str, corr='corr_personal_start_001'):
    s = _load(); s['start_layout'] = name; _save(s)
    publish('shell.personalization.start_layout.changed', {'layout': name}, corr=corr, source='personalization_host')
    return {'ok': True, 'code': 'PERSONAL_START_LAYOUT_SET_OK'}


if __name__ == '__main__':
    print(json.dumps(snapshot(), indent=2))

