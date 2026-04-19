#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
FW_BASE = Path(__file__).resolve().parents[1]
OS_ROOT = WORKSPACE_ROOT / "AxionOS"

PROVENANCE_DIR = OS_ROOT / "runtime" / "security"
if str(PROVENANCE_DIR) not in sys.path:
    sys.path.append(str(PROVENANCE_DIR))

from provenance_guard import issue_provenance_envelope, verify_provenance_envelope


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return default


def save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def hydrate_signing_env_from_files() -> None:
    def _hydrate_key_env(env_name: str, file_env_name: str) -> None:
        raw = str(os.environ.get(env_name, "")).strip()
        if raw:
            return
        file_path = str(os.environ.get(file_env_name, "")).strip()
        if not file_path:
            local_appdata = str(os.environ.get("LOCALAPPDATA", "")).strip()
            if local_appdata:
                candidate = Path(local_appdata) / "AxionOS" / "secrets" / "release_signing" / f"{env_name}.key"
                if candidate.exists():
                    file_path = str(candidate)
        if not file_path:
            return
        p = Path(file_path)
        if not p.exists():
            return
        value = p.read_text(encoding="utf-8-sig").strip()
        if value:
            os.environ[env_name] = value

    _hydrate_key_env("AXION_KMS_RELEASE_SIGNING_KEY_01", "AXION_KMS_RELEASE_SIGNING_KEY_01_FILE")
    _hydrate_key_env("AXION_HSM_RELEASE_SIGNING_KEY_02", "AXION_HSM_RELEASE_SIGNING_KEY_02_FILE")


