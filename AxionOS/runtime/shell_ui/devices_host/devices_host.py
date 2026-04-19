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
SECURITY_DIR = Path(axion_path_str('runtime', 'security'))
if str(BUS) not in sys.path:
    sys.path.append(str(BUS))
if str(SECURITY_DIR) not in sys.path:
    sys.path.append(str(SECURITY_DIR))

from event_bus import publish
try:
    from network_sandbox_hub import (
        set_ingress_adapter_state,
        hub_status as network_hub_status,
    )
except Exception:
    set_ingress_adapter_state = None
    network_hub_status = None

STATE_PATH = Path(axion_path_str('config', 'DEVICES_STATE_V1.json'))


def _now():
    return datetime.now(timezone.utc).isoformat()


def _load():
    return json.loads(STATE_PATH.read_text(encoding='utf-8-sig'))


def _save(s):
    STATE_PATH.write_text(json.dumps(s, indent=2) + "\n", encoding='utf-8')


def _sync_network_adapter(adapter: str, enabled: bool, corr: str):
    if not callable(set_ingress_adapter_state):
        return {'ok': True, 'code': 'NETWORK_SANDBOX_ADAPTER_SYNC_BYPASSED', 'adapter': str(adapter)}
    return set_ingress_adapter_state(
        adapter=str(adapter),
        enabled=bool(enabled),
        sandboxed=True,
        corr=corr,
    )


def _network_hub_snapshot():
    if not callable(network_hub_status):
        return {'ok': False, 'code': 'NETWORK_SANDBOX_HUB_UNAVAILABLE'}
    return network_hub_status()


def snapshot(corr='corr_devices_snap_001'):
    s = _load()
    out = {
        'ts': _now(),
        'corr': corr,
        'bluetooth': s.get('bluetooth', {}),
        'devices': s.get('devices', []),
        'audio': s.get('audio', {}),
        'printers': s.get('printers', []),
        'camera': s.get('camera', {}),
        'mouse': s.get('mouse', {}),
        'touchpad': s.get('touchpad', {}),
        'readers': s.get('readers', {}),
        'network_sandbox_hub': _network_hub_snapshot(),
        'actions': [
            'toggle_bluetooth',
            'set_discoverable',
            'pair_device',
            'unpair_device',
            'set_device_trust',
            'set_default_audio_output',
            'trigger_driver_rebind'
        ]
    }
    publish('shell.devices.refreshed', {'ok': True}, corr=corr, source='devices_host')
    return out


def toggle_bluetooth(enabled: bool, corr='corr_devices_bt_001'):
    s = _load()
    old = s['bluetooth']['enabled']
    s['bluetooth']['enabled'] = bool(enabled)
    if not enabled:
        s['bluetooth']['discoverable'] = False
    _save(s)
    adapter_sync = _sync_network_adapter('bluetooth', bool(enabled), corr)
    publish('shell.devices.bluetooth.changed', {'old': old, 'new': bool(enabled)}, corr=corr, source='devices_host')
    return {'ok': True, 'code': 'DEVICES_BLUETOOTH_SET_OK', 'enabled': bool(enabled), 'adapter_sync': adapter_sync}


def set_discoverable(enabled: bool, corr='corr_devices_discover_001'):
    s = _load()
    if not s['bluetooth']['enabled'] and enabled:
        return {'ok': False, 'code': 'DEVICES_DISCOVERABLE_DENIED'}
    s['bluetooth']['discoverable'] = bool(enabled)
    _save(s)
    publish('shell.devices.discoverable.changed', {'enabled': bool(enabled)}, corr=corr, source='devices_host')
    return {'ok': True, 'code': 'DEVICES_DISCOVERABLE_SET_OK'}


def pair_device(device_id: str, name: str, dtype='bluetooth', corr='corr_devices_pair_001'):
    s = _load()
    devs = s.get('devices', [])
    if any(d['device_id'] == device_id for d in devs):
        return {'ok': True, 'code': 'DEVICES_PAIR_EXISTS'}
    devs.append({
        'device_id': device_id,
        'name': name,
        'type': dtype,
        'state': 'connected',
        'trust': 'restricted',
        'driver': None,
        'sandboxed': True
    })
    _save(s)
    publish('shell.devices.paired', {'device_id': device_id, 'name': name}, corr=corr, source='devices_host')
    return {'ok': True, 'code': 'DEVICES_PAIR_OK', 'device_id': device_id}


def unpair_device(device_id: str, corr='corr_devices_unpair_001'):
    s = _load()
    before = len(s.get('devices', []))
    s['devices'] = [d for d in s.get('devices', []) if d.get('device_id') != device_id]
    _save(s)
    publish('shell.devices.unpaired', {'device_id': device_id}, corr=corr, source='devices_host')
    return {'ok': True, 'code': 'DEVICES_UNPAIR_OK' if len(s['devices']) < before else 'DEVICES_UNPAIR_NOOP'}


def set_device_trust(device_id: str, trust: str, corr='corr_devices_trust_001'):
    if trust not in ('trusted', 'restricted', 'blocked'):
        return {'ok': False, 'code': 'DEVICES_TRUST_BAD_VALUE'}
    s = _load()
    for d in s.get('devices', []):
        if d.get('device_id') == device_id:
            old = d.get('trust')
            d['trust'] = trust
            _save(s)
            publish('shell.devices.trust.changed', {'device_id': device_id, 'old': old, 'new': trust}, corr=corr, source='devices_host')
            return {'ok': True, 'code': 'DEVICES_TRUST_SET_OK', 'device_id': device_id, 'trust': trust}
    return {'ok': False, 'code': 'DEVICES_NOT_FOUND'}


def set_default_audio_output(name: str, corr='corr_devices_audio_001'):
    s = _load()
    s.setdefault('audio', {})['default_output'] = name
    _save(s)
    publish('shell.devices.audio_output.changed', {'name': name}, corr=corr, source='devices_host')
    return {'ok': True, 'code': 'DEVICES_AUDIO_OUTPUT_SET_OK'}


def trigger_driver_rebind(device_id: str, corr='corr_devices_rebind_001'):
    publish('shell.devices.driver.rebind.requested', {'device_id': device_id}, corr=corr, source='devices_host')
    return {'ok': True, 'code': 'DEVICES_REBIND_REQUESTED', 'device_id': device_id}


if __name__ == '__main__':
    print(json.dumps(snapshot(), indent=2))

