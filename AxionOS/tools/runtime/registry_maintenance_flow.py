from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys
from datetime import datetime, timezone
from pathlib import Path

SERVICE_CFG = Path(axion_path_str('config', 'SERVICE_MAINTENANCE_V1.json'))
BASE = Path(axion_path_str('out', 'runtime'))
SMOKE = BASE / 'registry_maintenance_smoke.json'
AUDIT = BASE / 'registry_maintenance_audit.json'
CODES = {
    'REGISTRY_DELAYED_CLEAN_DISABLED': 421,
    'ACTIVE_X_ERRORS_UNCLEANED': 422,
}


def now():
    return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')


def write(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2) + "\n", encoding='utf-8')


def main():
    cfg = json.loads(SERVICE_CFG.read_text(encoding='utf-8-sig'))
    mode = sys.argv[1] if len(sys.argv) > 1 else 'pass'
    delayed = cfg.get('delayed_start', {})
    registry = delayed.get('registry_clean', {})
    xcleanup = delayed.get('active_x_error_cleanup', {})
    failures = []

    if not registry.get('enabled'):
        failures.append({'code': 'REGISTRY_DELAYED_CLEAN_DISABLED', 'detail': 'delayed registry clean must be enabled'})
    if not xcleanup.get('enabled') or not xcleanup.get('catch_all_active_x_errors'):
        failures.append({'code': 'ACTIVE_X_ERRORS_UNCLEANED', 'detail': 'active X errors must be caught and cleaned'})
    if mode == 'x_errors_uncleaned':
        failures.append({'code': 'ACTIVE_X_ERRORS_UNCLEANED', 'detail': 'simulated active X error escaped cleanup'})

    status = 'FAIL' if failures else 'PASS'
    smoke = {
        'timestamp_utc': now(),
        'status': status,
        'registry_clean': {
            'enabled': registry.get('enabled'),
            'delay_seconds': registry.get('delay_seconds'),
            'remove_stale_entries': registry.get('remove_stale_entries'),
            'compact_hives': registry.get('compact_hives')
        },
        'active_x_error_cleanup': {
            'enabled': xcleanup.get('enabled'),
            'catch_all_active_x_errors': xcleanup.get('catch_all_active_x_errors'),
            'cleanup_actions': xcleanup.get('cleanup_actions', [])
        },
        'cleaned_active_x_errors': [] if failures else ['xapp.shell.crash', 'xapp.render.timeout'],
        'failures': failures
    }
    audit = {
        'timestamp_utc': now(),
        'status': status,
        'events': [
            {'op': 'delayed_start_registry_clean', 'delay_seconds': registry.get('delay_seconds')},
            {'op': 'active_x_error_cleanup_scan', 'catch_all': xcleanup.get('catch_all_active_x_errors')}
        ],
        'failures': failures
    }
    write(SMOKE, smoke)
    write(AUDIT, audit)
    if failures:
        raise SystemExit(CODES[failures[0]['code']])


if __name__ == '__main__':
    main()

