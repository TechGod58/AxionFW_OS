import json
from pathlib import Path

import bios_settings_bridge as bridge


def _write_json(path: Path, payload: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _policy_payload() -> dict:
    return {
        "version": 1,
        "policyId": "AXION_BIOS_SETTINGS_POLICY_V1",
        "allowedSettings": {
            "virtualization": {"type": "bool"},
            "iommu": {"type": "bool"},
            "secure_boot_mode": {"type": "enum", "allowed": ["standard", "custom", "disabled"]},
        },
        "forbiddenSettings": ["tpm", "bitlocker"],
    }


def test_stage_and_query_pending_bios_settings(monkeypatch, tmp_path: Path):
    policy_path = tmp_path / "BIOS_SETTINGS_POLICY_V1.json"
    pending_path = tmp_path / "pending_bios_settings_v1.json"
    audit_path = tmp_path / "bios_settings_staging_audit.json"
    _write_json(policy_path, _policy_payload())

    monkeypatch.setattr(bridge, "POLICY_PATH", policy_path)
    monkeypatch.setattr(bridge, "PENDING_PATH", pending_path)
    monkeypatch.setattr(bridge, "AUDIT_PATH", audit_path)

    staged = bridge.stage_bios_settings(
        {
            "virtualization": True,
            "iommu": True,
            "secure_boot_mode": "standard",
        },
        actor="pytest",
        corr="corr_bios_stage_001",
    )
    assert staged["ok"] is True
    assert staged["code"] == "BIOS_SETTINGS_STAGED_PENDING_RESTART"
    assert staged["pending"]["status"] == "PENDING_RESTART"
    assert staged["pending"]["apply_after_restart"] is True

    pending = bridge.get_pending_bios_settings()
    assert pending["ok"] is True
    assert pending["code"] == "BIOS_SETTINGS_PENDING_FOUND"
    assert pending["restart_required"] is True
    assert pending["pending"]["settings"]["virtualization"] is True


def test_stage_rejects_forbidden_or_unallowlisted_settings(monkeypatch, tmp_path: Path):
    policy_path = tmp_path / "BIOS_SETTINGS_POLICY_V1.json"
    pending_path = tmp_path / "pending_bios_settings_v1.json"
    audit_path = tmp_path / "bios_settings_staging_audit.json"
    _write_json(policy_path, _policy_payload())

    monkeypatch.setattr(bridge, "POLICY_PATH", policy_path)
    monkeypatch.setattr(bridge, "PENDING_PATH", pending_path)
    monkeypatch.setattr(bridge, "AUDIT_PATH", audit_path)

    bad = bridge.stage_bios_settings(
        {
            "tpm": True,
            "mystery_knob": "x",
        },
        actor="pytest",
    )
    assert bad["ok"] is False
    assert bad["code"] == "BIOS_SETTINGS_VALIDATION_FAIL"
    assert any("forbidden" in err.lower() for err in bad["errors"])
    assert any("allowlisted" in err.lower() for err in bad["errors"])
