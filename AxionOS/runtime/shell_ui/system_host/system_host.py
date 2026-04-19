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
from datetime import datetime, timezone
import sys

BASE = Path(axion_path_str('runtime', 'shell_ui'))
for p in ['event_bus', 'settings_host', 'desktop_host']:
    pp = str(BASE / p)
    if pp not in sys.path:
        sys.path.append(pp)

from event_bus import publish
import settings_host as settings
import desktop_host as desktop

STATE_PATH = Path(axion_path_str('config', 'SYSTEM_STATE_V1.json'))
RUNTIME_STATE_PATH = Path(axion_path_str('data', 'state', 'system_host_state.json'))


def _now():
    return datetime.now(timezone.utc).isoformat()


def _load():
    return json.loads(STATE_PATH.read_text(encoding='utf-8-sig'))


def _save_runtime(state):
    RUNTIME_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    RUNTIME_STATE_PATH.write_text(json.dumps(state, indent=2) + "\n", encoding='utf-8')


def _save_config(state):
    STATE_PATH.write_text(json.dumps(state, indent=2) + "\n", encoding='utf-8')


def build_system_state(corr='corr_system_001'):
    cfg = _load()
    s = settings.snapshot()
    d = desktop.snapshot()

    out = {
        'ts': _now(),
        'corr': corr,
        'about': cfg.get('about', {}),
        'display': cfg.get('display', {}),
        'sound': cfg.get('sound', {}),
        'notifications': cfg.get('notifications', {}),
        'power': cfg.get('power', {}),
        'storage': cfg.get('storage', {}),
        'clipboard': cfg.get('clipboard', {}),
        'optional_features': cfg.get('optional_features', []),
        'performance': {
            'cpu_pct': 9,
            'mem_pct': 24,
            'storage_pct': 41,
            'gpu_pct': 7
        },
        'graphics': d.get('graphics', {}),
        'settings_refs': {
            'taskbar_alignment': s.get('prefs', {}).get('taskbar_alignment'),
            'notifications': s.get('prefs', {}).get('notifications')
        },
        'actions': [
            'open_cleanup',
            'open_checkpoint_manager',
            'set_graphics_quality',
            'toggle_visual_effects',
            'set_night_light',
            'set_power_mode',
            'set_storage_sense'
        ]
    }

    _save_runtime(out)
    publish('shell.system.refreshed', {'ok': True}, corr=corr, source='system_host')
    return out


def set_graphics_quality(level: str, corr='corr_system_graphics_001'):
    if level not in ('high', 'balanced', 'low'):
        return {'ok': False, 'code': 'SYSTEM_GRAPHICS_BAD_LEVEL'}
    desktop.set_graphics('quality', level)
    publish('shell.system.graphics.changed', {'quality': level}, corr=corr, source='system_host')
    return {'ok': True, 'code': 'SYSTEM_GRAPHICS_SET_OK', 'quality': level}


def set_visual_effects(enabled: bool, corr='corr_system_fx_001'):
    desktop.set_graphics('transparency', bool(enabled))
    desktop.set_graphics('blur', bool(enabled))
    publish('shell.system.visualfx.changed', {'enabled': bool(enabled)}, corr=corr, source='system_host')
    return {'ok': True, 'code': 'SYSTEM_VISUALFX_SET_OK', 'enabled': bool(enabled)}


def set_night_light(enabled: bool, corr='corr_system_night_001'):
    cfg = _load()
    cfg.setdefault('display', {})['night_light'] = bool(enabled)
    _save_config(cfg)
    publish('shell.system.night_light.changed', {'enabled': bool(enabled)}, corr=corr, source='system_host')
    return {'ok': True, 'code': 'SYSTEM_NIGHT_LIGHT_SET_OK'}


def set_power_mode(mode: str, corr='corr_system_power_001'):
    if mode not in ('best_efficiency', 'balanced', 'best_performance'):
        return {'ok': False, 'code': 'SYSTEM_POWER_BAD_MODE'}
    cfg = _load()
    cfg.setdefault('power', {})['mode'] = mode
    _save_config(cfg)
    publish('shell.system.power_mode.changed', {'mode': mode}, corr=corr, source='system_host')
    return {'ok': True, 'code': 'SYSTEM_POWER_MODE_SET_OK'}


def set_storage_sense(enabled: bool, corr='corr_system_storage_001'):
    cfg = _load()
    cfg.setdefault('storage', {})['storage_sense'] = bool(enabled)
    _save_config(cfg)
    publish('shell.system.storage_sense.changed', {'enabled': bool(enabled)}, corr=corr, source='system_host')
    return {'ok': True, 'code': 'SYSTEM_STORAGE_SENSE_SET_OK'}


if __name__ == '__main__':
    desktop.apply_defaults()
    print(json.dumps(build_system_state(), indent=2))

