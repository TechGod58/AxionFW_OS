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

STATE_PATH = Path(axion_path_str('config', 'HARDWARE_DIAGNOSTICS_STATE_V1.json'))


def _now():
    return datetime.now(timezone.utc).isoformat()


def _load():
    return json.loads(STATE_PATH.read_text(encoding='utf-8-sig'))


def snapshot(corr='corr_hw_diag_001'):
    s = _load()
    out = {'ts': _now(), 'corr': corr, **s}
    publish('shell.hardware_diagnostics.refreshed', {'ok': True}, corr=corr, source='hardware_diagnostics_host')
    return out


def run_test(test_id: str, corr='corr_hw_diag_run_001'):
    s = _load()
    for test in s.get('tests', []):
        if test.get('id') == test_id:
            publish('shell.hardware_diagnostics.test.run', {'test_id': test_id}, corr=corr, source='hardware_diagnostics_host')
            return {'ok': True, 'code': 'HARDWARE_DIAGNOSTICS_TEST_OK', 'result': 'PASS', **test}
    return {'ok': False, 'code': 'HARDWARE_DIAGNOSTICS_TEST_UNKNOWN'}


if __name__ == '__main__':
    print(json.dumps(snapshot(), indent=2))

