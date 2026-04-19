from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
#!/usr/bin/env python3
import json
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(axion_path_str())
OUT = ROOT / "out" / "runtime"
OUT.mkdir(parents=True, exist_ok=True)
AUD = OUT / "real_hardware_bringup_readiness_audit.json"
SMK = OUT / "real_hardware_bringup_readiness_smoke.json"

HAL = ROOT / "config" / "AXION_HAL_PROFILE_V1.json"
BSP = ROOT / "config" / "BOARD_SUPPORT_PACKAGE_CATALOG_V1.json"
LADDER = ROOT / "config" / "REAL_HARDWARE_BRINGUP_LADDER_V1.json"
COLLECTOR = ROOT / "tools" / "hardware" / "collect_windows_hardware_inventory.ps1"
STRATEGY = ROOT / "design" / "platform" / "AXION_REAL_HARDWARE_BRINGUP_STRATEGY_V1.md"


def now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main():
    failures = []
    hal = load(HAL)
    bsp = load(BSP)
    ladder = load(LADDER)

    ref_ids = {entry.get("platform_id") for entry in hal.get("referencePlatforms", [])}
    if "hp_9470m_9480m_bridge" not in ref_ids:
        failures.append({"code": "REAL_HW_HP_REFERENCE_PLATFORM_MISSING", "detail": sorted(ref_ids)})

    bsp_ids = {entry.get("bsp_id") for entry in bsp.get("packages", [])}
    for needed in {"bsp_generic_x64_uefi_v1", "bsp_hp_9470m_9480m_bridge_v1"}:
        if needed not in bsp_ids:
            failures.append({"code": "REAL_HW_BSP_MISSING", "detail": needed})

    phases = {entry.get("phase_id") for entry in ladder.get("phases", [])}
    for needed_phase in {"q35_reference", "first_real_laptop_family", "generic_x64_laptop_broadening", "generic_x64_tower_broadening"}:
        if needed_phase not in phases:
            failures.append({"code": "REAL_HW_PHASE_MISSING", "detail": needed_phase})

    policy = ladder.get("policy", {})
    if not policy.get("generic_end_state"):
        failures.append({"code": "REAL_HW_GENERIC_DESTINATION_LOST", "detail": policy})

    if not COLLECTOR.exists():
        failures.append({"code": "REAL_HW_WINDOWS_INVENTORY_TOOL_MISSING", "detail": str(COLLECTOR)})

    if not STRATEGY.exists():
        failures.append({"code": "REAL_HW_STRATEGY_DOC_MISSING", "detail": str(STRATEGY)})

    status = "FAIL" if failures else "PASS"
    result = {
        "contract_id": "real_hardware_bringup_readiness",
        "timestamp_utc": now(),
        "status": status,
        "audit_path": str(AUD),
        "smoke_path": str(SMK),
        "checks": {
            "PASS_HAL_PROFILE_PRESENT": HAL.exists(),
            "PASS_BSP_CATALOG_PRESENT": BSP.exists(),
            "PASS_BRINGUP_LADDER_PRESENT": LADDER.exists(),
            "PASS_WINDOWS_INVENTORY_TOOL_PRESENT": COLLECTOR.exists(),
            "PASS_STRATEGY_DOC_PRESENT": STRATEGY.exists()
        },
        "failures": failures
    }
    AUD.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    SMK.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    raise SystemExit(1 if failures else 0)


if __name__ == "__main__":
    main()

