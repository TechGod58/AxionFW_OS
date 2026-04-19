from __future__ import annotations

import hashlib
import json
import re
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_TOOLS_DIR = None
for _parent in Path(__file__).resolve().parents:
    if (_parent / "tools" / "common" / "pathing.py").exists():
        _TOOLS_DIR = _parent / "tools"
        break
if _TOOLS_DIR and str(_TOOLS_DIR) not in sys.path:
    sys.path.append(str(_TOOLS_DIR))

from common.pathing import axion_path


def axion_path_str(*parts: str) -> str:
    return str(axion_path(*parts))


DRIVERKIT_DIR = Path(axion_path_str("tools", "driverkit"))
if str(DRIVERKIT_DIR) not in sys.path:
    sys.path.append(str(DRIVERKIT_DIR))

try:
    from create_driver_bundle import create_bundle as _create_driver_bundle
except Exception:
    _create_driver_bundle = None
try:
    from driver_artifact_compiler import compile_smart_fabric_artifacts
except Exception:
    compile_smart_fabric_artifacts = None


AXION_ROOT = Path(axion_path_str())
CONFIG_PATH = Path(axion_path_str("config", "SMART_DRIVER_FABRIC_V1.json"))
HAL_PATH = Path(axion_path_str("config", "AXION_HAL_PROFILE_V1.json"))
BSP_PATH = Path(axion_path_str("config", "BOARD_SUPPORT_PACKAGE_CATALOG_V1.json"))
CONTRACT_PATH = Path(axion_path_str("config", "FIRMWARE_OS_HARDWARE_CONTRACT_V1.json"))
DRIVER_CATALOG_PATH = Path(axion_path_str("config", "DEVICE_DRIVER_CATALOG_V1.json"))

_PCI_RE = re.compile(r"VEN_([0-9A-F]{4}).*DEV_([0-9A-F]{4})", re.IGNORECASE)
_USB_RE = re.compile(r"VID_([0-9A-F]{4}).*PID_([0-9A-F]{4})", re.IGNORECASE)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_config() -> dict[str, Any]:
    return {
        "version": 1,
        "fabric_id": "AXION_SMART_DRIVER_FABRIC_V1",
        "enabled": True,
        "one_time_bootstrap": True,
        "fail_closed_on_error": False,
        "target_bsp_id": "bsp_q35_ovmf_ref_v1",
        "materialize_missing_required_classes": True,
        "compile_signed_loadable_artifacts": True,
        "inventory_sources": [
            "out/hardware_inventory/windows_hardware_inventory.json",
            "data/hardware/device_inventory_active.json",
        ],
        "state_path": "data/drivers/smart_driver_fabric_state.json",
        "plan_path": "out/runtime/smart_driver_fabric_plan.json",
        "bundle_root": "data/driverkit/smart_driver_fabric",
        "artifact_root": "data/drivers/loadable_artifacts",
        "artifact_registry_path": "data/drivers/smart_driver_fabric_artifact_registry.json",
        "artifact_build_pipeline_id": "axion-smart-driver-fabric",
        "artifact_source_commit_sha": "0000000000000000000000000000000000000000",
        "required_driver_classes_fallback": [
            "firmware_handoff",
            "motherboard_core",
            "device_io",
            "security_trust",
            "sandbox_mediation",
        ],
    }


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return deepcopy(default)
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
        return value
    except Exception:
        return deepcopy(default)


def _save_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def _resolve_path(value: str | None, fallback_parts: tuple[str, ...]) -> Path:
    raw = str(value or "").strip()
    if not raw:
        return axion_path(*fallback_parts)
    p = Path(raw)
    if p.is_absolute():
        return p
    return axion_path(*Path(raw).parts)


def _load_config(config_override: dict[str, Any] | None = None) -> dict[str, Any]:
    base = _default_config()
    file_cfg = _load_json(CONFIG_PATH, {})
    if isinstance(file_cfg, dict):
        base.update(file_cfg)
    if isinstance(config_override, dict):
        base.update(config_override)
    return base


def _infer_driver_class(driver: dict[str, Any]) -> str:
    explicit = str(driver.get("driver_class", "")).strip()
    if explicit:
        return explicit
    driver_id = str(driver.get("driver_id", "")).strip().lower()
    if driver_id.startswith("drv_mb_"):
        return "motherboard_core"
    if driver_id.startswith("drv_fw_"):
        return "firmware_handoff"
    if driver_id.startswith("drv_sec_"):
        return "security_trust"
    if driver_id.startswith("drv_sbx_"):
        return "sandbox_mediation"
    return "device_io"


