import json
from pathlib import Path

from firmware_os_handoff_enforcement_flow import evaluate_handoff, run_enforcement


def _write_json(path: Path, payload: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _base_inputs():
    contract = {
        "contractId": "AXION_FIRMWARE_OS_HARDWARE_CONTRACT_V1",
        "firmware": {
            "requiredArtifacts": ["OVMF_CODE.fd", "OVMF_VARS.fd"],
            "requiredServices": ["UEFI Boot Services", "UEFI Runtime Services", "ACPI table export"],
        },
        "os": {
            "requiredConsumers": [
                "AxionHAL firmware_handoff class",
                "AxionHAL motherboard_core class",
                "security_trust class",
            ],
            "driverInstallMode": "firmware_first_os_second",
        },
        "sharedContracts": {
            "biosSettingsApplyMode": "pending_restart_only",
        },
    }
    handoff = {
        "driver_install_mode": "firmware_first_os_second",
        "inventory": {"manifest_path": "C:/tmp/inventory.json"},
        "firmware_runtime": {
            "services": ["UEFI Boot Services", "UEFI Runtime Services", "ACPI table export"],
        },
        "parallel_cubed_hardware_guard": {
            "enabled": True,
            "strict_mode": True,
        },
    }
    firmware_manifest = {"files": ["OVMF_CODE.fd", "OVMF_VARS.fd"]}
    smart_driver_state = {
        "ready": True,
        "required_driver_classes": ["firmware_handoff", "motherboard_core", "security_trust"],
        "synthesized_drivers": [],
    }
    smart_driver_kernel_handoff = {"payload": {"ready": 1}}
    parallel_policy = {"hardwareGuard": {"enabled": True, "strictMode": True}}
    hardware_guard_report = {"payload": {"enabled": 1, "strict_mode": 1}}
    return {
        "contract": contract,
        "handoff": handoff,
        "firmware_manifest": firmware_manifest,
        "smart_driver_state": smart_driver_state,
        "smart_driver_kernel_handoff": smart_driver_kernel_handoff,
        "parallel_policy": parallel_policy,
        "hardware_guard_report": hardware_guard_report,
    }


def test_evaluate_handoff_detects_missing_artifacts(tmp_path: Path):
    inputs = _base_inputs()
    inputs["firmware_manifest"] = {"files": ["OVMF_CODE.fd"]}
    inventory = tmp_path / "inventory.json"
    inventory.write_text("{}\n", encoding="utf-8")
    inputs["handoff"]["inventory"]["manifest_path"] = str(inventory)

    result = evaluate_handoff(**inputs)
    assert result["checks"]["PASS_FIRMWARE_ARTIFACTS_AVAILABLE"] is False
    assert any(x["code"] == "FIRMWARE_OS_HANDOFF_MISSING_ARTIFACTS" for x in result["failures"])


def test_evaluate_handoff_passes_with_valid_inputs(tmp_path: Path):
    inputs = _base_inputs()
    inventory = tmp_path / "inventory.json"
    inventory.write_text("{}\n", encoding="utf-8")
    inputs["handoff"]["inventory"]["manifest_path"] = str(inventory)

    result = evaluate_handoff(**inputs)
    assert len(result["failures"]) == 0
    assert all(result["checks"].values())


def test_run_enforcement_pass_status(tmp_path: Path):
    inputs = _base_inputs()
    inventory = tmp_path / "inventory.json"
    inventory.write_text("{}\n", encoding="utf-8")
    inputs["handoff"]["inventory"]["manifest_path"] = str(inventory)

    contract_path = tmp_path / "contract.json"
    handoff_path = tmp_path / "handoff.json"
    firmware_manifest_path = tmp_path / "firmware_manifest.json"
    smart_driver_state_path = tmp_path / "smart_driver_state.json"
    smart_driver_kernel_handoff_path = tmp_path / "smart_driver_kernel_handoff.json"
    parallel_policy_path = tmp_path / "parallel_policy.json"
    hardware_guard_report_path = tmp_path / "hardware_guard_report.json"

    _write_json(contract_path, inputs["contract"])
    _write_json(handoff_path, inputs["handoff"])
    _write_json(firmware_manifest_path, inputs["firmware_manifest"])
    _write_json(smart_driver_state_path, inputs["smart_driver_state"])
    _write_json(smart_driver_kernel_handoff_path, inputs["smart_driver_kernel_handoff"])
    _write_json(parallel_policy_path, inputs["parallel_policy"])
    _write_json(hardware_guard_report_path, inputs["hardware_guard_report"])

    report = run_enforcement(
        contract_path=contract_path,
        handoff_path=handoff_path,
        firmware_manifest_path=firmware_manifest_path,
        smart_driver_state_path=smart_driver_state_path,
        smart_driver_kernel_handoff_path=smart_driver_kernel_handoff_path,
        parallel_policy_path=parallel_policy_path,
        hardware_guard_report_path=hardware_guard_report_path,
    )

    assert report["status"] == "PASS"
    assert report["failure_count"] == 0


def test_evaluate_handoff_fails_when_bios_pending_not_restart_gated(tmp_path: Path):
    inputs = _base_inputs()
    inventory = tmp_path / "inventory.json"
    inventory.write_text("{}\n", encoding="utf-8")
    inputs["handoff"]["inventory"]["manifest_path"] = str(inventory)
    inputs["handoff"]["firmware_runtime"]["bios_settings_pending"] = {
        "present": True,
        "status": "READY",
        "apply_after_restart": False,
    }

    result = evaluate_handoff(**inputs)
    assert result["checks"]["PASS_BIOS_SETTINGS_APPLY_AFTER_RESTART"] is False
    assert any(x["code"] == "FIRMWARE_OS_HANDOFF_BIOS_SETTINGS_RESTART_POLICY_VIOLATION" for x in result["failures"])
