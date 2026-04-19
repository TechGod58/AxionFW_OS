from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
#!/usr/bin/env python3
import json
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(axion_path_str())
OUT = ROOT / "out" / "runtime"
OUT.mkdir(parents=True, exist_ok=True)
AUD = OUT / "reference_bsp_q35_driver_readiness_audit.json"
SMK = OUT / "reference_bsp_q35_driver_readiness_smoke.json"

CATALOG = ROOT / "config" / "DEVICE_DRIVER_CATALOG_V1.json"
BSP = ROOT / "config" / "BOARD_SUPPORT_PACKAGE_CATALOG_V1.json"


def now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def main():
    failures = []
    catalog = json.loads(CATALOG.read_text(encoding="utf-8-sig"))
    bsp = json.loads(BSP.read_text(encoding="utf-8-sig"))
    present = {entry.get("driver_id") for entry in catalog.get("drivers", [])}
    required = {
        "drv_mb_q35_acpi",
        "drv_mb_ich9_lpc",
        "drv_pci_net_e1000",
        "drv_storage_virtio_blk_modern",
        "drv_sbx_profile_persist_bridge"
    }
    missing = sorted(required - present)
    if missing:
        failures.append({"code": "REFERENCE_BSP_Q35_DRIVERS_MISSING", "detail": missing})

    bsp_ids = {entry.get("bsp_id") for entry in bsp.get("packages", [])}
    if "bsp_q35_ovmf_ref_v1" not in bsp_ids:
        failures.append({"code": "REFERENCE_BSP_Q35_CATALOG_MISSING", "detail": sorted(bsp_ids)})

    status = "FAIL" if failures else "PASS"
    result = {
        "contract_id": "reference_bsp_q35_driver_readiness",
        "timestamp_utc": now(),
        "status": status,
        "audit_path": str(AUD),
        "smoke_path": str(SMK),
        "failures": failures
    }
    AUD.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    SMK.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    raise SystemExit(1 if failures else 0)


if __name__ == "__main__":
    main()

