#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path, default: Any):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return default


def fw_base_from_script(script_path: Path) -> Path:
    return script_path.resolve().parents[1]


def workspace_root_from_fw_base(fw_base: Path) -> Path:
    return fw_base.parent.parent


def find_latest_plan(plans_dir: Path) -> Path:
    latest = plans_dir / "latest.plan.json"
    if latest.exists():
        return latest
    items = sorted(plans_dir.glob("*.plan.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not items:
        raise FileNotFoundError(f"No plan files found in {plans_dir}")
    return items[0]


def find_latest_firmware_manifest(fw_base: Path) -> Path | None:
    manifests = sorted((fw_base / "out").glob("**/manifest.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    return manifests[0] if manifests else None


def resolve_contract_path(workspace_root: Path) -> Path:
    return workspace_root / "AxionOS" / "config" / "FIRMWARE_OS_HARDWARE_CONTRACT_V1.json"


def resolve_pending_bios_settings_path(fw_base: Path) -> Path:
    return fw_base / "out" / "handoff" / "pending_bios_settings_v1.json"


def resolve_latest_rewrite_artifact(fw_base: Path, filename: str) -> Path | None:
    direct = fw_base / "out" / "rewrite" / filename
    if direct.exists():
        return direct
    candidates = sorted((fw_base / "out" / "rewrite").glob(f"**/{filename}"), key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0] if candidates else None


def build_handoff(
    workspace_root: Path,
    fw_base: Path,
    plan_path: Path,
    plan: dict[str, Any],
    contract: dict[str, Any],
    firmware_manifest_path: Path | None,
    pending_bios_settings_path: Path,
    pending_bios_settings: dict[str, Any],
    rewrite_graph_path: Path | None,
    rewrite_plan_path: Path | None,
    rewrite_signature_path: Path | None,
    rewrite_execution_path: Path | None,
) -> dict[str, Any]:
    firmware_manifest = load_json(firmware_manifest_path, {}) if firmware_manifest_path else {}
    rewrite_plan = load_json(rewrite_plan_path, {}) if rewrite_plan_path else {}
    selected = plan.get("selected_profile", {}) or {}
    rewrite_exec_policy = (
        rewrite_plan.get("execution_policy", {})
        if isinstance(rewrite_plan, dict) and isinstance(rewrite_plan.get("execution_policy"), dict)
        else {}
    )
    physical_mode = str(rewrite_exec_policy.get("physical_flash_mode") or "").strip()
    physical_enabled = bool(rewrite_exec_policy.get("allow_physical_flash", False))
    write_mode = "controlled_physical_flash_fail_closed" if (physical_enabled and physical_mode == "controlled_fail_closed") else "no_physical_flash"

    required_artifacts = list(contract.get("firmware", {}).get("requiredArtifacts") or [])
    available_artifacts = list((firmware_manifest or {}).get("files") or [])
    missing_artifacts = [x for x in required_artifacts if x not in set(available_artifacts)]

    handoff = {
        "version": 1,
        "contract_id": str(contract.get("contractId") or "AXION_FIRMWARE_OS_HARDWARE_CONTRACT_V1"),
        "generated_utc": now_iso(),
        "source": "AxionFW/Base/scripts/30_emit_os_handoff.py",
        "plan_path": str(plan_path),
        "workspace_root": str(workspace_root),
        "driver_install_mode": str(contract.get("os", {}).get("driverInstallMode") or "firmware_first_os_second"),
        "inventory": {
            "manifest_path": str(plan.get("inventory_manifest_path") or ""),
            "manifest_sha256": str(plan.get("inventory_manifest_sha256") or ""),
            "summary": dict(plan.get("inventory_summary") or {}),
        },
        "firmware_runtime": {
            "profile": str(selected.get("firmware_profile") or "axionfw_generic_x64_safe"),
            "manifest_path": str(firmware_manifest_path) if firmware_manifest_path else None,
            "services": list(contract.get("firmware", {}).get("requiredServices") or []),
            "artifacts_required": required_artifacts,
            "artifacts_available": available_artifacts,
            "artifacts_missing": missing_artifacts,
            "write_mode": write_mode,
            "bios_settings_pending": {
                "present": bool(isinstance(pending_bios_settings, dict) and pending_bios_settings),
                "path": str(pending_bios_settings_path),
                "status": str((pending_bios_settings or {}).get("status") or "NONE"),
                "apply_after_restart": bool((pending_bios_settings or {}).get("apply_after_restart", True)),
                "request_id": str((pending_bios_settings or {}).get("request_id") or ""),
                "settings": dict((pending_bios_settings or {}).get("settings") or {}),
            },
            "rewrite_engine": {
                "capability_graph_path": str(rewrite_graph_path) if rewrite_graph_path else None,
                "rewrite_plan_path": str(rewrite_plan_path) if rewrite_plan_path else None,
                "rewrite_signature_path": str(rewrite_signature_path) if rewrite_signature_path else None,
                "rewrite_execution_report_path": str(rewrite_execution_path) if rewrite_execution_path else None,
                "backup_required": True,
                "ab_slot_rollback_required": True,
                "physical_flash_mode": physical_mode or None,
                "physical_flash_policy_path": str(((rewrite_plan.get("physical_flash_executor") or {}).get("policy_path") or "")) if isinstance(rewrite_plan, dict) else None,
            },
        },
        "os_runtime": {
            "profile": str(selected.get("driver_profile") or "axionos_capsule_generic_x64"),
            "required_consumers": list(contract.get("os", {}).get("requiredConsumers") or []),
            "smart_driver_fabric_contract": "smart_driver_fabric_v1",
        },
        "parallel_cubed_hardware_guard": {
            "enabled": True,
            "strict_mode": bool((plan.get("parallel_cubed_hardware_guard") or {}).get("strict_mode", True)),
            "allow_bus_classes": list((plan.get("parallel_cubed_hardware_guard") or {}).get("allow_bus_classes") or [1, 2, 6]),
            "deny_bus_classes": list((plan.get("parallel_cubed_hardware_guard") or {}).get("deny_bus_classes") or [12, 13]),
            "inventory_required_before_smart_write": True,
        },
        "qm_binding": dict((plan.get("external_sources") or {}).get("qm") or {}),
        "constellation_memory_binding": dict((plan.get("external_sources") or {}).get("constellation_memory") or {}),
        "status": "READY_WITH_WARNINGS" if missing_artifacts else "READY",
    }
    return handoff


def main() -> None:
    parser = argparse.ArgumentParser(description="Emit firmware->OS handoff artifact")
    parser.add_argument("--plan", default="", help="Path to policy plan json")
    parser.add_argument("--contract", default="", help="Path to firmware/os contract json")
    parser.add_argument("--out", default="", help="Output handoff path")
    args = parser.parse_args()

    script = Path(__file__).resolve()
    fw_base = fw_base_from_script(script)
    workspace_root = workspace_root_from_fw_base(fw_base)

    plans_dir = fw_base / "out" / "plans"
    plan_path = Path(args.plan).resolve() if str(args.plan).strip() else find_latest_plan(plans_dir)
    plan = load_json(plan_path, {})
    if not isinstance(plan, dict) or not plan:
        raise SystemExit(f"Invalid plan file: {plan_path}")

    contract_path = (
        Path(args.contract).resolve() if str(args.contract).strip() else resolve_contract_path(workspace_root)
    )
    contract = load_json(contract_path, {})
    if not isinstance(contract, dict) or not contract:
        raise SystemExit(f"Invalid contract file: {contract_path}")

    firmware_manifest_path = find_latest_firmware_manifest(fw_base)
    pending_bios_settings_path = resolve_pending_bios_settings_path(fw_base)
    pending_bios_settings = load_json(pending_bios_settings_path, {})
    if not isinstance(pending_bios_settings, dict):
        pending_bios_settings = {}
    rewrite_graph_path = resolve_latest_rewrite_artifact(fw_base, "capability_graph_v1.json")
    rewrite_plan_path = resolve_latest_rewrite_artifact(fw_base, "rewrite_plan_v1.json")
    rewrite_signature_path = resolve_latest_rewrite_artifact(fw_base, "rewrite_signature_v1.json")
    rewrite_execution_path = resolve_latest_rewrite_artifact(fw_base, "rewrite_execution_report.json")
    handoff = build_handoff(
        workspace_root,
        fw_base,
        plan_path,
        plan,
        contract,
        firmware_manifest_path,
        pending_bios_settings_path,
        pending_bios_settings,
        rewrite_graph_path,
        rewrite_plan_path,
        rewrite_signature_path,
        rewrite_execution_path,
    )

    out_path = (
        Path(args.out).resolve()
        if str(args.out).strip()
        else (fw_base / "out" / "handoff" / "firmware_os_handoff_v1.json")
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(handoff, indent=2) + "\n", encoding="utf-8")

    result = {
        "ok": True,
        "code": "AXION_FW_OS_HANDOFF_READY",
        "plan_path": str(plan_path),
        "contract_path": str(contract_path),
        "firmware_manifest_path": str(firmware_manifest_path) if firmware_manifest_path else None,
        "handoff_path": str(out_path),
        "status": handoff.get("status"),
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
