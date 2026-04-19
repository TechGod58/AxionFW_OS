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

BASE = Path(axion_path_str('runtime', 'shell_ui'))
for p in ['taskbar_host', 'start_menu_host', 'tray_host', 'settings_host', 'event_bus']:
    pp = str(BASE / p)
    if pp not in sys.path:
        sys.path.append(pp)

import taskbar_host as taskbar
import start_menu_host as start
import tray_host as tray
import settings_host as settings
from event_bus import subscribe, publish, snapshot_subscribers

STATE_PATH = Path(axion_path_str('data', 'apps', 'pulse_monitor', 'state.json'))

LIVE = {
    'events': [],
    'subscribed': False
}


def _now():
    return datetime.now(timezone.utc).isoformat()


def _save(state):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding='utf-8')


def _record_event(topic, payload, corr=None):
    LIVE['events'].insert(0, {
        'ts': _now(),
        'topic': topic,
        'payload': payload,
        'corr': corr
    })
    LIVE['events'] = LIVE['events'][:300]


def wire_live_topics():
    if LIVE['subscribed']:
        return {'ok': True, 'code': 'PULSE_LIVE_ALREADY_WIRED'}
    topics = [
        'shell.taskbar.app.started',
        'shell.taskbar.app.stopped',
        'shell.settings.changed',
        'shell.notifications.push',
        'shell.startmenu.opened',
        'shell.startmenu.closed'
    ]
    for t in topics:
        subscribe(t, 'pulse_monitor')
    LIVE['subscribed'] = True
    return {'ok': True, 'code': 'PULSE_LIVE_WIRED', 'topics': topics}


def ingest_event(topic: str, payload: dict, corr: str = None):
    _record_event(topic, payload, corr)
    return {'ok': True, 'code': 'PULSE_EVENT_INGEST_OK', 'topic': topic}


def collect_snapshot(corr='corr_pulse_001'):
    t = taskbar.snapshot()
    s = start.snapshot()
    tr = tray.snapshot()
    se = settings.snapshot()

    processes = []
    for r in t.get('running', []):
        processes.append({
            'name': r.get('label'),
            'app_id': r.get('app_id'),
            'corr': r.get('corr') or corr,
            'launch_mode': 'capsule',
            'state': 'running'
        })

    services = [
        {'name': 'shell_event_bus', 'state': 'running'},
        {'name': 'shell_orchestrator', 'state': 'running'},
        {'name': 'pulse_monitor', 'state': 'running'}
    ]

    startup = [
        {'name': 'Axion Launch', 'enabled': True, 'impact': 'low'},
        {'name': 'Axion Tray Host', 'enabled': True, 'impact': 'low'}
    ]

    perf = {
        'cpu_pct': 8,
        'mem_pct': 23,
        'disk_pct': 4,
        'net_pct': 2,
        'gpu_pct': 6,
        'ts': _now()
    }

    out = {
        'corr': corr,
        'ts': _now(),
        'live': {
            'subscribed': LIVE['subscribed'],
            'subscriber_topics': snapshot_subscribers().get('shell.settings.changed', []) if LIVE['subscribed'] else [],
            'recent_events': LIVE['events'][:25]
        },
        'tabs': {
            'processes': processes,
            'performance': perf,
            'startup': startup,
            'services': services,
            'users': [{'name': 'default', 'state': 'active'}],
            'details': {
                'taskbar_alignment': se.get('prefs', {}).get('taskbar_alignment'),
                'notifications': len(tr.get('notifications', [])),
                'start_open': s.get('is_open', False)
            }
        }
    }
    _save(out)
    return out


def demo_live(corr='corr_pulse_live_001'):
    wire_live_topics()
    publish('shell.settings.changed', {'key': 'taskbar_alignment', 'new': 'left'}, corr=corr, source='demo')
    ingest_event('shell.settings.changed', {'key': 'taskbar_alignment', 'new': 'left'}, corr)
    publish('shell.notifications.push', {'title': 'Pulse', 'level': 'info'}, corr=corr, source='demo')
    ingest_event('shell.notifications.push', {'title': 'Pulse', 'level': 'info'}, corr)
    publish('shell.startmenu.opened', {'open': True}, corr=corr, source='demo')
    ingest_event('shell.startmenu.opened', {'open': True}, corr)
    return collect_snapshot(corr)


if __name__ == '__main__':
    print(json.dumps(demo_live(), indent=2))

