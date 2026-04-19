from pathlib import Path

from preboot_auth_host import snapshot, choose_action, set_method_availability, axion_path_str

STATE_PATH = Path(axion_path_str("config", "PREBOOT_AUTH_STATE_V1.json"))


def test_preboot_auth_snapshot():
    snap = snapshot()
    assert snap["mode"] == "preboot_secure_desktop"
    assert snap["repair_option"]["visible_on_sign_in_screen"]


def test_preboot_auth_action():
    out = choose_action("repair")
    assert out["ok"]
    assert out["action"] == "repair"


def test_preboot_auth_set_method():
    before = STATE_PATH.read_text(encoding="utf-8-sig")
    try:
        out = set_method_availability("face", True)
        assert out["ok"] is True
        assert out["method"] == "face_unlock"
        snap = snapshot()
        assert snap["methods"]["face_unlock"] is True
        assert snap["methods"]["biometric"] is True
    finally:
        STATE_PATH.write_text(before, encoding="utf-8")