def find_latest_json(path: Path, pattern: str = "*.json") -> Path:
    items = sorted(path.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    if not items:
        raise FileNotFoundError(f"No files matching {pattern} under {path}")
    return items[0]


def _norm_text(value: Any) -> str:
    return str(value or "").strip().lower()


def _extract_board_strings(inventory: dict[str, Any]) -> str:
    inv = inventory.get("inventory", {}) if isinstance(inventory, dict) else {}
    cs = inv.get("computer_system", {}) if isinstance(inv.get("computer_system"), dict) else {}
    bios = inv.get("bios", {}) if isinstance(inv.get("bios"), dict) else {}
    bb = inv.get("baseboard", {}) if isinstance(inv.get("baseboard"), dict) else {}
    cpu = inv.get("processor", {}) if isinstance(inv.get("processor"), dict) else {}
    parts = [
        cs.get("Manufacturer"),
        cs.get("Model"),
        cs.get("SystemFamily"),
        bios.get("Manufacturer"),
        bios.get("SMBIOSBIOSVersion"),
        bb.get("Manufacturer"),
        bb.get("Product"),
        bb.get("Version"),
        cpu.get("Manufacturer"),
        cpu.get("Name"),
    ]
    return " ".join(_norm_text(p) for p in parts if str(p or "").strip())


def detect_platform_lane(inventory: dict[str, Any]) -> str:
    board_text = _extract_board_strings(inventory)
    if "amd" in board_text:
        return "amd_x64"
    if "intel" in board_text or "q35" in board_text or "ich" in board_text:
        return "intel_x64"
    return "generic_x64_uefi"


def infer_chipset_family(inventory: dict[str, Any]) -> str:
    board_text = _extract_board_strings(inventory)
    hints = [
        ("q35", "q35"),
        ("ich9", "ich9"),
        ("pch", "intel_pch"),
        ("x670", "amd_x670"),
        ("b650", "amd_b650"),
        ("x570", "amd_x570"),
        ("promontory", "amd_promontory"),
    ]
    for needle, family in hints:
        if needle in board_text:
            return family
    if "intel" in board_text:
        return "intel_generic"
    if "amd" in board_text:
        return "amd_generic"
    return "unknown"


def _has_bus(inventory: dict[str, Any], bus: str) -> bool:
    counts = inventory.get("counts", {}) if isinstance(inventory, dict) else {}
    bus_map = {
        "pci": int(counts.get("pci_devices") or 0) > 0,
        "acpi": int(counts.get("acpi_devices") or 0) > 0,
        "usb": int(counts.get("usb_devices") or 0) > 0,
    }
    return bool(bus_map.get(bus, False))


def choose_adapter(
    inventory: dict[str, Any],
    adapter_contract: dict[str, Any],
    *,
    platform_lane: str,
    chipset_family: str,
) -> tuple[dict[str, Any], bool, list[str]]:
    adapters = [x for x in (adapter_contract.get("adapters") or []) if isinstance(x, dict)]
    default_id = str(adapter_contract.get("default_adapter_id") or "").strip()
    board_text = _extract_board_strings(inventory)
    scored: list[tuple[int, dict[str, Any], list[str]]] = []
    for adapter in adapters:
        score = 0
        reasons: list[str] = []
        lanes = [str(x).strip().lower() for x in (adapter.get("platform_lanes") or []) if str(x).strip()]
        if platform_lane.lower() in lanes:
            score += 4
            reasons.append("platform_lane_match")
        vendor_hints = [str(x).strip().lower() for x in (adapter.get("vendor_hints") or []) if str(x).strip()]
        if vendor_hints and any(v in board_text for v in vendor_hints):
            score += 3
            reasons.append("vendor_hint_match")
        chipset_hints = [str(x).strip().lower() for x in (adapter.get("chipset_hints") or []) if str(x).strip()]
        if chipset_hints and any(c in board_text for c in chipset_hints):
            score += 3
            reasons.append("chipset_hint_match")
        if chipset_hints and any(chipset_family.lower().startswith(c) for c in chipset_hints):
            score += 2
            reasons.append("chipset_family_match")
        required_buses = [str(x).strip().lower() for x in (adapter.get("required_buses") or []) if str(x).strip()]
        missing = [b for b in required_buses if not _has_bus(inventory, b)]
        if missing:
            score -= 5
            reasons.append(f"missing_required_buses:{','.join(missing)}")
        else:
            score += 1
            reasons.append("required_buses_present")
        scored.append((score, adapter, reasons))

    if not scored:
        raise RuntimeError("No adapters declared in chipset bus adapter contract")

    scored.sort(key=lambda x: (x[0], str(x[1].get("adapter_id") or "")), reverse=True)
    best_score, best, reasons = scored[0]
    default = next((a for a in adapters if str(a.get("adapter_id") or "").strip() == default_id), None)
    best_id = str(best.get("adapter_id") or "").strip()
    auto_mapped_unknown = bool(
        default is not None
        and (
            (best_score < 5)
            or (platform_lane.lower() == "generic_x64_uefi" and best_id == default_id)
        )
    )
    if auto_mapped_unknown and default is not None:
        return default, True, ["fallback_default_adapter", f"best_score={best_score}"]
    return best, False, reasons


def build_capability_graph(
    *,
    inventory: dict[str, Any],
    primitive_catalog: dict[str, Any],
    adapter_contract: dict[str, Any],
) -> dict[str, Any]:
    platform_lane = detect_platform_lane(inventory)
    chipset_family = infer_chipset_family(inventory)
    adapter, auto_mapped_unknown, reasons = choose_adapter(
        inventory,
        adapter_contract,
        platform_lane=platform_lane,
        chipset_family=chipset_family,
    )
    adapter_id = str(adapter.get("adapter_id") or "unknown_adapter")
    primitive_ids = [str(x) for x in (adapter.get("primitive_ids") or []) if str(x).strip()]
    if not primitive_ids:
        primitive_ids = [str(x) for x in (primitive_catalog.get("default_primitives") or []) if str(x).strip()]

    catalog_primitives = primitive_catalog.get("primitives", {}) if isinstance(primitive_catalog.get("primitives"), dict) else {}
    primitive_records = []
    for pid in primitive_ids:
        primitive_records.append(
            {
                "primitive_id": pid,
                "exists_in_catalog": pid in catalog_primitives,
                "definition": catalog_primitives.get(pid, {}),
            }
        )

    counts = inventory.get("counts", {}) if isinstance(inventory, dict) else {}
    graph = {
        "version": 1,
        "graph_id": "AXION_FW_HARDWARE_CAPABILITY_GRAPH_V1",
        "generated_utc": now_iso(),
        "machine_id": str(inventory.get("machine_id") or "unknown_machine"),
        "inventory_manifest_path": str(inventory.get("manifest_path") or inventory.get("source_path") or ""),
        "platform_lane": platform_lane,
        "chipset_family": chipset_family,
        "bus_capabilities": {
            "pci_devices": int(counts.get("pci_devices") or 0),
            "acpi_devices": int(counts.get("acpi_devices") or 0),
            "usb_devices": int(counts.get("usb_devices") or 0),
            "has_pci": _has_bus(inventory, "pci"),
            "has_acpi": _has_bus(inventory, "acpi"),
            "has_usb": _has_bus(inventory, "usb"),
        },
        "adapter_selection": {
            "adapter_id": adapter_id,
            "auto_mapped_unknown_board": auto_mapped_unknown,
            "selection_reasons": reasons,
            "required_buses": list(adapter.get("required_buses") or []),
        },
        "rewrite_primitives": primitive_records,
        "safety": {
            "mandatory_backup_before_rewrite": True,
            "ab_slot_staging_required": True,
            "rollback_required_on_any_failure": True,
            "physical_flash_default": "disabled",
        },
    }
    return graph


def locate_latest_firmware_manifest(fw_base: Path) -> Path:
    manifests = sorted((fw_base / "out").glob("**/manifest.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not manifests:
        raise FileNotFoundError(f"No firmware manifest found under {fw_base / 'out'}")
    return manifests[0]


def resolve_payload_files(firmware_manifest_path: Path) -> list[dict[str, Any]]:
    manifest = load_json(firmware_manifest_path, {})
    root = firmware_manifest_path.parent
    out: list[dict[str, Any]] = []
    for rel in (manifest.get("files") or []):
        rel_s = str(rel or "").strip()
        if not rel_s:
            continue
        p = root / rel_s
        if not p.exists():
            continue
        out.append(
            {
                "name": p.name,
                "path": str(p),
                "sha256": sha256_file(p),
                "size_bytes": int(p.stat().st_size),
            }
        )
    return out


def load_slot_state(slot_state_path: Path) -> dict[str, Any]:
    default = {
        "version": 1,
        "active_slot": "A",
        "pending_slot_on_reboot": None,
        "rollback_slot": "A",
        "last_update_utc": None,
    }
    state = load_json(slot_state_path, default)
    if not isinstance(state, dict):
        return dict(default)
    merged = dict(default)
    merged.update(state)
    active = str(merged.get("active_slot") or "A").upper()
    merged["active_slot"] = "A" if active not in ("A", "B") else active
    return merged


def _target_slot(active_slot: str) -> str:
    return "B" if str(active_slot).upper() == "A" else "A"


def _deep_merge_dict(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge_dict(merged.get(key, {}), value)
        else:
            merged[key] = value
    return merged


def _default_physical_flash_policy(capability_graph: dict[str, Any]) -> dict[str, Any]:
    adapter = capability_graph.get("adapter_selection", {}) if isinstance(capability_graph, dict) else {}
    adapter_id = str(adapter.get("adapter_id") or "").strip()
    platform_lane = str(capability_graph.get("platform_lane") or "").strip()
    return {
        "version": 1,
        "policy_id": "AXION_CONTROLLED_PHYSICAL_FLASH_POLICY_V1",
        "lane_enabled": True,
        "mode": "controlled_fail_closed",
        "max_inventory_age_hours": 24,
        "allow": {
            "adapter_ids": [adapter_id] if adapter_id else [],
            "platform_lanes": [platform_lane] if platform_lane else [],
            "vendor_tokens": [
                "intel",
                "amd",
                "dell",
                "hp",
                "lenovo",
                "asus",
                "msi",
                "gigabyte",
                "asrock",
                "qemu",
                "bochs",
                "innotek",
            ],
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
        "executor": {
            "allow_real_flash_command": False,
            "real_flash_opt_in_env": "AXION_ENABLE_REAL_FLASH_COMMAND",
            "command_timeout_sec": 180,
        },
        "command_profiles": {},
    }


def load_physical_flash_policy(*, policy_path: Path, capability_graph: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    default = _default_physical_flash_policy(capability_graph)
    raw = load_json(policy_path, {})
    if isinstance(raw, dict) and raw:
        return _deep_merge_dict(default, raw), True
    return default, False


def _inventory_from_plan(plan: dict[str, Any]) -> tuple[dict[str, Any], str]:
    cap = plan.get("capability_graph", {}) if isinstance(plan.get("capability_graph"), dict) else {}
    inv_path_s = str(cap.get("inventory_manifest_path") or "").strip()
    if not inv_path_s:
        return {}, ""
    inv_path = Path(inv_path_s)
    inv = load_json(inv_path, {})
    if not isinstance(inv, dict):
        return {}, str(inv_path)
    return inv, str(inv_path)


def _parse_iso_utc(value: Any) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(raw).astimezone(timezone.utc)
    except Exception:
        return None


def _physical_flash_denied(
    *,
    code: str,
    reason: str,
    policy: dict[str, Any],
    plan: dict[str, Any],
    inventory_manifest_path: str,
) -> dict[str, Any]:
    return {
        "ok": False,
        "code": code,
        "status": "denied",
        "reason": reason,
        "mode": str(policy.get("mode") or ""),
        "policy_id": str(policy.get("policy_id") or ""),
        "plan_id": str(plan.get("plan_id") or ""),
        "inventory_manifest_path": inventory_manifest_path or None,
    }


def evaluate_physical_flash_request(
    *,
    plan: dict[str, Any],
    policy: dict[str, Any],
    backup_receipt: dict[str, Any] | None,
    active_slot: str,
    target_slot: str,
) -> dict[str, Any]:
    inventory, inventory_manifest_path = _inventory_from_plan(plan)
    if str(policy.get("mode") or "") != "controlled_fail_closed":
        return _physical_flash_denied(
            code="FW_REWRITE_PHYSICAL_FLASH_POLICY_MODE_INVALID",
            reason="policy mode must be controlled_fail_closed",
            policy=policy,
            plan=plan,
            inventory_manifest_path=inventory_manifest_path,
        )

    execution_policy = plan.get("execution_policy", {}) if isinstance(plan.get("execution_policy"), dict) else {}
    if not bool(execution_policy.get("allow_physical_flash", False)):
        return _physical_flash_denied(
            code="FW_REWRITE_PHYSICAL_FLASH_DISABLED_BY_PLAN_POLICY",
            reason="rewrite plan execution policy does not allow physical flash requests",
            policy=policy,
            plan=plan,
            inventory_manifest_path=inventory_manifest_path,
        )

    rollback_enforcement = policy.get("rollback_enforcement", {}) if isinstance(policy.get("rollback_enforcement"), dict) else {}
    if bool(rollback_enforcement.get("require_backup_created", True)) and not backup_receipt:
        return _physical_flash_denied(
            code="FW_REWRITE_PHYSICAL_FLASH_BACKUP_REQUIRED",
            reason="backup receipt is required before physical flash execution",
            policy=policy,
            plan=plan,
            inventory_manifest_path=inventory_manifest_path,
        )
    if bool(rollback_enforcement.get("require_ab_slots", True)):
        if active_slot not in ("A", "B") or target_slot not in ("A", "B") or active_slot == target_slot:
            return _physical_flash_denied(
                code="FW_REWRITE_PHYSICAL_FLASH_INVALID_SLOT_STATE",
                reason="A/B slot state invalid for controlled physical flash",
                policy=policy,
                plan=plan,
                inventory_manifest_path=inventory_manifest_path,
            )
    if bool(rollback_enforcement.get("require_rollback_slot", True)):
        rollback_slot = str(((plan.get("slots") or {}).get("rollback_slot") or "")).upper()
        if rollback_slot != active_slot:
            return _physical_flash_denied(
                code="FW_REWRITE_PHYSICAL_FLASH_ROLLBACK_SLOT_INVALID",
                reason="rollback slot must match active slot before physical flash",
                policy=policy,
                plan=plan,
                inventory_manifest_path=inventory_manifest_path,
            )

    allow = policy.get("allow", {}) if isinstance(policy.get("allow"), dict) else {}
    adapter_allow = [str(x).strip() for x in (allow.get("adapter_ids") or []) if str(x).strip()]
    adapter_id = str(((plan.get("rewrite_adapter") or {}).get("adapter_id") or "")).strip()
    if adapter_allow and adapter_id not in adapter_allow:
        return _physical_flash_denied(
            code="FW_REWRITE_PHYSICAL_FLASH_ADAPTER_DENIED",
            reason=f"adapter {adapter_id} is not permitted by physical flash policy",
            policy=policy,
            plan=plan,
            inventory_manifest_path=inventory_manifest_path,
        )

    lane_allow = [str(x).strip().lower() for x in (allow.get("platform_lanes") or []) if str(x).strip()]
    platform_lane = str(((plan.get("capability_graph") or {}).get("platform_lane") or "")).strip().lower()
    if lane_allow and platform_lane not in lane_allow:
        return _physical_flash_denied(
            code="FW_REWRITE_PHYSICAL_FLASH_PLATFORM_LANE_DENIED",
            reason=f"platform lane {platform_lane or 'unknown'} not allowed by physical flash policy",
            policy=policy,
            plan=plan,
            inventory_manifest_path=inventory_manifest_path,
        )

    vendor_tokens = [str(x).strip().lower() for x in (allow.get("vendor_tokens") or []) if str(x).strip()]
    board_text = _extract_board_strings(inventory)
    if vendor_tokens and not any(token in board_text for token in vendor_tokens):
        return _physical_flash_denied(
            code="FW_REWRITE_PHYSICAL_FLASH_VENDOR_DENIED",
            reason="inventory vendor signature does not match allowed vendor tokens",
            policy=policy,
            plan=plan,
            inventory_manifest_path=inventory_manifest_path,
        )

    max_age_hours = int(policy.get("max_inventory_age_hours") or 0)
    if max_age_hours > 0:
        generated = _parse_iso_utc((inventory.get("generated_utc") if isinstance(inventory, dict) else None))
        if generated is None:
            return _physical_flash_denied(
                code="FW_REWRITE_PHYSICAL_FLASH_INVENTORY_TIMESTAMP_MISSING",
                reason="inventory timestamp is required by physical flash policy",
                policy=policy,
                plan=plan,
                inventory_manifest_path=inventory_manifest_path,
            )
        age_hours = (datetime.now(timezone.utc) - generated).total_seconds() / 3600.0
        if age_hours > float(max_age_hours):
            return _physical_flash_denied(
                code="FW_REWRITE_PHYSICAL_FLASH_INVENTORY_TOO_OLD",
                reason=f"inventory age {age_hours:.2f}h exceeds max {max_age_hours}h",
                policy=policy,
                plan=plan,
                inventory_manifest_path=inventory_manifest_path,
            )

    ack = policy.get("operator_ack", {}) if isinstance(policy.get("operator_ack"), dict) else {}
    if bool(ack.get("required", True)):
        ack_env = str(ack.get("env") or "AXION_PHYSICAL_FLASH_ACK").strip()
        ack_value = str(ack.get("value") or "").strip()
        actual = str(os.environ.get(ack_env, "")).strip()
        if not ack_value or actual != ack_value:
            return _physical_flash_denied(
                code="FW_REWRITE_PHYSICAL_FLASH_ACK_REQUIRED",
                reason=f"set {ack_env} to required approval token before physical flash",
                policy=policy,
                plan=plan,
                inventory_manifest_path=inventory_manifest_path,
            )
        if bool(ack.get("require_matching_plan_id", True)):
            session_env = str(ack.get("session_env") or "AXION_PHYSICAL_FLASH_SESSION_ID").strip()
            session_actual = str(os.environ.get(session_env, "")).strip()
            if session_actual != str(plan.get("plan_id") or ""):
                return _physical_flash_denied(
                    code="FW_REWRITE_PHYSICAL_FLASH_SESSION_MISMATCH",
                    reason=f"{session_env} must equal current plan_id before physical flash",
                    policy=policy,
                    plan=plan,
                    inventory_manifest_path=inventory_manifest_path,
                )

    return {
        "ok": True,
        "code": "FW_REWRITE_PHYSICAL_FLASH_GATES_PASS",
        "status": "authorized",
        "mode": str(policy.get("mode") or ""),
        "policy_id": str(policy.get("policy_id") or ""),
        "plan_id": str(plan.get("plan_id") or ""),
        "adapter_id": adapter_id,
        "platform_lane": platform_lane,
        "inventory_manifest_path": inventory_manifest_path or None,
    }


def _render_command_token(value: Any, replacements: dict[str, str]) -> str:
    token = str(value or "")
    for key, repl in replacements.items():
        token = token.replace("{" + key + "}", repl)
    return token


def execute_controlled_physical_flash(
    *,
    plan: dict[str, Any],
    policy: dict[str, Any],
    stage_dir: Path,
    backup_receipt: dict[str, Any] | None,
    active_slot: str,
    target_slot: str,
) -> dict[str, Any]:
    adapter_id = str(((plan.get("rewrite_adapter") or {}).get("adapter_id") or "")).strip()
    command_profiles = policy.get("command_profiles", {}) if isinstance(policy.get("command_profiles"), dict) else {}
    profile = command_profiles.get(adapter_id)
    if not isinstance(profile, dict):
        return {
            "ok": False,
            "code": "FW_REWRITE_PHYSICAL_FLASH_PROFILE_MISSING",
            "status": "denied",
            "reason": f"missing command profile for adapter {adapter_id or 'unknown'}",
        }

    receipts_root = FW_BASE / "out" / "rewrite" / "physical_flash_receipts"
    receipt_path = receipts_root / f"{str(plan.get('plan_id') or 'unknown_plan')}.json"
    receipt = {
        "version": 1,
        "created_utc": now_iso(),
        "plan_id": str(plan.get("plan_id") or ""),
        "policy_id": str(policy.get("policy_id") or ""),
        "adapter_id": adapter_id,
        "active_slot": active_slot,
        "target_slot": target_slot,
        "stage_dir": str(stage_dir),
        "backup_dir": str((backup_receipt or {}).get("backup_dir") or ""),
        "profile": profile,
    }

    execution_kind = str(profile.get("execution_kind") or "receipt_only").strip().lower()
    if execution_kind == "receipt_only":
        receipt["status"] = "authorized_receipt_only"
        receipt["note"] = "Physical flash lane authorized; command execution disabled by profile."
        save_json(receipt_path, receipt)
        return {
            "ok": True,
            "code": "FW_REWRITE_PHYSICAL_FLASH_AUTHORIZED_RECEIPT_ONLY",
            "status": "authorized_receipt_only",
            "receipt_path": str(receipt_path),
            "execution_kind": execution_kind,
        }

    if execution_kind != "command":
        receipt["status"] = "denied_invalid_execution_kind"
        save_json(receipt_path, receipt)
        return {
            "ok": False,
            "code": "FW_REWRITE_PHYSICAL_FLASH_EXECUTION_KIND_INVALID",
            "status": "denied",
            "receipt_path": str(receipt_path),
        }

    executor_cfg = policy.get("executor", {}) if isinstance(policy.get("executor"), dict) else {}
    if not bool(executor_cfg.get("allow_real_flash_command", False)):
        receipt["status"] = "denied_real_flash_disabled_by_policy"
        save_json(receipt_path, receipt)
        return {
            "ok": False,
            "code": "FW_REWRITE_PHYSICAL_FLASH_REAL_COMMAND_DISABLED",
            "status": "denied",
            "receipt_path": str(receipt_path),
        }

    opt_in_env = str(executor_cfg.get("real_flash_opt_in_env") or "AXION_ENABLE_REAL_FLASH_COMMAND").strip()
    if str(os.environ.get(opt_in_env, "")).strip() != "1":
        receipt["status"] = "denied_real_flash_opt_in_missing"
        save_json(receipt_path, receipt)
        return {
            "ok": False,
            "code": "FW_REWRITE_PHYSICAL_FLASH_REAL_COMMAND_OPT_IN_REQUIRED",
            "status": "denied",
            "receipt_path": str(receipt_path),
        }

    command = profile.get("command")
    if not isinstance(command, list) or not command:
        receipt["status"] = "denied_command_template_missing"
        save_json(receipt_path, receipt)
        return {
            "ok": False,
            "code": "FW_REWRITE_PHYSICAL_FLASH_COMMAND_TEMPLATE_MISSING",
            "status": "denied",
            "receipt_path": str(receipt_path),
        }

    replacements = {
        "plan_id": str(plan.get("plan_id") or ""),
        "stage_dir": str(stage_dir),
        "backup_dir": str((backup_receipt or {}).get("backup_dir") or ""),
        "active_slot": active_slot,
        "target_slot": target_slot,
    }
    command_line = [_render_command_token(x, replacements) for x in command]
    timeout_sec = int(executor_cfg.get("command_timeout_sec") or 180)
    result = subprocess.run(command_line, capture_output=True, text=True, timeout=max(timeout_sec, 1))
    receipt["command_line"] = command_line
    receipt["exit_code"] = int(result.returncode)
    receipt["stdout_tail"] = str(result.stdout or "")[-2000:]
    receipt["stderr_tail"] = str(result.stderr or "")[-2000:]
    save_json(receipt_path, receipt)
    if int(result.returncode) != 0:
        return {
            "ok": False,
            "code": "FW_REWRITE_PHYSICAL_FLASH_COMMAND_FAILED",
            "status": "failed",
            "receipt_path": str(receipt_path),
            "exit_code": int(result.returncode),
        }
    return {
        "ok": True,
        "code": "FW_REWRITE_PHYSICAL_FLASH_COMMAND_OK",
        "status": "executed",
        "receipt_path": str(receipt_path),
        "execution_kind": execution_kind,
    }


def build_rewrite_plan(
    *,
    fw_base: Path,
    capability_graph: dict[str, Any],
    pending_bios_settings_path: Path,
    rewrite_plan_path: Path,
) -> dict[str, Any]:
    rewrite_root = fw_base / "out" / "rewrite"
    backups_root = rewrite_root / "backups"
    slots_root = rewrite_root / "slots"
    slot_state_path = rewrite_root / "slot_state.json"
    firmware_manifest_path = locate_latest_firmware_manifest(fw_base)
    payload_files = resolve_payload_files(firmware_manifest_path)
    if not payload_files:
        raise RuntimeError(f"No payload files resolved from firmware manifest: {firmware_manifest_path}")

    slot_state = load_slot_state(slot_state_path)
    active_slot = str(slot_state.get("active_slot") or "A").upper()
    target_slot = _target_slot(active_slot)
    pending_bios = load_json(pending_bios_settings_path, {})
    if not isinstance(pending_bios, dict):
        pending_bios = {}

    required_free_bytes = 512 * 1024 * 1024
    if payload_files:
        required_free_bytes = max(required_free_bytes, int(sum(int(x.get("size_bytes") or 0) for x in payload_files) * 3))

    adapter = capability_graph.get("adapter_selection", {}) if isinstance(capability_graph, dict) else {}
    rewrite_primitives = [x.get("primitive_id") for x in (capability_graph.get("rewrite_primitives") or []) if isinstance(x, dict)]
    physical_flash_policy_path = fw_base / "policy" / "physical_flash_executor_policy_v1.json"
    physical_flash_policy, physical_flash_policy_from_file = load_physical_flash_policy(
        policy_path=physical_flash_policy_path,
        capability_graph=capability_graph,
    )
    plan = {
        "version": 1,
        "plan_id": f"axion_fw_rewrite_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_utc": now_iso(),
        "contract_id": "AXION_SIGNED_FW_REWRITE_EXECUTOR_V1",
        "capability_graph_path": str(rewrite_plan_path.parent / "capability_graph_v1.json"),
        "capability_graph": {
            "platform_lane": str(capability_graph.get("platform_lane") or ""),
            "chipset_family": str(capability_graph.get("chipset_family") or ""),
            "adapter_id": str(adapter.get("adapter_id") or ""),
            "auto_mapped_unknown_board": bool(adapter.get("auto_mapped_unknown_board", False)),
            "inventory_manifest_path": str(capability_graph.get("inventory_manifest_path") or ""),
        },
        "rewrite_adapter": {
            "adapter_id": str(adapter.get("adapter_id") or ""),
            "selection_reasons": list(adapter.get("selection_reasons") or []),
            "primitive_ids": rewrite_primitives,
        },
        "firmware_payload": {
            "firmware_manifest_path": str(firmware_manifest_path),
            "files": payload_files,
        },
        "bios_settings": {
            "pending_path": str(pending_bios_settings_path),
            "pending_present": bool(pending_bios),
            "pending_status": str(pending_bios.get("status") or "NONE"),
            "apply_after_restart": bool(pending_bios.get("apply_after_restart", True)),
            "settings": dict(pending_bios.get("settings") or {}),
        },
        "execution_policy": {
            "allow_physical_flash": bool(physical_flash_policy.get("lane_enabled", True)),
            "require_signature": True,
            "mandatory_backup": True,
            "ab_slots_required": True,
            "rollback_on_failure": True,
            "required_free_space_bytes": required_free_bytes,
            "physical_flash_mode": str(physical_flash_policy.get("mode") or "controlled_fail_closed"),
        },
        "physical_flash_executor": {
            "policy_path": str(physical_flash_policy_path),
            "policy_loaded_from_file": bool(physical_flash_policy_from_file),
            "policy_id": str(physical_flash_policy.get("policy_id") or "AXION_CONTROLLED_PHYSICAL_FLASH_POLICY_V1"),
            "mode": str(physical_flash_policy.get("mode") or "controlled_fail_closed"),
            "max_inventory_age_hours": int(physical_flash_policy.get("max_inventory_age_hours") or 0),
            "allow": dict(physical_flash_policy.get("allow") or {}),
            "rollback_enforcement": dict(physical_flash_policy.get("rollback_enforcement") or {}),
            "operator_ack": {
                "required": bool((physical_flash_policy.get("operator_ack") or {}).get("required", True)),
                "env": str((physical_flash_policy.get("operator_ack") or {}).get("env") or "AXION_PHYSICAL_FLASH_ACK"),
                "session_env": str((physical_flash_policy.get("operator_ack") or {}).get("session_env") or "AXION_PHYSICAL_FLASH_SESSION_ID"),
                "require_matching_plan_id": bool((physical_flash_policy.get("operator_ack") or {}).get("require_matching_plan_id", True)),
            },
            "executor": {
                "allow_real_flash_command": bool((physical_flash_policy.get("executor") or {}).get("allow_real_flash_command", False)),
                "real_flash_opt_in_env": str((physical_flash_policy.get("executor") or {}).get("real_flash_opt_in_env") or "AXION_ENABLE_REAL_FLASH_COMMAND"),
            },
            "command_profile_ids": sorted(
                str(k)
                for k, v in (physical_flash_policy.get("command_profiles") or {}).items()
                if isinstance(v, dict)
            ),
        },
        "backup": {
            "required": True,
            "backup_root": str(backups_root),
            "strategy": "copy_payload_and_metadata",
            "manifest_file": "backup_manifest.json",
        },
        "slots": {
            "slot_state_path": str(slot_state_path),
            "slots_root": str(slots_root),
            "active_slot": active_slot,
            "target_slot": target_slot,
            "rollback_slot": active_slot,
        },
        "operations": [
            {"op": "verify_inventory_and_adapter_contract", "required": True},
            {"op": "preflight_disk_and_payload_validation", "required": True},
            {"op": "create_backup_snapshot", "required": True},
            {"op": "stage_payload_to_inactive_slot", "required": True},
            {"op": "verify_staged_hashes", "required": True},
            {"op": "mark_slot_pending_on_reboot", "required": True},
            {"op": "rollback_to_active_slot_on_any_error", "required": True},
            {"op": "physical_flash_controlled_lane", "required": False, "policy_gated": True},
        ],
    }
    return plan


def sign_rewrite_plan(
    *,
    plan_path: Path,
    signature_path: Path,
    source_commit_sha: str,
    build_pipeline_id: str,
    trusted_key_id: str | None = None,
) -> dict[str, Any]:
    hydrate_signing_env_from_files()

    plan = load_json(plan_path, {})
    if not isinstance(plan, dict) or not plan:
        return {
            "ok": False,
            "code": "FW_REWRITE_PLAN_INVALID",
            "plan_path": str(plan_path),
        }
    metadata = {
        "artifact_kind": "firmware_rewrite_plan",
        "plan_id": str(plan.get("plan_id") or ""),
        "adapter_id": str((plan.get("rewrite_adapter") or {}).get("adapter_id") or ""),
    }
    issue = issue_provenance_envelope(
        subject_type="module",
        artifact_path=str(plan_path),
        metadata=metadata,
        source_commit_sha=source_commit_sha,
        build_pipeline_id=build_pipeline_id,
        trusted_key_id=trusted_key_id,
    )
    if not bool(issue.get("ok")):
        out = {
            "ok": False,
            "code": str(issue.get("code") or "FW_REWRITE_PLAN_SIGN_FAIL"),
            "issue": issue,
            "plan_path": str(plan_path),
        }
        save_json(signature_path, out)
        return out
    envelope = dict(issue.get("envelope") or {})
    verify = verify_provenance_envelope(
        subject_type="module",
        artifact_path=str(plan_path),
        envelope=envelope,
        metadata=metadata,
    )
    out = {
        "ok": bool(verify.get("ok")),
        "code": "FW_REWRITE_PLAN_SIGNED_VERIFIED" if bool(verify.get("ok")) else str(verify.get("code") or "FW_REWRITE_PLAN_VERIFY_FAIL"),
        "plan_path": str(plan_path),
        "signature_path": str(signature_path),
        "envelope": envelope,
        "verify": verify,
    }
    save_json(signature_path, out)
    return out


def _copy_with_hash(src: Path, dst: Path) -> dict[str, Any]:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return {
        "src": str(src),
        "dst": str(dst),
        "sha256": sha256_file(dst),
        "size_bytes": int(dst.stat().st_size),
    }


def execute_rewrite_plan(
    *,
    plan_path: Path,
    signature_path: Path,
    report_path: Path,
    allow_physical_flash: bool = False,
) -> dict[str, Any]:
    hydrate_signing_env_from_files()

    plan = load_json(plan_path, {})
    sig = load_json(signature_path, {})
    if not isinstance(plan, dict) or not plan:
        out = {"ok": False, "code": "FW_REWRITE_PLAN_INVALID", "plan_path": str(plan_path)}
        save_json(report_path, out)
        return out
    if not isinstance(sig, dict) or not bool(sig.get("ok")):
        out = {"ok": False, "code": "FW_REWRITE_SIGNATURE_INVALID", "signature_path": str(signature_path)}
        save_json(report_path, out)
        return out

    metadata = {
        "artifact_kind": "firmware_rewrite_plan",
        "plan_id": str(plan.get("plan_id") or ""),
        "adapter_id": str((plan.get("rewrite_adapter") or {}).get("adapter_id") or ""),
    }
    envelope = sig.get("envelope") if isinstance(sig.get("envelope"), dict) else {}
    verify = verify_provenance_envelope(
        subject_type="module",
        artifact_path=str(plan_path),
        envelope=envelope,
        metadata=metadata,
    )
    if not bool(verify.get("ok")):
        out = {
            "ok": False,
            "code": str(verify.get("code") or "FW_REWRITE_SIGNATURE_VERIFY_FAIL"),
            "verify": verify,
            "plan_path": str(plan_path),
        }
        save_json(report_path, out)
        return out

    execution_policy = plan.get("execution_policy", {}) if isinstance(plan.get("execution_policy"), dict) else {}
    backup_cfg = plan.get("backup", {}) if isinstance(plan.get("backup"), dict) else {}
    slots = plan.get("slots", {}) if isinstance(plan.get("slots"), dict) else {}
    payload = plan.get("firmware_payload", {}) if isinstance(plan.get("firmware_payload"), dict) else {}

    backup_required = bool(execution_policy.get("mandatory_backup", True))
    slot_state_path = Path(str(slots.get("slot_state_path") or (FW_BASE / "out" / "rewrite" / "slot_state.json")))
    slots_root = Path(str(slots.get("slots_root") or (FW_BASE / "out" / "rewrite" / "slots")))
    active_slot = str(slots.get("active_slot") or "A").upper()
    target_slot = str(slots.get("target_slot") or _target_slot(active_slot)).upper()

    required_free = int(execution_policy.get("required_free_space_bytes") or 0)
    usage = shutil.disk_usage(str(slots_root.parent if slots_root.parent.exists() else FW_BASE))
    if required_free > 0 and int(usage.free) < required_free:
        out = {
            "ok": False,
            "code": "FW_REWRITE_PREFLIGHT_INSUFFICIENT_DISK",
            "required_free_space_bytes": required_free,
            "actual_free_space_bytes": int(usage.free),
        }
        save_json(report_path, out)
        return out

    backup_receipt: dict[str, Any] | None = None
    if backup_required:
        backup_root = Path(str(backup_cfg.get("backup_root") or (FW_BASE / "out" / "rewrite" / "backups")))
        backup_dir = backup_root / str(plan.get("plan_id") or "unknown_plan")
        backup_dir.mkdir(parents=True, exist_ok=True)
        copied = []
        for item in payload.get("files") or []:
            if not isinstance(item, dict):
                continue
            src = Path(str(item.get("path") or ""))
            if not src.exists():
                out = {
                    "ok": False,
                    "code": "FW_REWRITE_BACKUP_SOURCE_MISSING",
                    "source_path": str(src),
                }
                save_json(report_path, out)
                return out
            copied.append(_copy_with_hash(src, backup_dir / src.name))
        backup_manifest_path = backup_dir / str(backup_cfg.get("manifest_file") or "backup_manifest.json")
        backup_receipt = {
            "version": 1,
            "plan_id": plan.get("plan_id"),
            "created_utc": now_iso(),
            "backup_dir": str(backup_dir),
            "files": copied,
        }
        save_json(backup_manifest_path, backup_receipt)

    stage_dir = slots_root / target_slot / str(plan.get("plan_id") or "unknown_plan")
    stage_dir.mkdir(parents=True, exist_ok=True)
    staged_files = []
    try:
        for item in payload.get("files") or []:
            if not isinstance(item, dict):
                continue
            src = Path(str(item.get("path") or ""))
            if not src.exists():
                raise FileNotFoundError(f"payload source missing: {src}")
            staged = _copy_with_hash(src, stage_dir / src.name)
            expected = str(item.get("sha256") or "").lower()
            actual = str(staged.get("sha256") or "").lower()
            if expected and expected != actual:
                raise RuntimeError(f"staged hash mismatch for {src.name}: expected={expected} actual={actual}")
            staged_files.append(staged)
    except Exception as ex:
        out = {
            "ok": False,
            "code": "FW_REWRITE_STAGE_FAIL_ROLLBACK_READY",
            "error": str(ex),
            "rollback_slot": active_slot,
            "backup_created": bool(backup_receipt),
            "staged_dir": str(stage_dir),
        }
        save_json(report_path, out)
        return out

    physical_requested = bool(allow_physical_flash)
    physical_policy = bool(execution_policy.get("allow_physical_flash", False))
    physical_mode = str(execution_policy.get("physical_flash_mode") or "controlled_fail_closed")
    physical_summary: dict[str, Any] = {
        "requested": physical_requested,
        "policy_allows": physical_policy,
        "mode": physical_mode,
        "effective": False,
        "status": "not_requested",
    }

    state = load_slot_state(slot_state_path)
    state["rollback_slot"] = active_slot
    state["last_update_utc"] = now_iso()
    state["last_plan_id"] = str(plan.get("plan_id") or "")
    state["last_backup_path"] = str((backup_receipt or {}).get("backup_dir") or "")
    state["brick_protection"] = {
        "backup_required": backup_required,
        "backup_created": bool(backup_receipt),
        "ab_slots": True,
        "rollback_slot": active_slot,
    }

    if not physical_requested:
        state["pending_slot_on_reboot"] = target_slot
        save_json(slot_state_path, state)
        physical_summary["status"] = "not_requested"
        out = {
            "ok": True,
            "code": "FW_REWRITE_STAGED_PENDING_REBOOT",
            "plan_path": str(plan_path),
            "signature_path": str(signature_path),
            "report_path": str(report_path),
            "active_slot": active_slot,
            "target_slot": target_slot,
            "rollback_slot": active_slot,
            "slot_state_path": str(slot_state_path),
            "staged_dir": str(stage_dir),
            "staged_files": staged_files,
            "backup": backup_receipt,
            "signature_verify": verify,
            "physical_flash": physical_summary,
            "restart_required": True,
        }
        save_json(report_path, out)
        return out

    physical_policy_path = Path(
        str(
            ((plan.get("physical_flash_executor") or {}).get("policy_path"))
            or (FW_BASE / "policy" / "physical_flash_executor_policy_v1.json")
        )
    )
    physical_policy_obj, physical_policy_from_file = load_physical_flash_policy(
        policy_path=physical_policy_path,
        capability_graph=plan.get("capability_graph", {}) if isinstance(plan.get("capability_graph"), dict) else {},
    )
    gate = evaluate_physical_flash_request(
        plan=plan,
        policy=physical_policy_obj,
        backup_receipt=backup_receipt,
        active_slot=active_slot,
        target_slot=target_slot,
    )
    physical_summary.update(
        {
            "effective": bool(gate.get("ok")),
            "status": str(gate.get("status") or ("authorized" if bool(gate.get("ok")) else "denied")),
            "policy_path": str(physical_policy_path),
            "policy_loaded_from_file": bool(physical_policy_from_file),
            "policy_id": str(physical_policy_obj.get("policy_id") or ""),
            "gate": gate,
        }
    )
    if not bool(gate.get("ok")):
        state["pending_slot_on_reboot"] = None
        state["physical_flash_last_error"] = {
            "code": str(gate.get("code") or "FW_REWRITE_PHYSICAL_FLASH_DENIED"),
            "reason": str(gate.get("reason") or ""),
            "utc": now_iso(),
        }
        save_json(slot_state_path, state)
        out = {
            "ok": False,
            "code": str(gate.get("code") or "FW_REWRITE_PHYSICAL_FLASH_DENIED"),
            "plan_path": str(plan_path),
            "signature_path": str(signature_path),
            "report_path": str(report_path),
            "active_slot": active_slot,
            "target_slot": target_slot,
            "rollback_slot": active_slot,
            "slot_state_path": str(slot_state_path),
            "staged_dir": str(stage_dir),
            "staged_files": staged_files,
            "backup": backup_receipt,
            "signature_verify": verify,
            "physical_flash": physical_summary,
            "restart_required": False,
        }
        save_json(report_path, out)
        return out

    physical_exec = execute_controlled_physical_flash(
        plan=plan,
        policy=physical_policy_obj,
        stage_dir=stage_dir,
        backup_receipt=backup_receipt,
        active_slot=active_slot,
        target_slot=target_slot,
    )
    physical_summary["execution"] = physical_exec
    physical_summary["status"] = str(physical_exec.get("status") or physical_summary.get("status") or "")
    if not bool(physical_exec.get("ok")):
        state["pending_slot_on_reboot"] = None
        state["physical_flash_last_error"] = {
            "code": str(physical_exec.get("code") or "FW_REWRITE_PHYSICAL_FLASH_EXECUTION_FAILED"),
            "utc": now_iso(),
            "execution": physical_exec,
        }
        save_json(slot_state_path, state)
        out = {
            "ok": False,
            "code": str(physical_exec.get("code") or "FW_REWRITE_PHYSICAL_FLASH_EXECUTION_FAILED"),
            "plan_path": str(plan_path),
            "signature_path": str(signature_path),
            "report_path": str(report_path),
            "active_slot": active_slot,
            "target_slot": target_slot,
            "rollback_slot": active_slot,
            "slot_state_path": str(slot_state_path),
            "staged_dir": str(stage_dir),
            "staged_files": staged_files,
            "backup": backup_receipt,
            "signature_verify": verify,
            "physical_flash": physical_summary,
            "restart_required": False,
        }
        save_json(report_path, out)
        return out

    state["pending_slot_on_reboot"] = target_slot
    state["physical_flash_last_success"] = {
        "code": str(physical_exec.get("code") or "FW_REWRITE_PHYSICAL_FLASH_OK"),
        "utc": now_iso(),
        "execution": physical_exec,
    }
    save_json(slot_state_path, state)
    out = {
        "ok": True,
        "code": "FW_REWRITE_PHYSICAL_FLASH_CONTROLLED_PENDING_REBOOT",
        "plan_path": str(plan_path),
        "signature_path": str(signature_path),
        "report_path": str(report_path),
        "active_slot": active_slot,
        "target_slot": target_slot,
        "rollback_slot": active_slot,
        "slot_state_path": str(slot_state_path),
        "staged_dir": str(stage_dir),
        "staged_files": staged_files,
        "backup": backup_receipt,
        "signature_verify": verify,
        "physical_flash": physical_summary,
        "restart_required": True,
    }
    save_json(report_path, out)
    return out
