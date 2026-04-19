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
import sys
from pathlib import Path

EVENT_BUS_DIR = Path(axion_path_str('runtime', 'shell_ui', 'event_bus'))
if str(EVENT_BUS_DIR) not in sys.path:
    sys.path.append(str(EVENT_BUS_DIR))

from event_bus import publish
from state_bridge import save_state

STATE = {
    'label': 'Statistics',
    'is_open': False,
    'processes': [],
    'startup_apps': [],
    'resource_summary': {'cpu_pct': 0.0, 'memory_mb': 0, 'disk_io_mb': 0},
    'last_refresh_utc': None
}


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def _emit(topic, payload, corr=None):
    publish(topic, payload, corr=corr, source='statistics_host')
    save_state('statistics_host', snapshot(), corr=corr)


def open_statistics(corr=None):
    STATE['is_open'] = True
    STATE['last_refresh_utc'] = now_iso()
    _emit('shell.statistics.opened', {'open': True}, corr)
    return {'ok': True, 'code': 'STATISTICS_OPEN_OK'}


def close_statistics(corr=None):
    STATE['is_open'] = False
    _emit('shell.statistics.closed', {'open': False}, corr)
    return {'ok': True, 'code': 'STATISTICS_CLOSE_OK'}


def refresh(processes=None, startup_apps=None, corr=None):
    STATE['processes'] = list(processes or [])
    STATE['startup_apps'] = list(startup_apps or [])
    STATE['resource_summary'] = {
        'cpu_pct': round(len(STATE['processes']) * 3.5, 1),
        'memory_mb': len(STATE['processes']) * 96,
        'disk_io_mb': len(STATE['processes']) * 4
    }
    STATE['last_refresh_utc'] = now_iso()
    _emit('shell.statistics.refreshed', {'process_count': len(STATE['processes'])}, corr)
    return {'ok': True, 'code': 'STATISTICS_REFRESH_OK'}


def snapshot():
    return json.loads(json.dumps(STATE))


if __name__ == '__main__':
    print(json.dumps(snapshot(), indent=2))

