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
from firewall_guard import list_quarantine_packets, adjudicate_quarantine_packet, replay_quarantine_packet
from os_encryption_guard import (
    snapshot as os_encryption_snapshot,
    provision as provision_os_encryption,
    rotate_recovery_key as rotate_os_encryption_recovery_key,
    set_email_escrow as set_os_encryption_email_escrow,
)

STATE_PATH = Path(axion_path_str('config', 'PRIVACY_SECURITY_STATE_V1.json'))
SHARING_STATE_PATH = Path(axion_path_str('config', 'SHARING_SECURITY_STATE_V1.json'))
REMOTE_STATE_PATH = Path(axion_path_str('config', 'REMOTE_DESKTOP_STATE_V1.json'))
FIREWALL_GUARD_STATE_PATH = Path(axion_path_str('config', 'FIREWALL_GUARD_STATE_V1.json'))


def _now():
    return datetime.now(timezone.utc).isoformat()


def _load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def _save(path, s):
    path.write_text(json.dumps(s, indent=2) + "\n", encoding='utf-8')


def snapshot(corr='corr_privsec_snap_001'):
    s = _load(STATE_PATH)
    sharing = _load(SHARING_STATE_PATH)
    remote = _load(REMOTE_STATE_PATH)
    fw_guard = _load(FIREWALL_GUARD_STATE_PATH) if FIREWALL_GUARD_STATE_PATH.exists() else {}
    encryption = os_encryption_snapshot(include_policy=True)
    out = {
        'ts': _now(),
        'corr': corr,
        'privacy': s.get('privacy', {}),
        'security': s.get('security', {}),
        'logging': s.get('logging', {}),
        'sharing': sharing.get('sharing', {}),
        'security_and_sharing': sharing.get('security_and_sharing', {}),
        'remote_desktop': remote.get('remote_desktop', {}),
        'os_encryption': encryption,
        'firewall_guard': {
            'session_count': len((fw_guard.get('sessions') or {}).keys()) if isinstance(fw_guard, dict) else 0,
            'quarantine_total': int((fw_guard.get('quarantine_total') or 0)) if isinstance(fw_guard, dict) else 0,
            'last_updated_utc': (fw_guard.get('last_updated_utc') if isinstance(fw_guard, dict) else None),
        },
        'actions': [
            'toggle_privacy_control',
            'set_telemetry_mode',
            'set_firewall_mode',
            'trigger_quick_scan',
            'set_lockdown_mode',
            'clear_non_required_logs',
            'set_file_sharing',
            'set_network_discovery',
            'set_remote_desktop',
            'get_os_encryption_status',
            'provision_os_encryption',
            'rotate_os_encryption_recovery_key',
            'set_os_encryption_email_escrow',
            'get_firewall_guard_status',
            'list_firewall_quarantine',
            'adjudicate_firewall_quarantine',
            'replay_firewall_quarantine'
        ]
    }
    publish('shell.privacy_security.refreshed', {'ok': True}, corr=corr, source='privacy_security_host')
    return out


def set_privacy_toggle(name: str, value: bool, corr='corr_privsec_toggle_001'):
    s = _load(STATE_PATH)
    p = s.get('privacy', {})
    if name not in p or not isinstance(p[name], bool):
        return {'ok': False, 'code': 'PRIVACY_TOGGLE_UNKNOWN'}
    old = p[name]
    p[name] = bool(value)
    _save(STATE_PATH, s)
    publish('shell.privacy.changed', {'name': name, 'old': old, 'new': bool(value)}, corr=corr, source='privacy_security_host')
    return {'ok': True, 'code': 'PRIVACY_TOGGLE_SET_OK', 'name': name, 'value': bool(value)}


def set_telemetry_mode(mode: str, corr='corr_privsec_telemetry_001'):
    if mode not in ('off', 'local_only', 'opt_in_cloud'):
        return {'ok': False, 'code': 'PRIVACY_TELEMETRY_BAD_MODE'}
    s = _load(STATE_PATH)
    old = s['privacy']['telemetry_mode']
    s['privacy']['telemetry_mode'] = mode
    _save(STATE_PATH, s)
    publish('shell.privacy.telemetry.changed', {'old': old, 'new': mode}, corr=corr, source='privacy_security_host')
    return {'ok': True, 'code': 'PRIVACY_TELEMETRY_SET_OK', 'mode': mode}


def set_firewall_mode(mode: str, corr='corr_privsec_fw_001'):
    if mode not in ('standard', 'strict'):
        return {'ok': False, 'code': 'SECURITY_FIREWALL_BAD_MODE'}
    s = _load(STATE_PATH)
    old = s['security']['firewall_mode']
    s['security']['firewall_mode'] = mode
    _save(STATE_PATH, s)
    sharing = _load(SHARING_STATE_PATH)
    sharing.setdefault('security_and_sharing', {})['firewall_profile'] = 'private' if mode == 'strict' else 'public'
    sharing['security_and_sharing']['last_reviewed_utc'] = _now()
    _save(SHARING_STATE_PATH, sharing)
    publish('shell.security.firewall.changed', {'old': old, 'new': mode}, corr=corr, source='privacy_security_host')
    return {'ok': True, 'code': 'SECURITY_FIREWALL_SET_OK', 'mode': mode}


def set_lockdown_mode(enabled: bool, corr='corr_privsec_lockdown_001'):
    s = _load(STATE_PATH)
    old = s['security']['lockdown_mode']
    s['security']['lockdown_mode'] = bool(enabled)
    _save(STATE_PATH, s)
    publish('shell.security.lockdown.changed', {'old': old, 'new': bool(enabled)}, corr=corr, source='privacy_security_host')
    return {'ok': True, 'code': 'SECURITY_LOCKDOWN_SET_OK', 'enabled': bool(enabled)}


