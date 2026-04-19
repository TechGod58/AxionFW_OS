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
import json, sys
from pathlib import Path
from datetime import datetime, timezone
BUS = Path(axion_path_str('runtime', 'shell_ui', 'event_bus'))
SECURITY_DIR = Path(axion_path_str('runtime', 'security'))
if str(BUS) not in sys.path: sys.path.append(str(BUS))
if str(SECURITY_DIR) not in sys.path: sys.path.append(str(SECURITY_DIR))
from event_bus import publish
try:
    from network_sandbox_hub import (
        set_ingress_adapter_state,
        hub_status as network_hub_status,
    )
except Exception:
    set_ingress_adapter_state = None
    network_hub_status = None
NETWORK_STATE_PATH = Path(axion_path_str('config', 'NETWORK_STATE_V1.json'))
IDENTITY_STATE_PATH = Path(axion_path_str('config', 'INSTALL_IDENTITY_V1.json'))
REMOTE_STATE_PATH = Path(axion_path_str('config', 'REMOTE_DESKTOP_STATE_V1.json'))


def _now(): return datetime.now(timezone.utc).isoformat()
def _load(path): return json.loads(path.read_text(encoding='utf-8-sig'))
def _save(path, s): path.write_text(json.dumps(s, indent=2) + "\n", encoding='utf-8')


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


def snapshot(corr='corr_net_snap_001'):
    net = _load(NETWORK_STATE_PATH)
    ident = _load(IDENTITY_STATE_PATH)
    remote = _load(REMOTE_STATE_PATH)
    hub = _network_hub_snapshot()
    out = {
        'ts': _now(),
        'corr': corr,
        **net,
        'install_identity': ident.get('install', {}),
        'remote_desktop': remote.get('remote_desktop', {}),
        'network_sandbox_hub': hub,
        'actions': [
            'set_wifi',
            'set_wired',
            'set_airplane',
            'set_vpn',
            'set_remote_desktop',
        ],
    }
    publish('shell.network.refreshed', {'ok': True}, corr=corr, source='network_host')
    return out


def set_wifi(enabled: bool, corr='corr_net_wifi_001'):
    s = _load(NETWORK_STATE_PATH)
    s['wifi']['enabled'] = bool(enabled)
    if enabled and bool(s.get('airplane_mode', False)):
        s['airplane_mode'] = False
    _save(NETWORK_STATE_PATH, s)
    adapter_sync = _sync_network_adapter('wifi', bool(enabled), corr)
    publish('shell.network.wifi.changed', {'enabled': bool(enabled)}, corr=corr, source='network_host')
    return {'ok': True, 'code': 'NETWORK_WIFI_SET_OK', 'adapter_sync': adapter_sync}


def set_wired(connected: bool, profile: str = None, corr='corr_net_wired_001'):
    s = _load(NETWORK_STATE_PATH)
    s.setdefault('ethernet', {})['connected'] = bool(connected)
    if profile is not None:
        s['ethernet']['profile'] = profile
    _save(NETWORK_STATE_PATH, s)
    adapter_sync = _sync_network_adapter('wired', bool(connected), corr)
    publish(
        'shell.network.wired.changed',
        {'connected': bool(connected), 'profile': s.get('ethernet', {}).get('profile')},
        corr=corr,
        source='network_host',
    )
    return {'ok': True, 'code': 'NETWORK_WIRED_SET_OK', 'adapter_sync': adapter_sync}


def set_airplane(enabled: bool, corr='corr_net_air_001'):
    s = _load(NETWORK_STATE_PATH)
    s['airplane_mode'] = bool(enabled)
    if enabled:
        s.setdefault('wifi', {})['enabled'] = False
    _save(NETWORK_STATE_PATH, s)
    wifi_sync = _sync_network_adapter('wifi', not bool(enabled), corr)
    bt_sync = _sync_network_adapter('bluetooth', False if bool(enabled) else True, corr)
    publish('shell.network.airplane.changed', {'enabled': bool(enabled)}, corr=corr, source='network_host')
    return {
        'ok': True,
        'code': 'NETWORK_AIRPLANE_SET_OK',
        'adapter_sync': {'wifi': wifi_sync, 'bluetooth': bt_sync},
    }


def set_vpn(connected: bool, profile: str = None, corr='corr_net_vpn_001'):
    s = _load(NETWORK_STATE_PATH)
    s['vpn']['connected'] = bool(connected)
    s['vpn']['enabled'] = bool(connected)
    s['vpn']['profile'] = profile
    _save(NETWORK_STATE_PATH, s)
    adapter_sync = _sync_network_adapter('vpn', bool(connected), corr)
    publish('shell.network.vpn.changed', {'connected': bool(connected), 'profile': profile}, corr=corr, source='network_host')
    return {'ok': True, 'code': 'NETWORK_VPN_SET_OK', 'adapter_sync': adapter_sync}


def set_computer_name(name: str, corr='corr_net_name_001'):
    if not name or len(str(name).strip()) < 2:
        return {'ok': False, 'code': 'NETWORK_COMPUTER_NAME_INVALID'}
    s = _load(IDENTITY_STATE_PATH)
    s.setdefault('install', {})['computer_name'] = str(name).strip()
    _save(IDENTITY_STATE_PATH, s)
    publish('shell.network.computer_name.changed', {'computer_name': s['install']['computer_name']}, corr=corr, source='network_host')
    return {'ok': True, 'code': 'NETWORK_COMPUTER_NAME_SET_OK', 'computer_name': s['install']['computer_name']}


def set_workgroup(name: str, corr='corr_net_workgroup_001'):
    if not name or len(str(name).strip()) < 2:
        return {'ok': False, 'code': 'NETWORK_WORKGROUP_INVALID'}
    s = _load(IDENTITY_STATE_PATH)
    s.setdefault('install', {})['workgroup'] = str(name).strip()
    _save(IDENTITY_STATE_PATH, s)
    publish('shell.network.workgroup.changed', {'workgroup': s['install']['workgroup']}, corr=corr, source='network_host')
    return {'ok': True, 'code': 'NETWORK_WORKGROUP_SET_OK', 'workgroup': s['install']['workgroup']}


def set_remote_desktop(enabled: bool, corr='corr_net_rdp_001'):
    s = _load(REMOTE_STATE_PATH)
    s.setdefault('remote_desktop', {})['enabled'] = bool(enabled)
    s['remote_desktop']['last_changed_utc'] = _now()
    _save(REMOTE_STATE_PATH, s)
    rdp = s.get('remote_desktop', {})
    admin_sync = _sync_network_adapter('rdp_admin', bool(enabled and bool(rdp.get('allow_admins', True))), corr)
    user_sync = _sync_network_adapter('rdp_user', bool(enabled and bool(rdp.get('allow_users', False))), corr)
    publish('shell.network.remote_desktop.changed', {'enabled': bool(enabled)}, corr=corr, source='network_host')
    return {
        'ok': True,
        'code': 'NETWORK_REMOTE_DESKTOP_SET_OK',
        'enabled': bool(enabled),
        'adapter_sync': {'rdp_admin': admin_sync, 'rdp_user': user_sync},
    }


if __name__ == '__main__': print(json.dumps(snapshot(), indent=2))

