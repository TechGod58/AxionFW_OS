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
from uuid import uuid4

from accounts_host import (
    snapshot,
    update_profile,
    set_signin_method,
    set_pin,
    set_password,
    generate_recovery_codes,
    session_action,
    set_role,
    create_local_account,
)

ACCOUNTS_PATH = Path(axion_path_str('config', 'ACCOUNTS_STATE_V1.json'))
PREBOOT_PATH = Path(axion_path_str('config', 'PREBOOT_AUTH_STATE_V1.json'))


def _remove_handle(handle: str):
    state = json.loads(ACCOUNTS_PATH.read_text(encoding='utf-8-sig'))
    state['users'] = [user for user in state.get('users', []) if user.get('handle') != handle]
    ACCOUNTS_PATH.write_text(json.dumps(state, indent=2) + "\n", encoding='utf-8')


def test_accounts_flow():
    state_before = ACCOUNTS_PATH.read_text(encoding='utf-8-sig')
    preboot_before = PREBOOT_PATH.read_text(encoding='utf-8-sig')
    try:
        assert update_profile(display_name='TechGod', handle='techgod')['ok']
        assert set_signin_method('pin', True)['ok']
        assert set_pin('1234')['ok']
        assert set_password(None)['ok']
        assert set_signin_method('fingerprint', True)['ok']
        assert set_role('Administrator')['ok']
        assert generate_recovery_codes()['ok']
        assert session_action('lock_session')['ok']
        out = snapshot('corr_accounts_test_001')
        assert out['account']['handle'] == 'techgod'
        assert out['account']['role'] == 'Administrator'
        assert out['signin']['fingerprint_enabled'] is True
        assert out['signin']['biometric_enabled'] is True
        assert out['preboot_auth']['repair_option']['visible_on_sign_in_screen']
        assert out['os_encryption']['code'] == 'OS_ENCRYPTION_STATUS_OK'
        assert out['default_setup']['bootstrap_admin_required']
    finally:
        ACCOUNTS_PATH.write_text(state_before, encoding='utf-8')
        PREBOOT_PATH.write_text(preboot_before, encoding='utf-8')


def test_accounts_create_local_account():
    handle = f"builder2_{uuid4().hex[:8]}"
    out = create_local_account('Builder Two', handle, role='User')
    try:
        assert out['ok']
        assert out['role'] == 'User'
        assert out['handle'] == handle
    finally:
        _remove_handle(handle)