def _choose_target_bsp(bsp_catalog: dict[str, Any], requested_bsp_id: str | None) -> dict[str, Any] | None:
    packages = [x for x in (bsp_catalog.get("packages") or []) if isinstance(x, dict)]
    if not packages:
        return None
    requested = str(requested_bsp_id or "").strip()
    if requested:
        for item in packages:
            if str(item.get("bsp_id", "")).strip() == requested:
                return item
    for item in packages:
        if str(item.get("support_level", "")).strip().lower() == "active":
            return item
    return packages[0]


def _parse_pnp_device(pnp: str) -> dict[str, str] | None:
    raw = str(pnp or "").strip()
    if not raw:
        return None
    pci = _PCI_RE.search(raw)
    if pci:
        return {"bus": "pci", "vendor": pci.group(1).lower(), "product": pci.group(2).lower()}
    usb = _USB_RE.search(raw)
    if usb:
        return {"bus": "usb", "vendor": usb.group(1).lower(), "product": usb.group(2).lower()}
    return None


def _normalize_device(entry: dict[str, Any], *, target_bsp_id: str | None) -> dict[str, Any] | None:
    if not isinstance(entry, dict):
        return None
    bus = str(entry.get("bus") or "").strip().lower()
    vendor = str(entry.get("vendor") or "").strip().lower()
    product = str(entry.get("product") or "").strip().lower()
    profile = str(entry.get("profile") or "").strip()
    cls = str(entry.get("class") or "").strip().lower()
    bsp = str(entry.get("bsp") or target_bsp_id or "").strip()
    if bus in ("pci", "usb"):
        if not (vendor and product):
            return None
        out = {"bus": bus, "vendor": vendor, "product": product}
        if cls:
            out["class"] = cls
        if bsp:
            out["bsp"] = bsp
        return out
    if bus == "sandbox":
        if not profile:
            return None
        out = {"bus": "sandbox", "profile": profile}
        if cls:
            out["class"] = cls
        if bsp:
            out["bsp"] = bsp
        return out
    return None


def _extract_windows_inventory_devices(payload: dict[str, Any], *, target_bsp_id: str | None) -> list[dict[str, Any]]:
    devices: list[dict[str, Any]] = []
    category_class = {
        "disk_drives": "storage",
        "network_adapters": "network",
        "video_controllers": "video",
        "sound_devices": "audio",
        "keyboards": "input",
        "pointing_devices": "input",
    }
    for category, cls in category_class.items():
        for row in (payload.get(category) or []):
            if not isinstance(row, dict):
                continue
            parsed = _parse_pnp_device(str(row.get("PNPDeviceID") or ""))
            if not parsed:
                continue
            parsed["class"] = cls
            if target_bsp_id:
                parsed["bsp"] = target_bsp_id
            devices.append(parsed)
    return devices


def _seed_devices_from_catalog(catalog: dict[str, Any], *, target_bsp_id: str | None) -> list[dict[str, Any]]:
    seeded: list[dict[str, Any]] = []
    for entry in (catalog.get("drivers") or []):
        if not isinstance(entry, dict):
            continue
        match = entry.get("match") or {}
        if not isinstance(match, dict):
            continue
        bus = str(match.get("bus") or "").strip().lower()
        required_bsp = str(match.get("bsp") or "").strip()
        if required_bsp and target_bsp_id and required_bsp != target_bsp_id:
            continue
        if bus in ("pci", "usb"):
            dev = _normalize_device(
                {
                    "bus": bus,
                    "vendor": match.get("vendor"),
                    "product": match.get("product"),
                    "class": _infer_driver_class(entry),
                    "bsp": required_bsp or target_bsp_id,
                },
                target_bsp_id=target_bsp_id,
            )
            if dev:
                seeded.append(dev)
        elif bus == "sandbox":
            dev = _normalize_device(
                {
                    "bus": "sandbox",
                    "profile": match.get("profile"),
                    "class": "sandbox",
                    "bsp": required_bsp or target_bsp_id,
                },
                target_bsp_id=target_bsp_id,
            )
            if dev:
                seeded.append(dev)
    return seeded