def trigger_quick_scan(corr='corr_privsec_scan_001'):
    publish('shell.security.scan.triggered', {'mode': 'quick'}, corr=corr, source='privacy_security_host')
    return {'ok': True, 'code': 'SECURITY_SCAN_TRIGGERED'}


def set_file_sharing(enabled: bool, corr='corr_privsec_share_001'):
    s = _load(SHARING_STATE_PATH)
    s.setdefault('sharing', {})['file_and_printer_sharing'] = bool(enabled)
    s['security_and_sharing']['last_reviewed_utc'] = _now()
    _save(SHARING_STATE_PATH, s)
    publish('shell.sharing.file_printer.changed', {'enabled': bool(enabled)}, corr=corr, source='privacy_security_host')
    return {'ok': True, 'code': 'SHARING_FILE_PRINTER_SET_OK', 'enabled': bool(enabled)}


def set_network_discovery(enabled: bool, corr='corr_privsec_discovery_001'):
    s = _load(SHARING_STATE_PATH)
    s.setdefault('sharing', {})['network_discovery'] = bool(enabled)
    s['security_and_sharing']['last_reviewed_utc'] = _now()
    _save(SHARING_STATE_PATH, s)
    publish('shell.sharing.discovery.changed', {'enabled': bool(enabled)}, corr=corr, source='privacy_security_host')
    return {'ok': True, 'code': 'SHARING_DISCOVERY_SET_OK', 'enabled': bool(enabled)}


def set_remote_desktop(enabled: bool, corr='corr_privsec_rdp_001'):
    s = _load(REMOTE_STATE_PATH)
    s.setdefault('remote_desktop', {})['enabled'] = bool(enabled)
    s['remote_desktop']['last_changed_utc'] = _now()
    _save(REMOTE_STATE_PATH, s)
    publish('shell.security.remote_desktop.changed', {'enabled': bool(enabled)}, corr=corr, source='privacy_security_host')
    return {'ok': True, 'code': 'SECURITY_REMOTE_DESKTOP_SET_OK', 'enabled': bool(enabled)}


def get_os_encryption_status(corr='corr_privsec_os_enc_status_001'):
    out = os_encryption_snapshot(include_policy=True)
    publish('shell.security.os_encryption.status', out, corr=corr, source='privacy_security_host')
    return out


def provision_os_encryption_setup(
    computer_name: str,
    user_name: str,
    user_handle: str,
    password: str | None = None,
    pin: str | None = None,
    enable_fingerprint: bool = False,
    enable_face_unlock: bool = False,
    recovery_email: str | None = None,
    allow_email_escrow: bool = False,
    corr='corr_privsec_os_enc_provision_001',
):
    out = provision_os_encryption(
        computer_name=computer_name,
        user_name=user_name,
        user_handle=user_handle,
        password=password,
        pin=pin,
        enable_fingerprint=bool(enable_fingerprint),
        enable_face_unlock=bool(enable_face_unlock),
        recovery_email=recovery_email,
        allow_email_escrow=bool(allow_email_escrow),
        corr=corr,
    )
    publish('shell.security.os_encryption.provisioned', out, corr=corr, source='privacy_security_host')
    return out


def rotate_os_recovery_key(reason: str = 'manual_rotation', corr='corr_privsec_os_enc_rotate_001'):
    out = rotate_os_encryption_recovery_key(reason=reason, corr=corr)
    publish('shell.security.os_encryption.recovery_key.rotated', out, corr=corr, source='privacy_security_host')
    return out


def set_os_recovery_email_escrow(address: str | None, enabled: bool, corr='corr_privsec_os_enc_email_001'):
    out = set_os_encryption_email_escrow(address=address, enabled=bool(enabled), corr=corr)
    publish('shell.security.os_encryption.email_escrow.changed', out, corr=corr, source='privacy_security_host')
    return out


def get_firewall_guard_status(corr='corr_privsec_fw_guard_001'):
    if not FIREWALL_GUARD_STATE_PATH.exists():
        return {'ok': False, 'code': 'SECURITY_FIREWALL_GUARD_STATE_MISSING'}
    obj = _load(FIREWALL_GUARD_STATE_PATH)
    out = {
        'ok': True,
        'code': 'SECURITY_FIREWALL_GUARD_STATUS_OK',
        'session_count': len((obj.get('sessions') or {}).keys()),
        'quarantine_total': int(obj.get('quarantine_total', 0)),
        'last_updated_utc': obj.get('last_updated_utc'),
    }
    publish('shell.security.firewall_guard.status', out, corr=corr, source='privacy_security_host')
    return out


def list_firewall_quarantine(limit: int = 32, app_id: str | None = None, decision: str | None = None, corr='corr_privsec_fw_quarantine_001'):
    out = list_quarantine_packets(limit=int(limit), app_id=app_id, decision=decision)
    publish('shell.security.firewall_guard.quarantine.list', out, corr=corr, source='privacy_security_host')
    return out


def adjudicate_firewall_quarantine(path: str, decision: str, note: str | None = None, corr='corr_privsec_fw_quarantine_adjudicate_001'):
    out = adjudicate_quarantine_packet(path=path, decision=decision, note=note, reviewer='privacy_security_host', corr=corr)
    publish('shell.security.firewall_guard.quarantine.adjudicated', out, corr=corr, source='privacy_security_host')
    return out


def replay_firewall_quarantine(path: str, corr='corr_privsec_fw_quarantine_replay_001'):
    out = replay_quarantine_packet(path=path, corr=corr)
    publish('shell.security.firewall_guard.quarantine.replayed', out, corr=corr, source='privacy_security_host')
    return out


if __name__ == '__main__':
    print(json.dumps(snapshot(), indent=2))

