import json
from pathlib import Path

from os_encryption_guard import (
    key_required_for_context,
    provision,
    rotate_recovery_key,
    set_email_escrow,
    snapshot,
    validate_pin,
)


def test_validate_pin():
    assert validate_pin("1234") is True
    assert validate_pin("12345678") is True
    assert validate_pin("123") is False
    assert validate_pin("123456789") is False
    assert validate_pin("12ab") is False


def test_key_requirement_contexts():
    assert key_required_for_context("external_disk_mount")["required"] is True
    assert key_required_for_context("normal_boot")["required"] is False


def test_provision_and_rotate_encryption(monkeypatch, tmp_path):
    state_path = tmp_path / "OS_ENCRYPTION_STATE_V1.json"
    recovery_dir = tmp_path / "recovery"
    audit_path = tmp_path / "audit.ndjson"
    state_path.write_text(
        json.dumps(
            {
                "version": 1,
                "policy": {"enabled": False, "allow_email_recovery_escrow": False},
                "runtime": {"status": "not_configured", "last_updated_utc": None, "last_key_rotation_utc": None},
                "recovery": {"key_id": None, "key_hint": None, "local_secure_path": None, "email_escrow": {"enabled": False, "address": None}},
                "setup_requirements": {"pin_length": {"min": 4, "max": 8}},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr("os_encryption_guard.STATE_PATH", state_path)
    monkeypatch.setattr("os_encryption_guard.RECOVERY_DIR", recovery_dir)
    monkeypatch.setattr("os_encryption_guard.AUDIT_PATH", audit_path)

    out = provision(
        computer_name="AXION-LAB",
        user_name="Builder",
        user_handle="builder",
        password="StrongPass123",
        pin="123456",
        enable_fingerprint=True,
        enable_face_unlock=True,
        corr="corr_os_enc_001",
    )
    assert out["ok"] is True
    assert out["code"] == "OS_ENCRYPTION_PROVISIONED"
    assert out["key_prompt_mode"] == "external_offline_access_only"
    assert out["normal_boot_unlock_mode"] == "transparent_via_trusted_boot"
    assert Path(out["recovery_package_path"]).exists()

    before = snapshot()
    assert before["runtime"]["status"] == "active"
    assert before["policy"]["requires_preboot_auth"] is False
    assert before["policy"]["key_prompt_mode"] == "external_offline_access_only"
    assert before["recovery"]["key_id"] == out["recovery_key_id"]

    rotated = rotate_recovery_key(corr="corr_os_enc_002", reason="test_rotation")
    assert rotated["ok"] is True
    assert rotated["code"] == "OS_ENCRYPTION_RECOVERY_KEY_ROTATED"
    assert rotated["recovery_key_id"] != out["recovery_key_id"]
    assert Path(rotated["recovery_package_path"]).exists()


def test_email_escrow_requires_policy(monkeypatch, tmp_path):
    state_path = tmp_path / "OS_ENCRYPTION_STATE_V1.json"
    state_path.write_text(
        json.dumps(
            {
                "version": 1,
                "policy": {"enabled": True, "allow_email_recovery_escrow": False},
                "runtime": {"status": "active"},
                "recovery": {"email_escrow": {"enabled": False, "address": None}},
                "setup_requirements": {},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("os_encryption_guard.STATE_PATH", state_path)
    monkeypatch.setattr("os_encryption_guard.RECOVERY_DIR", tmp_path / "recovery")
    monkeypatch.setattr("os_encryption_guard.AUDIT_PATH", tmp_path / "audit.ndjson")

    denied = set_email_escrow("user@example.com", True, corr="corr_os_enc_003")
    assert denied["ok"] is False
    assert denied["code"] == "OS_ENCRYPTION_EMAIL_ESCROW_DISABLED_BY_POLICY"
