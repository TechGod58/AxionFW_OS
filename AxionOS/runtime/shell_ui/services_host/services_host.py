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

STATE_PATH = Path(axion_path_str('config', 'SERVICES_STATE_V1.json'))


def _now():
    return datetime.now(timezone.utc).isoformat()


def _load():
    return json.loads(STATE_PATH.read_text(encoding='utf-8-sig'))


def _save(s):
    STATE_PATH.write_text(json.dumps(s, indent=2) + "\n", encoding='utf-8')


def snapshot(corr='corr_services_snap_001'):
    s = _load()
    out = {
        'ts': _now(),
        'corr': corr,
        'sections': s.get('sections', []),
        'services': s.get('services', {}),
        'actions': ['start_service', 'stop_service', 'restart_service', 'set_startup_type']
    }
    publish('shell.services.refreshed', {'ok': True}, corr=corr, source='services_host')
    return out


def set_startup_type(service_id: str, startup_type: str, corr='corr_services_startup_001'):
    if startup_type not in ('auto', 'manual', 'disabled'):
        return {'ok': False, 'code': 'SERVICES_STARTUP_INVALID'}
    s = _load()
    svc = s.get('services', {}).get(service_id)
    if not svc:
        return {'ok': False, 'code': 'SERVICES_NOT_FOUND'}
    svc['startup_type'] = startup_type
    _save(s)
    publish('shell.services.startup.changed', {'service_id': service_id, 'startup_type': startup_type}, corr=corr, source='services_host')
    return {'ok': True, 'code': 'SERVICES_STARTUP_SET_OK'}


def start_service(service_id: str, corr='corr_services_start_001'):
    s = _load()
    svc = s.get('services', {}).get(service_id)
    if not svc:
        return {'ok': False, 'code': 'SERVICES_NOT_FOUND'}
    if svc.get('startup_type') == 'disabled':
        return {'ok': False, 'code': 'SERVICES_START_DENIED'}
    svc['state'] = 'running'
    _save(s)
    publish('shell.services.started', {'service_id': service_id}, corr=corr, source='services_host')
    return {'ok': True, 'code': 'SERVICES_START_OK'}


def stop_service(service_id: str, corr='corr_services_stop_001'):
    s = _load()
    svc = s.get('services', {}).get(service_id)
    if not svc:
        return {'ok': False, 'code': 'SERVICES_NOT_FOUND'}
    if svc.get('protected'):
        return {'ok': False, 'code': 'SERVICES_STOP_DENIED'}
    svc['state'] = 'stopped'
    _save(s)
    publish('shell.services.stopped', {'service_id': service_id}, corr=corr, source='services_host')
    return {'ok': True, 'code': 'SERVICES_STOP_OK'}


def restart_service(service_id: str, corr='corr_services_restart_001'):
    stop_out = stop_service(service_id, corr=corr)
    if not stop_out.get('ok') and stop_out.get('code') != 'SERVICES_STOP_OK':
        return stop_out
    return start_service(service_id, corr=corr)


if __name__ == '__main__':
    print(json.dumps(snapshot(), indent=2))

