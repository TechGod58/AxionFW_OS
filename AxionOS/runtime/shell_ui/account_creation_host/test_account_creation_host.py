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

from account_creation_host import snapshot, create_account, run_setup_wizard

ACCOUNTS_PATH = Path(axion_path_str('config', 'ACCOUNTS_STATE_V1.json'))
INSTALL_IDENTITY_PATH = Path(axion_path_str('config', 'INSTALL_IDENTITY_V1.json'))
OS_ENCRYPTION_PATH = Path(axion_path_str('config', 'OS_ENCRYPTION_STATE_V1.json'))
PREBOOT_PATH = Path(axion_path_str('config', 'PREBOOT_AUTH_STATE_V1.json'))


def _remove_handle(handle: str):
    state = json.loads(ACCOUNTS_PATH.read_text(encoding='utf-8-sig'))
    state['users'] = [user for user in state.get('users', []) if user.get('handle') != handle]
    ACCOUNTS_PATH.write_text(json.dumps(state, indent=2) + "\n", encoding='utf-8')


def test_account_creation_snapshot():
    snap = snapshot()
    assert snap['defaults']['admin_first_run'] is True


def test_account_creation_create_standard_user():
    handle = f"builder_{uuid4().hex[:8]}"
    out = create_account('Builder', handle, role='User')
    try:
        assert out['ok']
        assert out['role'] == 'User'
        assert out['handle'] == handle
    finally:
        _remove_handle(handle)


def test_account_setup_wizard_optional_password_and_pin():
    handle = f"setup_{uuid4().hex[:8]}"
    accounts_before = ACCOUNTS_PATH.read_text(encoding="utf-8-sig")
    install_before = INSTALL_IDENTITY_PATH.read_text(encoding="utf-8-sig")
    preboot_before = PREBOOT_PATH.read_text(encoding="utf-8-sig")
    enc_before = OS_ENCRYPTION_PATH.read_text(encoding="utf-8-sig") if OS_ENCRYPTION_PATH.exists() else None
    out = run_setup_wizard(
        computer_name="AXION-SETUP",
        display_name="Setup User",
        handle=handle,
        role="Administrator",
        password=None,
        pin="1234",
        enable_fingerprint=True,
        enable_face_unlock=True,
        allow_email_escrow=False,
        corr="corr_account_setup_wizard_test_001",
    )
    try:
        assert out["ok"] is True
        assert out["code"] == "ACCOUNT_SETUP_WIZARD_OK"
        assert out["signin"]["password_enabled"] is False
        assert out["signin"]["pin_enabled"] is True
        assert out["signin"]["fingerprint_enabled"] is True
        assert out["signin"]["face_unlock_enabled"] is True
        assert out["encryption"]["code"] == "OS_ENCRYPTION_PROVISIONED"

        install = json.loads(INSTALL_IDENTITY_PATH.read_text(encoding="utf-8-sig"))
        assert install["install"]["computer_name"] == "AXION-SETUP"

        preboot = json.loads(PREBOOT_PATH.read_text(encoding="utf-8-sig"))
        assert preboot["methods"]["pin"] is True
        assert preboot["methods"]["fingerprint"] is True
        assert preboot["methods"]["face_unlock"] is True

        enc_state = json.loads(OS_ENCRYPTION_PATH.read_text(encoding="utf-8-sig"))
        assert enc_state["policy"]["enabled"] is True
        assert enc_state["runtime"]["status"] == "active"
    finally:
        ACCOUNTS_PATH.write_text(accounts_before, encoding="utf-8")
        INSTALL_IDENTITY_PATH.write_text(install_before, encoding="utf-8")
        PREBOOT_PATH.write_text(preboot_before, encoding="utf-8")
        if enc_before is None:
            if OS_ENCRYPTION_PATH.exists():
                OS_ENCRYPTION_PATH.unlink()
        else:
            OS_ENCRYPTION_PATH.write_text(enc_before, encoding="utf-8")