def _dedupe_devices(devices: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for dev in devices:
        key = json.dumps(
            {
                "bus": dev.get("bus"),
                "vendor": dev.get("vendor"),
                "product": dev.get("product"),
                "profile": dev.get("profile"),
                "bsp": dev.get("bsp"),
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(dev)
    return out


def _load_devices(
    cfg: dict[str, Any],
    *,
    target_bsp_id: str | None,
    catalog: dict[str, Any],
    hardware_inventory: list[dict[str, Any]] | dict[str, Any] | None,
) -> tuple[list[dict[str, Any]], str]:
    devices: list[dict[str, Any]] = []
    source = "none"

    payload = hardware_inventory
    if payload is None:
        for item in (cfg.get("inventory_sources") or []):
            path = _resolve_path(str(item), ())
            if not path.exists():
                continue
            payload = _load_json(path, None)
            source = str(path)
            break

    if isinstance(payload, list):
        for row in payload:
            if not isinstance(row, dict):
                continue
            normalized = _normalize_device(row, target_bsp_id=target_bsp_id)
            if normalized:
                devices.append(normalized)
        if source == "none":
            source = "inline_list"
    elif isinstance(payload, dict):
        if isinstance(payload.get("devices"), list):
            for row in payload.get("devices") or []:
                if not isinstance(row, dict):
                    continue
                normalized = _normalize_device(row, target_bsp_id=target_bsp_id)
                if normalized:
                    devices.append(normalized)
            if source == "none":
                source = "inline_devices_object"
        else:
            windows_devices = _extract_windows_inventory_devices(payload, target_bsp_id=target_bsp_id)
            devices.extend(windows_devices)
            if source == "none":
                source = "windows_inventory_object"

    seeded_devices = _seed_devices_from_catalog(catalog, target_bsp_id=target_bsp_id)
    if seeded_devices:
        devices.extend(seeded_devices)
        if source == "none":
            source = "catalog_seed"
        elif "catalog_seed" not in source:
            source = f"{source}+catalog_seed"

    return _dedupe_devices(devices), source


def _driver_matches(driver: dict[str, Any], device: dict[str, Any], *, target_bsp_id: str | None) -> bool:
    match = driver.get("match") or {}
    if not isinstance(match, dict):
        return False
    for key, value in match.items():
        key_s = str(key)
        val_s = str(value).strip().lower()
        if key_s == "bsp":
            required_bsp = str(value).strip()
            if target_bsp_id and required_bsp != str(target_bsp_id):
                return False
            dev_bsp = str(device.get("bsp") or "").strip()
            if dev_bsp and dev_bsp != required_bsp:
                return False
            continue
        dev_val = str(device.get(key_s) or "").strip().lower()
        if dev_val != val_s:
            return False
    return True


def _resolve_driver_set(
    devices: list[dict[str, Any]],
    catalog: dict[str, Any],
    *,
    target_bsp_id: str | None,
) -> list[dict[str, Any]]:
    drivers = [d for d in (catalog.get("drivers") or []) if isinstance(d, dict)]
    resolved: dict[str, dict[str, Any]] = {}
    for device in devices:
        candidates: list[dict[str, Any]] = []
        for driver in drivers:
            if _driver_matches(driver, device, target_bsp_id=target_bsp_id):
                candidates.append(driver)
        if not candidates:
            continue
        candidates.sort(
            key=lambda d: (
                len((d.get("match") or {}).keys()),
                1 if str((d.get("match") or {}).get("bsp") or "").strip() else 0,
                str(d.get("driver_id") or ""),
            ),
            reverse=True,
        )
        chosen = candidates[0]
        driver_id = str(chosen.get("driver_id") or "").strip()
        if not driver_id:
            continue
        resolved[driver_id] = {
            "driver_id": driver_id,
            "driver_class": _infer_driver_class(chosen),
            "version": str(chosen.get("version") or ""),
            "signed": bool(chosen.get("signed", False)),
            "match": dict(chosen.get("match") or {}),
        }
    return sorted(resolved.values(), key=lambda d: str(d.get("driver_id") or ""))


def _synth_driver_id(target_family: str, class_id: str) -> str:
    base = f"drv_sdf_{target_family}_{class_id}_v1".lower()
    return re.sub(r"[^a-z0-9_]+", "_", base).strip("_")


def _materialize_driver_bundle(bundle_root: Path, driver_id: str, class_id: str, target_family: str) -> Path:
    if callable(_create_driver_bundle):
        return _create_driver_bundle(bundle_root, driver_id, class_id, target_family)

    bundle_dir = bundle_root / driver_id
    for child in ("src", "tests", "docs"):
        (bundle_dir / child).mkdir(parents=True, exist_ok=True)
    manifest = {
        "driver_id": driver_id,
        "driver_class": class_id,
        "target_family": target_family,
        "version": "0.1.0",
        "package_kind": "axionhal_driver_bundle",
    }
    (bundle_dir / "bundle_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return bundle_dir


def _fingerprint(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def ensure_fabric_initialized(
    *,
    corr: str = "corr_sdf_bootstrap_001",
    hardware_inventory: list[dict[str, Any]] | dict[str, Any] | None = None,
    force_rebuild: bool = False,
    config_override: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cfg = _load_config(config_override=config_override)
    fail_closed = bool(cfg.get("fail_closed_on_error", False))
    enabled = bool(cfg.get("enabled", True))
    state_path = _resolve_path(str(cfg.get("state_path") or ""), ("data", "drivers", "smart_driver_fabric_state.json"))
    plan_path = _resolve_path(str(cfg.get("plan_path") or ""), ("out", "runtime", "smart_driver_fabric_plan.json"))
    bundle_root = _resolve_path(str(cfg.get("bundle_root") or ""), ("data", "driverkit", "smart_driver_fabric"))
    artifact_root = _resolve_path(str(cfg.get("artifact_root") or ""), ("data", "drivers", "loadable_artifacts"))
    artifact_registry_path = _resolve_path(
        str(cfg.get("artifact_registry_path") or ""),
        ("data", "drivers", "smart_driver_fabric_artifact_registry.json"),
    )
    artifact_pipeline = str(cfg.get("artifact_build_pipeline_id") or "axion-smart-driver-fabric")
    artifact_commit = str(cfg.get("artifact_source_commit_sha") or "0000000000000000000000000000000000000000")
    compile_artifacts = bool(cfg.get("compile_signed_loadable_artifacts", True))

    if not enabled:
        return {
            "ok": True,
            "code": "SMART_DRIVER_FABRIC_DISABLED",
            "corr": corr,
            "enabled": False,
            "fail_closed": fail_closed,
            "state_path": str(state_path),
            "plan_path": str(plan_path),
            "artifact_root": str(artifact_root),
            "artifact_registry_path": str(artifact_registry_path),
        }

    try:
        hal = _load_json(HAL_PATH, {})
        bsp_catalog = _load_json(BSP_PATH, {})
        contract = _load_json(CONTRACT_PATH, {})
        driver_catalog = _load_json(DRIVER_CATALOG_PATH, {})

        target_bsp = _choose_target_bsp(bsp_catalog, str(cfg.get("target_bsp_id") or "").strip())
        if not isinstance(target_bsp, dict):
            return {
                "ok": False,
                "code": "SMART_DRIVER_FABRIC_BSP_MISSING",
                "corr": corr,
                "fail_closed": fail_closed,
                "state_path": str(state_path),
                "plan_path": str(plan_path),
            }

        target_bsp_id = str(target_bsp.get("bsp_id") or "").strip()
        target_family = str(target_bsp.get("board_family") or "generic_x64_uefi").strip()
        required_classes = [
            str(x)
            for x in (target_bsp.get("required_driver_classes") or cfg.get("required_driver_classes_fallback") or [])
            if str(x).strip()
        ]
        if not required_classes:
            required_classes = [str(x) for x in (_default_config().get("required_driver_classes_fallback") or [])]
        required_classes = sorted(set(required_classes))

        devices, inventory_source = _load_devices(
            cfg,
            target_bsp_id=target_bsp_id,
            catalog=driver_catalog,
            hardware_inventory=hardware_inventory,
        )
        resolved = _resolve_driver_set(devices, driver_catalog, target_bsp_id=target_bsp_id)
        resolved_classes = sorted({_infer_driver_class(d) for d in resolved})
        missing_classes = sorted(set(required_classes) - set(resolved_classes))

        fingerprint_payload = {
            "fabric_id": str(cfg.get("fabric_id") or "AXION_SMART_DRIVER_FABRIC_V1"),
            "target_bsp_id": target_bsp_id,
            "target_family": target_family,
            "firmware_profile": str(target_bsp.get("firmware_profile") or ""),
            "os_profile": str(target_bsp.get("os_profile") or ""),
            "required_driver_classes": required_classes,
            "resolved_driver_ids": [str(d.get("driver_id") or "") for d in resolved],
            "missing_driver_classes": missing_classes,
            "inventory_devices": devices,
            "contract_installer_order": contract.get("sharedContracts", {}).get("installerOrder", []),
            "hal_profile": str(hal.get("profileId") or ""),
        }
        load_once_token = _fingerprint(fingerprint_payload)

        existing_state = _load_json(state_path, {})
        one_time = bool(cfg.get("one_time_bootstrap", True))
        if (
            one_time
            and not force_rebuild
            and isinstance(existing_state, dict)
            and bool(existing_state.get("ready"))
            and str(existing_state.get("load_once_token") or "") == load_once_token
        ):
            existing_state["last_seen_utc"] = _now_iso()
            existing_state["reuse_count"] = int(existing_state.get("reuse_count", 0)) + 1
            _save_json(state_path, existing_state)
            return {
                "ok": True,
                "code": "SMART_DRIVER_FABRIC_REUSED",
                "corr": corr,
                "fail_closed": fail_closed,
                "load_once_token": load_once_token,
                "target_bsp_id": target_bsp_id,
                "target_family": target_family,
                "required_driver_classes": required_classes,
                "missing_driver_classes": missing_classes,
                "resolved_drivers": resolved,
                "synthesized_drivers": list(existing_state.get("synthesized_drivers") or []),
                "compiled_artifacts": list(existing_state.get("compiled_artifacts") or []),
                "artifact_compile_failures": list(existing_state.get("artifact_compile_failures") or []),
                "inventory_source": inventory_source,
                "inventory_count": len(devices),
                "state_path": str(state_path),
                "plan_path": str(plan_path),
                "artifact_root": str(artifact_root),
                "artifact_registry_path": str(artifact_registry_path),
            }

        synthesized: list[dict[str, Any]] = []
        if bool(cfg.get("materialize_missing_required_classes", True)):
            for class_id in missing_classes:
                driver_id = _synth_driver_id(target_family, class_id)
                bundle_dir = _materialize_driver_bundle(bundle_root, driver_id, class_id, target_family)
                synthesized.append(
                    {
                        "driver_id": driver_id,
                        "driver_class": class_id,
                        "target_family": target_family,
                        "bundle_dir": str(bundle_dir),
                        "bundle_manifest_path": str(bundle_dir / "bundle_manifest.json"),
                        "synthesized": True,
                    }
                )

        compiled_artifacts: list[dict[str, Any]] = []
        artifact_compile_failures: list[dict[str, Any]] = []
        if compile_artifacts and synthesized:
            if callable(compile_smart_fabric_artifacts):
                compiled_out = compile_smart_fabric_artifacts(
                    synthesized_drivers=synthesized,
                    artifact_root=artifact_root,
                    artifact_registry_path=artifact_registry_path,
                    build_pipeline_id=artifact_pipeline,
                    source_commit_sha=artifact_commit,
                )
                compiled_artifacts = list(compiled_out.get("compiled_artifacts") or [])
                artifact_compile_failures = list(compiled_out.get("failures") or [])
                if artifact_compile_failures and fail_closed:
                    return {
                        "ok": False,
                        "code": "SMART_DRIVER_FABRIC_ARTIFACT_COMPILE_FAIL",
                        "corr": corr,
                        "fail_closed": fail_closed,
                        "load_once_token": load_once_token,
                        "target_bsp_id": target_bsp_id,
                        "target_family": target_family,
                        "required_driver_classes": required_classes,
                        "missing_driver_classes": missing_classes,
                        "resolved_drivers": resolved,
                        "synthesized_drivers": synthesized,
                        "compiled_artifacts": compiled_artifacts,
                        "artifact_compile_failures": artifact_compile_failures,
                        "inventory_source": inventory_source,
                        "inventory_count": len(devices),
                        "state_path": str(state_path),
                        "plan_path": str(plan_path),
                        "artifact_root": str(artifact_root),
                        "artifact_registry_path": str(artifact_registry_path),
                    }
            elif fail_closed:
                return {
                    "ok": False,
                    "code": "SMART_DRIVER_FABRIC_ARTIFACT_COMPILER_UNAVAILABLE",
                    "corr": corr,
                    "fail_closed": fail_closed,
                    "load_once_token": load_once_token,
                    "target_bsp_id": target_bsp_id,
                    "target_family": target_family,
                    "required_driver_classes": required_classes,
                    "missing_driver_classes": missing_classes,
                    "resolved_drivers": resolved,
                    "synthesized_drivers": synthesized,
                    "compiled_artifacts": [],
                    "artifact_compile_failures": [
                        {"code": "SMART_DRIVER_FABRIC_ARTIFACT_COMPILER_UNAVAILABLE"}
                    ],
                    "inventory_source": inventory_source,
                    "inventory_count": len(devices),
                    "state_path": str(state_path),
                    "plan_path": str(plan_path),
                    "artifact_root": str(artifact_root),
                    "artifact_registry_path": str(artifact_registry_path),
                }
            else:
                artifact_compile_failures = [{"code": "SMART_DRIVER_FABRIC_ARTIFACT_COMPILER_UNAVAILABLE"}]

        plan = {
            "version": 1,
            "contract_id": "smart_driver_fabric_v1",
            "corr": corr,
            "timestamp_utc": _now_iso(),
            "status": "PASS",
            "boot_load_mode": "single_load_unified",
            "load_once_token": load_once_token,
            "target_bsp_id": target_bsp_id,
            "target_family": target_family,
            "firmware_profile": str(target_bsp.get("firmware_profile") or ""),
            "os_profile": str(target_bsp.get("os_profile") or ""),
            "inventory_source": inventory_source,
            "inventory_count": len(devices),
            "required_driver_classes": required_classes,
            "resolved_driver_classes": resolved_classes,
            "missing_driver_classes": missing_classes,
            "resolved_drivers": resolved,
            "synthesized_drivers": synthesized,
            "compiled_artifacts": compiled_artifacts,
            "artifact_compile_failures": artifact_compile_failures,
            "installer_order": contract.get("sharedContracts", {}).get("installerOrder", []),
        }
        _save_json(plan_path, plan)

        state = {
            "version": 1,
            "fabric_id": str(cfg.get("fabric_id") or "AXION_SMART_DRIVER_FABRIC_V1"),
            "ready": True,
            "boot_load_mode": "single_load_unified",
            "load_once_token": load_once_token,
            "target_bsp_id": target_bsp_id,
            "target_family": target_family,
            "required_driver_classes": required_classes,
            "resolved_driver_ids": [str(d.get("driver_id") or "") for d in resolved],
            "synthesized_drivers": synthesized,
            "compiled_artifacts": compiled_artifacts,
            "artifact_compile_failures": artifact_compile_failures,
            "plan_path": str(plan_path),
            "last_bootstrap_utc": _now_iso(),
            "last_seen_utc": _now_iso(),
            "load_count": int(existing_state.get("load_count", 0)) + 1,
            "reuse_count": int(existing_state.get("reuse_count", 0)),
        }
        _save_json(state_path, state)
        return {
            "ok": True,
            "code": "SMART_DRIVER_FABRIC_READY",
            "corr": corr,
            "fail_closed": fail_closed,
            "load_once_token": load_once_token,
            "target_bsp_id": target_bsp_id,
            "target_family": target_family,
            "required_driver_classes": required_classes,
            "missing_driver_classes": missing_classes,
            "resolved_drivers": resolved,
            "synthesized_drivers": synthesized,
            "compiled_artifacts": compiled_artifacts,
            "artifact_compile_failures": artifact_compile_failures,
            "inventory_source": inventory_source,
            "inventory_count": len(devices),
            "state_path": str(state_path),
            "plan_path": str(plan_path),
            "artifact_root": str(artifact_root),
            "artifact_registry_path": str(artifact_registry_path),
        }
    except Exception as ex:
        return {
            "ok": False,
            "code": "SMART_DRIVER_FABRIC_ERROR",
            "corr": corr,
            "fail_closed": fail_closed,
            "error": str(ex),
            "state_path": str(state_path),
            "plan_path": str(plan_path),
        }
