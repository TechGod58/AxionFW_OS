#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
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


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def workspace_root_from_script(script_path: Path) -> Path:
    # .../AxionFW/Base/scripts/20_policy_plan.py -> .../AxionFW_OS
    return script_path.resolve().parents[3]


def fw_base_from_script(script_path: Path) -> Path:
    # .../AxionFW/Base
    return script_path.resolve().parents[1]


def find_latest_manifest(manifest_dir: Path) -> Path:
    items = sorted(manifest_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not items:
        raise FileNotFoundError(f"No inventory manifests found in {manifest_dir}")
    return items[0]


def text_contains_any(text: str, needles: list[str]) -> bool:
    low = (text or "").strip().lower()
    if not low:
        return False
    for n in needles:
        if n.lower() in low:
            return True
    return False


def choose_profile(profiles_cfg: dict[str, Any], inventory: dict[str, Any]) -> dict[str, Any]:
    profiles = profiles_cfg.get("profiles") or []
    default_id = str(profiles_cfg.get("default_profile") or "")

    cs = inventory.get("inventory", {}).get("computer_system", {}) or {}
    model = str(cs.get("Model") or "")
    manufacturer = str(cs.get("Manufacturer") or "")

    default_profile = None
    for p in profiles:
        if str(p.get("id") or "") == default_id:
            default_profile = p
            break

    for p in profiles:
        match = p.get("match", {}) or {}
        model_needles = list(match.get("model_contains") or [])
        manufacturer_needles = list(match.get("manufacturer_contains") or [])

        model_ok = True if not model_needles else text_contains_any(model, model_needles)
        manufacturer_ok = True if not manufacturer_needles else text_contains_any(manufacturer, manufacturer_needles)
        if model_ok and manufacturer_ok:
            return p

    if default_profile is not None:
        return default_profile

    if profiles:
        return profiles[0]

    raise RuntimeError("No firmware policy profiles are defined")


def discover_qm_constellation_sources(workspace_root: Path) -> dict[str, Any]:
    qm_root = workspace_root / "_imports" / "AxionQM"
    cm_root = workspace_root / "_imports" / "axion_constellation_memory"

    qm_hardware_binding = qm_root / "AxionQM" / "AxionE" / "README_BATCH30_HARDWARE_BINDING.txt"
    qm_hardware_loop = qm_root / "AxionQM" / "AxionE" / "axione" / "runtime" / "loop_hardware.py"
    constellation_runtime = cm_root / "axion_constellation_memory" / "parallel_cubed_runtime.py"
    constellation_api = cm_root / "axion_constellation_memory" / "axion_parallel_cubed_api.py"
    constellation_genome = cm_root / "axion_constellation_memory" / "parallel_cubed_region_genome.json"

    out = {
        "qm": {
            "zip_root": str(qm_root),
            "hardware_binding_readme": str(qm_hardware_binding),
            "hardware_loop": str(qm_hardware_loop),
            "available": qm_hardware_binding.exists() and qm_hardware_loop.exists(),
        },
        "constellation_memory": {
            "zip_root": str(cm_root),
            "runtime": str(constellation_runtime),
            "api": str(constellation_api),
            "genome": str(constellation_genome),
            "available": constellation_runtime.exists() and constellation_api.exists(),
        },
    }

    if constellation_genome.exists():
        out["constellation_memory"]["genome_sha256"] = sha256_file(constellation_genome)

    return out


def firmware_artifact_summary(fw_base: Path) -> dict[str, Any]:
    out_root = fw_base / "out"
    manifests = sorted(out_root.glob("**/manifest.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not manifests:
        return {"available": False, "latest_manifest": None, "files": []}

    latest = manifests[0]
    data = load_json(latest, {})
    files = list(data.get("files") or []) if isinstance(data, dict) else []
    return {
        "available": True,
        "latest_manifest": str(latest),
        "files": files,
        "profile": str(data.get("profile") or ""),
        "version": str(data.get("version") or ""),
    }


def build_plan(
    fw_base: Path,
    inventory_path: Path,
    inventory: dict[str, Any],
    profiles_cfg: dict[str, Any],
) -> dict[str, Any]:
    workspace_root = fw_base.parent.parent
    selected = choose_profile(profiles_cfg, inventory)
    sources = discover_qm_constellation_sources(workspace_root)
    fw_artifacts = firmware_artifact_summary(fw_base)

    counts = inventory.get("counts", {}) or {}
    machine_id = str(inventory.get("machine_id") or "unknown_machine")

    required_artifacts = list(selected.get("required_firmware_artifacts") or [])
    available_files = {str(x) for x in fw_artifacts.get("files") or []}
    missing_required_artifacts = [x for x in required_artifacts if x not in available_files]

    guard = selected.get("parallel_cubed_guard", {}) or {}

    return {
        "version": 1,
        "policy_id": str(profiles_cfg.get("policy_id") or "AXION_FW_POLICY_EXECUTOR_V1"),
        "generated_utc": now_iso(),
        "machine_id": machine_id,
        "mode": "emulation_only_no_flash",
        "inventory_manifest_path": str(inventory_path),
        "inventory_manifest_sha256": sha256_file(inventory_path),
        "inventory_summary": {
            "pci_devices": int(counts.get("pci_devices") or 0),
            "acpi_devices": int(counts.get("acpi_devices") or 0),
            "usb_devices": int(counts.get("usb_devices") or 0),
            "disk_drives": int(counts.get("disk_drives") or 0),
        },
        "selected_profile": {
            "id": str(selected.get("id") or "unknown_profile"),
            "firmware_profile": str(selected.get("firmware_profile") or "axionfw_generic_x64_safe"),
            "driver_profile": str(selected.get("driver_profile") or "axionos_capsule_generic_x64"),
            "required_firmware_artifacts": required_artifacts,
            "required_services": list(selected.get("required_services") or []),
            "missing_required_artifacts": missing_required_artifacts,
        },
        "driver_binding_contract": {
            "path": "engine_backend_driver_hardware",
            "qm_source": "axionqm_clean_with_external_binding_option",
            "parallel_cubed_source": "axion_constellation_memory_external_runtime",
        },
        "external_sources": sources,
        "parallel_cubed_hardware_guard": {
            "strict_mode": bool(guard.get("strict_mode", True)),
            "allow_bus_classes": list(guard.get("allow_bus_classes") or [1, 2, 6]),
            "deny_bus_classes": list(guard.get("deny_bus_classes") or [12, 13]),
            "inventory_required_before_smart_write": True,
        },
        "firmware_artifact_summary": fw_artifacts,
        "execution_stages": [
            {"stage": "inventory_capture", "status": "PASS"},
            {"stage": "profile_selection", "status": "PASS"},
            {
                "stage": "artifact_presence",
                "status": "PASS" if len(missing_required_artifacts) == 0 else "WARN",
                "missing": missing_required_artifacts,
            },
            {"stage": "physical_write", "status": "SKIPPED", "reason": "no_physical_flash_guard"},
        ],
        "guardrails": {
            "no_physical_flash": True,
            "rollback_metadata_required_for_future_write": True,
            "inventory_before_smart_write": True,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate firmware policy plan from inventory")
    parser.add_argument("--inventory", default="", help="Path to inventory manifest json. Defaults to latest in out/manifests")
    parser.add_argument("--profiles", default="", help="Path to firmware policy profiles json")
    parser.add_argument("--out", default="", help="Output plan path")
    args = parser.parse_args()

    script = Path(__file__).resolve()
    fw_base = fw_base_from_script(script)

    manifest_dir = fw_base / "out" / "manifests"
    inventory_path = Path(args.inventory).resolve() if str(args.inventory).strip() else find_latest_manifest(manifest_dir)
    inventory = load_json(inventory_path, {})
    if not isinstance(inventory, dict) or not inventory:
        raise SystemExit(f"Invalid or empty inventory manifest: {inventory_path}")

    profiles_path = (
        Path(args.profiles).resolve()
        if str(args.profiles).strip()
        else (fw_base / "policy" / "firmware_policy_profiles.json")
    )
    profiles_cfg = load_json(profiles_path, {})
    if not isinstance(profiles_cfg, dict) or not profiles_cfg:
        raise SystemExit(f"Invalid or empty policy profile file: {profiles_path}")

    plan = build_plan(fw_base, inventory_path, inventory, profiles_cfg)
    machine_id = str(plan.get("machine_id") or "unknown_machine")
    plans_dir = fw_base / "out" / "plans"
    plans_dir.mkdir(parents=True, exist_ok=True)

    out_path = (
        Path(args.out).resolve()
        if str(args.out).strip()
        else plans_dir / f"{machine_id}.plan.json"
    )
    out_path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")

    latest = plans_dir / "latest.plan.json"
    latest.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")

    result = {
        "ok": True,
        "code": "AXION_FW_POLICY_PLAN_READY",
        "inventory_path": str(inventory_path),
        "profiles_path": str(profiles_path),
        "plan_path": str(out_path),
        "latest_plan_path": str(latest),
        "machine_id": machine_id,
        "selected_profile": plan.get("selected_profile", {}).get("id"),
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
