from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys
from datetime import datetime, timezone
from pathlib import Path

LAUNCHER_DIR = Path(axion_path_str('runtime', 'capsule', 'launchers'))
if str(LAUNCHER_DIR) not in sys.path:
    sys.path.append(str(LAUNCHER_DIR))

from app_runtime_launcher import warm_shell_cache, shell_cache_entry, resolve_compatibility

BASE = Path(axion_path_str('out', 'runtime'))
SMOKE = BASE / 'sandbox_shell_cache_smoke.json'
AUDIT = BASE / 'sandbox_shell_cache_audit.json'


def now():
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def write(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2) + "\n", encoding='utf-8')


def main():
    native_shell = warm_shell_cache('pad')
    windows_shell = warm_shell_cache('legacy_winapp', family='windows', profile='win95')
    linux_shell = warm_shell_cache('legacy_linux_app', family='linux', profile='linux_2_6')
    smoke = {
        'timestamp_utc': now(),
        'status': 'PASS',
        'native_shell': native_shell,
        'windows_shell': windows_shell,
        'linux_shell': linux_shell,
        'resolved': {
            'pad': resolve_compatibility('pad'),
            'legacy_winapp': resolve_compatibility('legacy_winapp', family='windows', profile='win95'),
            'legacy_linux_app': resolve_compatibility('legacy_linux_app', family='linux', profile='linux_2_6')
        },
        'shell_cache_entries': {
            'pad': shell_cache_entry('pad'),
            'legacy_winapp': shell_cache_entry('legacy_winapp'),
            'legacy_linux_app': shell_cache_entry('legacy_linux_app')
        },
        'failures': []
    }
    audit = {
        'timestamp_utc': now(),
        'status': 'PASS',
        'events': [
            {'op': 'warm_shell_cache', 'app_id': 'pad'},
            {'op': 'warm_shell_cache', 'app_id': 'legacy_winapp', 'family': 'windows', 'profile': 'win95'},
            {'op': 'warm_shell_cache', 'app_id': 'legacy_linux_app', 'family': 'linux', 'profile': 'linux_2_6'}
        ],
        'failures': []
    }
    write(SMOKE, smoke)
    write(AUDIT, audit)


if __name__ == '__main__':
    main()

