from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.append(str(SCRIPTS_DIR))

import fw_rewrite_engine as eng


def _save(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _inventory_payload(vendor: str = "UnknownVendor", model: str = "MysteryBoard") -> dict:
    return {
        "machine_id": "TESTMACHINE01",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "counts": {
            "pci_devices": 4,
            "acpi_devices": 3,
            "usb_devices": 2,
        },
        "inventory": {
            "computer_system": {
                "Manufacturer": vendor,
                "Model": model,
                "SystemFamily": "custom",
            },
            "bios": {
                "Manufacturer": vendor,
                "SMBIOSBIOSVersion": "1.0.0",
            },
            "baseboard": {
                "Manufacturer": vendor,
                "Product": "X1",
            },
            "processor": {
                "Manufacturer": vendor,
                "Name": f"{vendor} CPU",
            },
        },
    }


def _primitive_catalog() -> dict:
    return {
        "default_primitives": ["inventory_guard", "backup_firmware_payload", "stage_inactive_slot"],
        "primitives": {
            "inventory_guard": {"description": "guard"},
            "backup_firmware_payload": {"description": "backup"},
            "stage_inactive_slot": {"description": "stage"},
        },
    }


def _adapter_contract() -> dict:
    return {
        "default_adapter_id": "generic_uefi_fallback_v1",
        "adapters": [
            {
                "adapter_id": "intel_pch_generic_v1",
                "platform_lanes": ["intel_x64"],
                "vendor_hints": ["intel"],
                "chipset_hints": ["q35"],
                "required_buses": ["pci", "acpi"],
                "primitive_ids": ["inventory_guard"],
            },
            {
                "adapter_id": "generic_uefi_fallback_v1",
                "platform_lanes": ["generic_x64_uefi", "intel_x64", "amd_x64"],
                "vendor_hints": [],
                "chipset_hints": [],
                "required_buses": ["acpi"],
                "primitive_ids": ["inventory_guard", "backup_firmware_payload", "stage_inactive_slot"],
            },
        ],
    }


def test_build_capability_graph_auto_maps_unknown_board():
    graph = eng.build_capability_graph(
        inventory=_inventory_payload(),
        primitive_catalog=_primitive_catalog(),
        adapter_contract=_adapter_contract(),
    )
    sel = graph["adapter_selection"]
    assert sel["adapter_id"] == "generic_uefi_fallback_v1"
    assert sel["auto_mapped_unknown_board"] is True


def test_plan_sign_execute_requires_backup_and_sets_pending_slot(monkeypatch, tmp_path: Path):
    fw_base = tmp_path / "AxionFW" / "Base"
    manifest_dir = fw_base / "out" / "ovmf-q35-debug" / "testbuild"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    ovmf_code = manifest_dir / "OVMF_CODE.fd"
    ovmf_vars = manifest_dir / "OVMF_VARS.fd"
    ovmf_code.write_bytes(b"code-image")
    ovmf_vars.write_bytes(b"vars-image")
    _save(
        manifest_dir / "manifest.json",
        {"files": ["OVMF_CODE.fd", "OVMF_VARS.fd"], "profile": "debug", "version": "test"},
    )

    rewrite_root = fw_base / "out" / "rewrite"
    graph_path = rewrite_root / "capability_graph_v1.json"
    plan_path = rewrite_root / "rewrite_plan_v1.json"
    sig_path = rewrite_root / "rewrite_signature_v1.json"
    report_path = rewrite_root / "rewrite_execution_report.json"
    pending_bios_path = fw_base / "out" / "handoff" / "pending_bios_settings_v1.json"
    _save(
        pending_bios_path,
        {
            "status": "PENDING_RESTART",
            "apply_after_restart": True,
            "settings": {"iommu": True},
        },
    )

    graph = eng.build_capability_graph(
        inventory=_inventory_payload(),
        primitive_catalog=_primitive_catalog(),
        adapter_contract=_adapter_contract(),
    )
    _save(graph_path, graph)
    plan = eng.build_rewrite_plan(
        fw_base=fw_base,
        capability_graph=graph,
        pending_bios_settings_path=pending_bios_path,
        rewrite_plan_path=plan_path,
    )
    eng.save_json(plan_path, plan)

    monkeypatch.setenv("AXION_KMS_RELEASE_SIGNING_KEY_01", "test-rewrite-signing-key-material")
    sign = eng.sign_rewrite_plan(
        plan_path=plan_path,
        signature_path=sig_path,
        source_commit_sha="1111111111111111111111111111111111111111",
        build_pipeline_id="axion-firmware-rewrite-engine-test",
    )
    assert sign["ok"] is True, sign

    run = eng.execute_rewrite_plan(
        plan_path=plan_path,
        signature_path=sig_path,
        report_path=report_path,
        allow_physical_flash=False,
    )
    assert run["ok"] is True, run
    assert run["code"] == "FW_REWRITE_STAGED_PENDING_REBOOT"
    assert run["backup"] is not None
    assert Path(run["slot_state_path"]).exists()
    state = eng.load_json(Path(run["slot_state_path"]), {})
    assert state.get("pending_slot_on_reboot") in ("A", "B")
    assert state.get("brick_protection", {}).get("backup_created") is True


def test_execute_fails_when_signature_missing(tmp_path: Path):
    plan_path = tmp_path / "rewrite_plan_v1.json"
    sig_path = tmp_path / "rewrite_signature_v1.json"
    report = tmp_path / "rewrite_execution_report.json"
    _save(
        plan_path,
        {
            "plan_id": "test-plan",
            "execution_policy": {"mandatory_backup": True},
            "slots": {"slot_state_path": str(tmp_path / "slot_state.json"), "slots_root": str(tmp_path / "slots"), "active_slot": "A", "target_slot": "B"},
            "firmware_payload": {"files": []},
        },
    )
    out = eng.execute_rewrite_plan(
        plan_path=plan_path,
        signature_path=sig_path,
        report_path=report,
        allow_physical_flash=False,
    )
    assert out["ok"] is False
    assert out["code"] == "FW_REWRITE_SIGNATURE_INVALID"


def _prepare_signed_rewrite_plan(
    *,
    tmp_path: Path,
    monkeypatch,
    inventory_vendor: str = "Intel Corporation",
) -> tuple[Path, Path, Path]:
    fw_base = tmp_path / "AxionFW" / "Base"
    manifest_dir = fw_base / "out" / "ovmf-q35-debug" / "testbuild"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    (manifest_dir / "OVMF_CODE.fd").write_bytes(b"code-image")
    (manifest_dir / "OVMF_VARS.fd").write_bytes(b"vars-image")
    _save(
        manifest_dir / "manifest.json",
        {"files": ["OVMF_CODE.fd", "OVMF_VARS.fd"], "profile": "debug", "version": "test"},
    )
    policy_path = fw_base / "policy" / "physical_flash_executor_policy_v1.json"
    _save(
        policy_path,
        {
            "version": 1,
            "policy_id": "AXION_CONTROLLED_PHYSICAL_FLASH_POLICY_V1",
            "lane_enabled": True,
            "mode": "controlled_fail_closed",
            "allow": {
                "adapter_ids": ["intel_pch_generic_v1", "generic_uefi_fallback_v1"],
                "platform_lanes": ["intel_x64", "generic_x64_uefi"],
                "vendor_tokens": ["intel"],
            },
            "rollback_enforcement": {
                "require_backup_created": True,
                "require_ab_slots": True,
                "require_rollback_slot": True,
            },
            "operator_ack": {
                "required": True,
                "env": "AXION_PHYSICAL_FLASH_ACK",
                "value": "AXION_PHYSICAL_FLASH_UNDERSTAND_RISK",
                "session_env": "AXION_PHYSICAL_FLASH_SESSION_ID",
                "require_matching_plan_id": True,
            },
            "command_profiles": {
                "intel_pch_generic_v1": {"execution_kind": "receipt_only"},
                "generic_uefi_fallback_v1": {"execution_kind": "receipt_only"},
            },
        },
    )

    rewrite_root = fw_base / "out" / "rewrite"
    graph_path = rewrite_root / "capability_graph_v1.json"
    plan_path = rewrite_root / "rewrite_plan_v1.json"
    sig_path = rewrite_root / "rewrite_signature_v1.json"
    pending_bios_path = fw_base / "out" / "handoff" / "pending_bios_settings_v1.json"
    _save(
        pending_bios_path,
        {
            "status": "PENDING_RESTART",
            "apply_after_restart": True,
            "settings": {"iommu": True},
        },
    )
    graph = eng.build_capability_graph(
        inventory=_inventory_payload(vendor=inventory_vendor, model="Q35 TestBoard"),
        primitive_catalog=_primitive_catalog(),
        adapter_contract=_adapter_contract(),
    )
    inventory_manifest_path = fw_base / "out" / "manifests" / "test_inventory.json"
    _save(inventory_manifest_path, _inventory_payload(vendor=inventory_vendor, model="Q35 TestBoard"))
    graph["inventory_manifest_path"] = str(inventory_manifest_path)
    _save(graph_path, graph)
    plan = eng.build_rewrite_plan(
        fw_base=fw_base,
        capability_graph=graph,
        pending_bios_settings_path=pending_bios_path,
        rewrite_plan_path=plan_path,
    )
    eng.save_json(plan_path, plan)
    monkeypatch.setenv("AXION_KMS_RELEASE_SIGNING_KEY_01", "test-rewrite-signing-key-material")
    signed = eng.sign_rewrite_plan(
        plan_path=plan_path,
        signature_path=sig_path,
        source_commit_sha="1111111111111111111111111111111111111111",
        build_pipeline_id="axion-firmware-rewrite-engine-test",
    )
    assert signed["ok"] is True
    return fw_base, plan_path, sig_path


def test_physical_flash_request_denies_without_operator_ack(monkeypatch, tmp_path: Path):
    fw_base, plan_path, sig_path = _prepare_signed_rewrite_plan(tmp_path=tmp_path, monkeypatch=monkeypatch)
    report_path = fw_base / "out" / "rewrite" / "rewrite_execution_report.json"
    out = eng.execute_rewrite_plan(
        plan_path=plan_path,
        signature_path=sig_path,
        report_path=report_path,
        allow_physical_flash=True,
    )
    assert out["ok"] is False
    assert out["code"] == "FW_REWRITE_PHYSICAL_FLASH_ACK_REQUIRED"
    state = eng.load_json(Path(out["slot_state_path"]), {})
    assert state.get("pending_slot_on_reboot") is None


def test_physical_flash_request_authorized_receipt_only(monkeypatch, tmp_path: Path):
    fw_base, plan_path, sig_path = _prepare_signed_rewrite_plan(tmp_path=tmp_path, monkeypatch=monkeypatch)
    plan = eng.load_json(plan_path, {})
    monkeypatch.setenv("AXION_PHYSICAL_FLASH_ACK", "AXION_PHYSICAL_FLASH_UNDERSTAND_RISK")
    monkeypatch.setenv("AXION_PHYSICAL_FLASH_SESSION_ID", str(plan.get("plan_id") or ""))
    report_path = fw_base / "out" / "rewrite" / "rewrite_execution_report.json"
    out = eng.execute_rewrite_plan(
        plan_path=plan_path,
        signature_path=sig_path,
        report_path=report_path,
        allow_physical_flash=True,
    )
    assert out["ok"] is True, out
    assert out["code"] == "FW_REWRITE_PHYSICAL_FLASH_CONTROLLED_PENDING_REBOOT"
    physical = out.get("physical_flash", {})
    assert str((physical.get("execution") or {}).get("code") or "") == "FW_REWRITE_PHYSICAL_FLASH_AUTHORIZED_RECEIPT_ONLY"
    receipt_path = Path(str((physical.get("execution") or {}).get("receipt_path") or ""))
    assert receipt_path.exists()
