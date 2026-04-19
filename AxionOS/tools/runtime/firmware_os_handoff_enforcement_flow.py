#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from runtime_paths import AXION_ROOT

OUT = AXION_ROOT / "out" / "runtime"
OUT.mkdir(parents=True, exist_ok=True)
AUDIT_PATH = OUT / "firmware_os_handoff_enforcement_audit.json"
SMOKE_PATH = OUT / "firmware_os_handoff_enforcement_smoke.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_json(path: Path, default: Any):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return default


def resolve_workspace_root() -> Path:
    # AXION_ROOT = .../AxionOS
    return AXION_ROOT.parent


def resolve_latest_firmware_manifest(base_root: Path) -> Path | None:
    manifests = sorted((base_root / "out").glob("**/manifest.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not manifests:
        return None
    return manifests[0]


def parse_required_consumer_classes(consumers: list[str]) -> set[str]:
    known = {"firmware_handoff", "motherboard_core", "security_trust"}
    out: set[str] = set()
    for raw in consumers:
        text = str(raw or "").lower()
        for cls in known:
            if cls in text:
                out.add(cls)
    return out


def collect_available_driver_classes(state: dict[str, Any]) -> set[str]:
    out: set[str] = set()
    for cls in state.get("required_driver_classes") or []:
        s = str(cls or "").strip().lower()
        if s:
            out.add(s)
    for item in state.get("synthesized_drivers") or []:
        if isinstance(item, dict):
            s = str(item.get("driver_class") or "").strip().lower()
            if s:
                out.add(s)
    return out


def evaluate_handoff(
    *,
    contract: dict[str, Any],
    handoff: dict[str, Any],
    firmware_manifest: dict[str, Any],
    smart_driver_state: dict[str, Any],
    smart_driver_kernel_handoff: dict[str, Any],
    parallel_policy: dict[str, Any],
    hardware_guard_report: dict[str, Any],
) -> dict[str, Any]:
    checks: dict[str, bool] = {}
    failures: list[dict[str, str]] = []

    def mark(check_id: str, cond: bool, code: str, detail: str) -> None:
        checks[check_id] = bool(cond)
        if not cond:
            failures.append({"code": code, "detail": detail})

    required_artifacts = list(contract.get("firmware", {}).get("requiredArtifacts") or [])
    available_artifacts = set(str(x) for x in (firmware_manifest.get("files") or []))
    missing_artifacts = [x for x in required_artifacts if x not in available_artifacts]
    mark(
        "PASS_FIRMWARE_ARTIFACTS_AVAILABLE",
        len(missing_artifacts) == 0,
        "FIRMWARE_OS_HANDOFF_MISSING_ARTIFACTS",
        f"missing artifacts: {missing_artifacts}",
    )

    required_services = set(str(x) for x in (contract.get("firmware", {}).get("requiredServices") or []))
    handoff_services = set(str(x) for x in (handoff.get("firmware_runtime", {}).get("services") or []))
    missing_services = sorted(required_services - handoff_services)
    mark(
        "PASS_FIRMWARE_RUNTIME_SERVICES_DECLARED",
        len(missing_services) == 0,
        "FIRMWARE_OS_HANDOFF_MISSING_SERVICES",
        f"missing services: {missing_services}",
    )

    required_consumers = parse_required_consumer_classes(list(contract.get("os", {}).get("requiredConsumers") or []))
    available_classes = collect_available_driver_classes(smart_driver_state)
    missing_classes = sorted(required_consumers - available_classes)
    mark(
        "PASS_OS_REQUIRED_CONSUMER_CLASSES_PRESENT",
        len(missing_classes) == 0,
        "FIRMWARE_OS_HANDOFF_MISSING_DRIVER_CLASSES",
        f"missing required driver classes: {missing_classes}",
    )

    expected_install_mode = str(contract.get("os", {}).get("driverInstallMode") or "")
    actual_install_mode = str(handoff.get("driver_install_mode") or "")
    mark(
        "PASS_DRIVER_INSTALL_MODE_MATCH",
        expected_install_mode == actual_install_mode,
        "FIRMWARE_OS_HANDOFF_DRIVER_INSTALL_MODE_MISMATCH",
        f"expected={expected_install_mode} actual={actual_install_mode}",
    )

    sdf_ready = bool(smart_driver_state.get("ready"))
    kernel_handoff_ready = bool((smart_driver_kernel_handoff.get("payload") or {}).get("ready") == 1)
    mark(
        "PASS_SMART_DRIVER_HANDOFF_READY",
        sdf_ready and kernel_handoff_ready,
        "FIRMWARE_OS_HANDOFF_SMART_DRIVER_NOT_READY",
        f"smart_driver_state.ready={sdf_ready} kernel_handoff.ready={kernel_handoff_ready}",
    )

    hw_guard_policy = parallel_policy.get("hardwareGuard") or {}
    handoff_guard = handoff.get("parallel_cubed_hardware_guard") or {}
    report_payload = hardware_guard_report.get("payload") or {}
    guard_ok = (
        bool(hw_guard_policy.get("enabled", False))
        and bool(hw_guard_policy.get("strictMode", False))
        and bool(handoff_guard.get("enabled", False))
        and bool(handoff_guard.get("strict_mode", False))
        and int(report_payload.get("enabled", 0)) == 1
        and int(report_payload.get("strict_mode", 0)) == 1
    )
    mark(
        "PASS_PARALLEL_CUBED_HARDWARE_GUARD_ACTIVE",
        guard_ok,
        "FIRMWARE_OS_HANDOFF_PARALLEL_GUARD_INACTIVE",
        "parallel cubed hardware guard policy/report/handoff not all strict+enabled",
    )

    inventory_manifest_path = str((handoff.get("inventory") or {}).get("manifest_path") or "").strip()
    inventory_exists = bool(inventory_manifest_path) and Path(inventory_manifest_path).exists()
    mark(
        "PASS_INVENTORY_EXISTS_BEFORE_SMART_WRITE",
        inventory_exists,
        "FIRMWARE_OS_HANDOFF_INVENTORY_MISSING",
        f"inventory manifest not found: {inventory_manifest_path}",
    )

    bios_pending = ((handoff.get("firmware_runtime") or {}).get("bios_settings_pending") or {})
    bios_mode = str((contract.get("sharedContracts") or {}).get("biosSettingsApplyMode") or "").strip().lower()
    if bios_mode == "pending_restart_only" and isinstance(bios_pending, dict) and bool(bios_pending.get("present")):
        restart_semantics_ok = bool(bios_pending.get("apply_after_restart")) and str(bios_pending.get("status") or "").upper() == "PENDING_RESTART"
    else:
        restart_semantics_ok = True
    mark(
        "PASS_BIOS_SETTINGS_APPLY_AFTER_RESTART",
        restart_semantics_ok,
        "FIRMWARE_OS_HANDOFF_BIOS_SETTINGS_RESTART_POLICY_VIOLATION",
        "pending BIOS settings must remain PENDING_RESTART with apply_after_restart=true",
    )

    rewrite_engine = (handoff.get("firmware_runtime") or {}).get("rewrite_engine") or {}
    rewrite_guard_ok = True
    rewrite_adapter_ok = True
    if isinstance(rewrite_engine, dict) and rewrite_engine:
        rewrite_guard_ok = bool(rewrite_engine.get("backup_required", False)) and bool(
            rewrite_engine.get("ab_slot_rollback_required", False)
        )
        contract_rewrite = (contract.get("sharedContracts") or {}).get("rewriteEngine") or {}
        allowed = {str(x) for x in (contract_rewrite.get("allowedAdapters") or []) if str(x).strip()}
        plan_path = str(rewrite_engine.get("rewrite_plan_path") or "").strip()
        if allowed and plan_path and Path(plan_path).exists():
            plan_obj = load_json(Path(plan_path), {})
            adapter_id = str(((plan_obj.get("rewrite_adapter") or {}).get("adapter_id") or "")).strip()
            rewrite_adapter_ok = bool(adapter_id) and adapter_id in allowed
    mark(
        "PASS_REWRITE_ENGINE_BACKUP_AND_AB_GUARDS",
        rewrite_guard_ok,
        "FIRMWARE_OS_HANDOFF_REWRITE_ENGINE_GUARD_MISSING",
        "rewrite engine metadata must enforce backup_required and ab_slot_rollback_required",
    )
    mark(
        "PASS_REWRITE_ADAPTER_ALLOWED_BY_CONTRACT",
        rewrite_adapter_ok,
        "FIRMWARE_OS_HANDOFF_REWRITE_ADAPTER_NOT_ALLOWED",
        "rewrite adapter is not in contract rewriteEngine.allowedAdapters",
    )

    return {
        "checks": checks,
        "failures": failures,
        "missing_artifacts": missing_artifacts,
        "missing_services": missing_services,
        "missing_driver_classes": missing_classes,
    }


def run_enforcement(
    *,
    contract_path: Path,
    handoff_path: Path,
    firmware_manifest_path: Path | None,
    smart_driver_state_path: Path,
    smart_driver_kernel_handoff_path: Path,
    parallel_policy_path: Path,
    hardware_guard_report_path: Path,
) -> dict[str, Any]:
    contract = load_json(contract_path, {})
    handoff = load_json(handoff_path, {})
    smart_driver_state = load_json(smart_driver_state_path, {})
    smart_driver_kernel_handoff = load_json(smart_driver_kernel_handoff_path, {})
    parallel_policy = load_json(parallel_policy_path, {})
    hardware_guard_report = load_json(hardware_guard_report_path, {})

    firmware_manifest = load_json(firmware_manifest_path, {}) if firmware_manifest_path else {}

    ev = evaluate_handoff(
        contract=contract if isinstance(contract, dict) else {},
        handoff=handoff if isinstance(handoff, dict) else {},
        firmware_manifest=firmware_manifest if isinstance(firmware_manifest, dict) else {},
        smart_driver_state=smart_driver_state if isinstance(smart_driver_state, dict) else {},
        smart_driver_kernel_handoff=smart_driver_kernel_handoff if isinstance(smart_driver_kernel_handoff, dict) else {},
        parallel_policy=parallel_policy if isinstance(parallel_policy, dict) else {},
        hardware_guard_report=hardware_guard_report if isinstance(hardware_guard_report, dict) else {},
    )

    failures = ev["failures"]
    status = "FAIL" if failures else "PASS"
    report = {
        "timestamp_utc": now_iso(),
        "contract_id": "firmware_os_handoff_enforcement_integrity",
        "status": status,
        "audit_path": str(AUDIT_PATH),
        "smoke_path": str(SMOKE_PATH),
        "contract_path": str(contract_path),
        "handoff_path": str(handoff_path),
        "firmware_manifest_path": str(firmware_manifest_path) if firmware_manifest_path else None,
        "smart_driver_state_path": str(smart_driver_state_path),
        "smart_driver_kernel_handoff_path": str(smart_driver_kernel_handoff_path),
        "parallel_policy_path": str(parallel_policy_path),
        "hardware_guard_report_path": str(hardware_guard_report_path),
        "checks": ev["checks"],
        "failures": failures,
        "failure_count": len(failures),
    }
    return report


def main() -> None:
    workspace_root = resolve_workspace_root()
    fw_base = workspace_root / "AxionFW" / "Base"

    parser = argparse.ArgumentParser(description="Enforce firmware<->OS handoff contract")
    parser.add_argument("--contract-path", default=str(AXION_ROOT / "config" / "FIRMWARE_OS_HARDWARE_CONTRACT_V1.json"))
    parser.add_argument("--handoff-path", default=str(fw_base / "out" / "handoff" / "firmware_os_handoff_v1.json"))
    parser.add_argument("--firmware-manifest-path", default="")
    parser.add_argument("--smart-driver-state-path", default=str(AXION_ROOT / "data" / "drivers" / "smart_driver_fabric_state.json"))
    parser.add_argument("--smart-driver-kernel-handoff-path", default=str(AXION_ROOT / "out" / "runtime" / "smart_driver_kernel_handoff.json"))
    parser.add_argument("--parallel-policy-path", default=str(AXION_ROOT / "config" / "PARALLEL_CUBED_SANDBOX_DOMAINS_V1.json"))
    parser.add_argument("--hardware-guard-report-path", default=str(AXION_ROOT / "out" / "runtime" / "parallel_cubed_hardware_guard.json"))
    args = parser.parse_args()

    contract_path = Path(args.contract_path).resolve()
    handoff_path = Path(args.handoff_path).resolve()

    firmware_manifest_path: Path | None
    if str(args.firmware_manifest_path).strip():
        firmware_manifest_path = Path(args.firmware_manifest_path).resolve()
    else:
        firmware_manifest_path = resolve_latest_firmware_manifest(fw_base)

    report = run_enforcement(
        contract_path=contract_path,
        handoff_path=handoff_path,
        firmware_manifest_path=firmware_manifest_path,
        smart_driver_state_path=Path(args.smart_driver_state_path).resolve(),
        smart_driver_kernel_handoff_path=Path(args.smart_driver_kernel_handoff_path).resolve(),
        parallel_policy_path=Path(args.parallel_policy_path).resolve(),
        hardware_guard_report_path=Path(args.hardware_guard_report_path).resolve(),
    )

    AUDIT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    SMOKE_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))

    if report["status"] != "PASS":
        raise SystemExit(1)
    raise SystemExit(0)


if __name__ == "__main__":
    main()
