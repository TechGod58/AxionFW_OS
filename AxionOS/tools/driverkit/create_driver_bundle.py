#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[1]
if str(TOOLS_DIR) not in sys.path:
    sys.path.append(str(TOOLS_DIR))

from common.pathing import axion_path


def build_manifest(driver_id: str, driver_class: str, target_family: str, output_dir: Path):
    return {
        "driver_id": driver_id,
        "driver_class": driver_class,
        "target_family": target_family,
        "version": "0.1.0",
        "package_kind": "axionhal_driver_bundle",
        "install_target": "safe://system/drivers" if driver_class != "sandbox_mediation" else "safe://system/drivers/sandbox",
        "artifacts": {
            "source_root": str(output_dir / "src"),
            "tests_root": str(output_dir / "tests"),
            "docs_root": str(output_dir / "docs")
        },
        "signing": {
            "required": True,
            "policy": "device_driver_runtime_policy_integrity"
        }
    }


def create_bundle(root: Path, driver_id: str, driver_class: str, target_family: str):
    bundle_dir = root / driver_id
    for child in ("src", "tests", "docs"):
        (bundle_dir / child).mkdir(parents=True, exist_ok=True)

    manifest = build_manifest(driver_id, driver_class, target_family, bundle_dir)
    (bundle_dir / "bundle_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (bundle_dir / "src" / "README.md").write_text(f"# {driver_id}\n\nAxionHAL driver scaffold for `{driver_class}` on `{target_family}`.\n", encoding="utf-8")
    (bundle_dir / "tests" / "smoke_test.md").write_text("Add bring-up, negative-control, and signing verification checks here.\n", encoding="utf-8")
    (bundle_dir / "docs" / "integration.md").write_text("Document firmware dependencies, board assumptions, and sandbox exposure rules here.\n", encoding="utf-8")
    return bundle_dir


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--driver-id", required=True)
    ap.add_argument("--driver-class", required=True)
    ap.add_argument("--target-family", required=True)
    ap.add_argument("--root", default=str(axion_path("data", "driverkit")))
    args = ap.parse_args()
    bundle_dir = create_bundle(Path(args.root), args.driver_id, args.driver_class, args.target_family)
    print(json.dumps({"ok": True, "bundle_dir": str(bundle_dir)}, indent=2))


if __name__ == "__main__":
    main()
