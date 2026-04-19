from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
#!/usr/bin/env python3
import json
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(axion_path_str())
OUT = ROOT / "out" / "runtime"
OUT.mkdir(parents=True, exist_ok=True)
AUD = OUT / "axion_hal_platform_readiness_audit.json"
SMK = OUT / "axion_hal_platform_readiness_smoke.json"

HAL = ROOT / "config" / "AXION_HAL_PROFILE_V1.json"
BSP = ROOT / "config" / "BOARD_SUPPORT_PACKAGE_CATALOG_V1.json"
CONTRACT = ROOT / "config" / "FIRMWARE_OS_HARDWARE_CONTRACT_V1.json"
BUNDLE = ROOT / "tools" / "packaging" / "build_unified_axion_stack_bundle.ps1"
DRIVERKIT = ROOT / "tools" / "driverkit" / "create_driver_bundle.py"


def now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main():
    failures = []
    hal = load(HAL)
    bsp = load(BSP)
    contract = load(CONTRACT)

    required_classes = {"firmware_handoff", "motherboard_core", "device_io", "security_trust", "sandbox_mediation"}
    found_classes = {entry["class_id"] for entry in hal.get("driverClasses", [])}
    if found_classes != required_classes:
        failures.append({"code": "AXION_HAL_DRIVER_CLASS_MISMATCH", "detail": sorted(found_classes)})

    bsp_ids = {entry["bsp_id"] for entry in bsp.get("packages", [])}
    if "bsp_q35_ovmf_ref_v1" not in bsp_ids:
        failures.append({"code": "AXION_HAL_REFERENCE_BSP_MISSING", "detail": sorted(bsp_ids)})

    sec = contract.get("firmware", {}).get("securityRequirements", {})
    if not (sec.get("measuredBoot") and sec.get("secureBootPolicyPresent")):
        failures.append({"code": "AXION_HAL_TRUST_CHAIN_INCOMPLETE", "detail": sec})

    if not BUNDLE.exists():
        failures.append({"code": "AXION_HAL_UNIFIED_BUNDLE_TOOL_MISSING", "detail": str(BUNDLE)})

    if not DRIVERKIT.exists():
        failures.append({"code": "AXION_HAL_DRIVERKIT_MISSING", "detail": str(DRIVERKIT)})

    status = "FAIL" if failures else "PASS"
    result = {
      "contract_id": "axion_hal_platform_readiness",
      "timestamp_utc": now(),
      "status": status,
      "audit_path": str(AUD),
      "smoke_path": str(SMK),
      "checks": {
        "PASS_HAL_PROFILE_PRESENT": HAL.exists(),
        "PASS_BSP_CATALOG_PRESENT": BSP.exists(),
        "PASS_FW_OS_CONTRACT_PRESENT": CONTRACT.exists(),
        "PASS_UNIFIED_BUNDLE_TOOL_PRESENT": BUNDLE.exists(),
        "PASS_DRIVERKIT_PRESENT": DRIVERKIT.exists()
      },
      "failures": failures
    }
    AUD.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    SMK.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    raise SystemExit(1 if failures else 0)


if __name__ == "__main__":
    main()

