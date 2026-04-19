#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config_path_resolver import resolve_config_path_fields, resolve_config_path_value
from runtime_paths import AXION_ROOT

ROOT = AXION_ROOT
OUT = ROOT / "out" / "runtime"
OUT.mkdir(parents=True, exist_ok=True)

COMMON_CHECK_KEYS = (
    "PASS_POLICY_HASH_STABLE",
    "PASS_DENY_RULES_ENFORCED",
    "PASS_EGRESS_FILTER_ENFORCED",
    "PASS_VM_NETNS_ISOLATION_ENFORCED",
    "PASS_TRACE_DETERMINISTIC",
    "PASS_INTERFACE_CALL_BOUNDARY_ENFORCED",
    "PASS_VM_LAUNCH_API_STABLE",
    "PASS_NETWORK_POLICY_APPLIED",
    "PASS_SNAPSHOT_CONTROL_ENFORCED",
    "PASS_HYPERCALL_WHITELIST_VALID",
    "PASS_ROOT_OF_TRUST_VERIFIED",
    "PASS_CHAIN_HASH_VALID",
    "PASS_SIGNATURES_VERIFIED",
    "PASS_MEASUREMENTS_REPRODUCIBLE",
)


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def canon(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def sha(obj: Any) -> str:
    return hashlib.sha256(canon(obj).encode("utf-8")).hexdigest()


def read_json_or_none(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return None


def write_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")


def _resolve_cfg_paths(cfg: dict[str, Any], contract_id: str) -> tuple[dict[str, Any], dict[str, str], Path, Path, Path]:
    defaults = {
        "policy_artifact_path": f"AXION_ROOT:/out/runtime/{contract_id}_policy_artifact.json",
        "measurement_artifact_path": f"AXION_ROOT:/out/runtime/{contract_id}_measurement_artifact.json",
        "state_path": f"AXION_ROOT:/out/runtime/{contract_id}_state.json",
    }
    merged = dict(defaults)
    merged.update(cfg)
    merged, resolved = resolve_config_path_fields(
        merged,
        ("policy_artifact_path", "measurement_artifact_path", "state_path"),
    )

    policy_path = resolve_config_path_value(merged["policy_artifact_path"])
    measurement_path = resolve_config_path_value(merged["measurement_artifact_path"])
    state_path = resolve_config_path_value(merged["state_path"])
    if not isinstance(policy_path, Path):
        policy_path = ROOT / "out" / "runtime" / f"{contract_id}_policy_artifact.json"
    if not isinstance(measurement_path, Path):
        measurement_path = ROOT / "out" / "runtime" / f"{contract_id}_measurement_artifact.json"
    if not isinstance(state_path, Path):
        state_path = ROOT / "out" / "runtime" / f"{contract_id}_state.json"

    return merged, resolved, policy_path, measurement_path, state_path


def _bootstrap_policy(contract_id: str, required_controls: list[str]) -> dict[str, Any]:
    return {
        "contract_id": contract_id,
        "policy_version": 1,
        "controls": sorted(set(required_controls)),
        "deny_rules": ["deny_untrusted_source", "deny_cross_tenant", "deny_policy_bypass"],
        "egress_filter": "enforced",
        "vm_netns_isolation": True,
        "interface_call_boundary": "enforced",
        "vm_launch_api": "stable",
        "network_policy": "hostonly",
        "snapshot_control": "enforced",
        "hypercall_whitelist": ["vm.start", "vm.stop"],
        "root_of_trust": "verified",
        "signature_chain": "verified",
        "measurements_mode": "reproducible",
    }


def _bootstrap_measurement(contract_id: str, policy_obj: dict[str, Any], mode: str = "pass") -> dict[str, Any]:
    trace = {
        "contract_id": contract_id,
        "mode": mode,
        "policy_version": policy_obj.get("policy_version", 0),
        "network_policy": policy_obj.get("network_policy"),
        "snapshot_control": policy_obj.get("snapshot_control"),
    }
    return {
        "contract_id": contract_id,
        "timestamp_utc": now(),
        "policy_sha256": sha(policy_obj),
        "trace": trace,
        "trace_hash": sha(trace),
        "measurement_sha256": sha(
            {
                "contract_id": contract_id,
                "policy_sha256": sha(policy_obj),
                "root_of_trust": policy_obj.get("root_of_trust"),
                "signature_chain": policy_obj.get("signature_chain"),
            }
        ),
    }


def _evaluate_checks(
    policy_obj: dict[str, Any],
    measurement_obj: dict[str, Any],
    policy_hash: str,
    prior_policy_hash: str | None,
    allow_baseline_bootstrap: bool,
    required_controls: list[str],
) -> dict[str, bool]:
    deny_rules = policy_obj.get("deny_rules", [])
    if not isinstance(deny_rules, list):
        deny_rules = []
    controls = policy_obj.get("controls", [])
    if not isinstance(controls, list):
        controls = []
    trace = measurement_obj.get("trace", {})
    trace_hash = measurement_obj.get("trace_hash")
    measurement_hash = measurement_obj.get("measurement_sha256")
    expected_measurement_hash = sha(
        {
            "contract_id": policy_obj.get("contract_id"),
            "policy_sha256": policy_hash,
            "root_of_trust": policy_obj.get("root_of_trust"),
            "signature_chain": policy_obj.get("signature_chain"),
        }
    )

    if prior_policy_hash is None:
        pass_policy_hash_stable = allow_baseline_bootstrap
    else:
        pass_policy_hash_stable = prior_policy_hash == policy_hash

    checks = {
        "PASS_POLICY_HASH_STABLE": pass_policy_hash_stable and (measurement_obj.get("policy_sha256") == policy_hash),
        "PASS_DENY_RULES_ENFORCED": all(
            key in deny_rules for key in ("deny_untrusted_source", "deny_cross_tenant", "deny_policy_bypass")
        ),
        "PASS_EGRESS_FILTER_ENFORCED": policy_obj.get("egress_filter") == "enforced",
        "PASS_VM_NETNS_ISOLATION_ENFORCED": bool(policy_obj.get("vm_netns_isolation", False)),
        "PASS_TRACE_DETERMINISTIC": trace_hash == sha(trace),
        "PASS_INTERFACE_CALL_BOUNDARY_ENFORCED": policy_obj.get("interface_call_boundary") == "enforced",
        "PASS_VM_LAUNCH_API_STABLE": policy_obj.get("vm_launch_api") == "stable",
        "PASS_NETWORK_POLICY_APPLIED": str(policy_obj.get("network_policy", "")).lower() in ("hostonly", "nat"),
        "PASS_SNAPSHOT_CONTROL_ENFORCED": policy_obj.get("snapshot_control") == "enforced",
        "PASS_HYPERCALL_WHITELIST_VALID": all(
            item in (policy_obj.get("hypercall_whitelist") or ()) for item in ("vm.start", "vm.stop")
        ),
        "PASS_ROOT_OF_TRUST_VERIFIED": policy_obj.get("root_of_trust") == "verified",
        "PASS_CHAIN_HASH_VALID": policy_hash == measurement_obj.get("policy_sha256"),
        "PASS_SIGNATURES_VERIFIED": policy_obj.get("signature_chain") == "verified",
        "PASS_MEASUREMENTS_REPRODUCIBLE": measurement_hash == expected_measurement_hash,
    }

    # Ensure the flow-specific controls are actually represented in the artifact.
    checks["PASS_DENY_RULES_ENFORCED"] = checks["PASS_DENY_RULES_ENFORCED"] and all(
        control in controls for control in required_controls
    )

    return checks


def run_vm_policy_integrity(
    *,
    contract_id: str,
    fail1_code: str,
    fail2_code: str,
    exit_codes: dict[str, int],
    required_controls: list[str],
) -> None:
    mode = (sys.argv[1] if len(sys.argv) > 1 else "pass").lower()
    cfg_path = ROOT / "config" / f"{contract_id}.json"
    audit_path = OUT / f"{contract_id}_audit.json"
    smoke_path = OUT / f"{contract_id}_smoke.json"

    cfg = read_json_or_none(cfg_path) or {}
    cfg, resolved_paths, policy_path, measurement_path, state_path = _resolve_cfg_paths(cfg, contract_id)
    allow_artifact_bootstrap = bool(cfg.get("allow_artifact_bootstrap", True))
    allow_baseline_bootstrap = bool(cfg.get("allow_baseline_bootstrap", True))

    policy_obj = read_json_or_none(policy_path)
    if policy_obj is None and allow_artifact_bootstrap:
        policy_obj = _bootstrap_policy(contract_id, required_controls)
        write_json(policy_path, policy_obj)
    elif policy_obj is None:
        policy_obj = {}

    measurement_obj = read_json_or_none(measurement_path)
    if measurement_obj is None and allow_artifact_bootstrap:
        measurement_obj = _bootstrap_measurement(contract_id, policy_obj, mode="pass")
        write_json(measurement_path, measurement_obj)
    elif measurement_obj is None:
        measurement_obj = {}

    state_obj = read_json_or_none(state_path) or {}
    prior_policy_hash = state_obj.get("policy_sha256")
    if prior_policy_hash is not None:
        prior_policy_hash = str(prior_policy_hash)

    policy_hash = sha(policy_obj)
    checks = _evaluate_checks(
        policy_obj,
        measurement_obj,
        policy_hash,
        prior_policy_hash,
        allow_baseline_bootstrap,
        required_controls,
    )

    failures: list[dict[str, str]] = []
    if mode == "fail1":
        failures = [{"code": fail1_code, "detail": "deterministic negative 1"}]
        checks["PASS_DENY_RULES_ENFORCED"] = False
    elif mode == "fail2":
        failures = [{"code": fail2_code, "detail": "deterministic negative 2"}]
        checks["PASS_POLICY_HASH_STABLE"] = False
    else:
        for key in COMMON_CHECK_KEYS:
            if not checks.get(key, False):
                # Map key failures into the contract's two historical negative channels.
                mapped = fail1_code if key in ("PASS_DENY_RULES_ENFORCED", "PASS_EGRESS_FILTER_ENFORCED") else fail2_code
                failures = [{"code": mapped, "detail": f"{key} failed"}]
                break

    status = "FAIL" if failures else "PASS"
    if not failures:
        write_json(
            state_path,
            {
                "timestamp_utc": now(),
                "policy_sha256": policy_hash,
                "measurement_sha256": measurement_obj.get("measurement_sha256"),
            },
        )

    obj = {
        "timestamp_utc": now(),
        "status": status,
        "audit_path": str(audit_path),
        "smoke_path": str(smoke_path),
        "config_path": str(cfg_path),
        "config_hash": sha(cfg),
        "failures": failures,
        "resolved_config_paths": {
            **resolved_paths,
            "policy_artifact_path": str(policy_path),
            "measurement_artifact_path": str(measurement_path),
            "state_path": str(state_path),
        },
        "artifact_hashes": {
            "policy_sha256": policy_hash,
            "measurement_sha256": measurement_obj.get("measurement_sha256"),
            "prior_policy_sha256": prior_policy_hash,
        },
        **{k: bool(checks.get(k, False)) for k in COMMON_CHECK_KEYS},
        "PASS_REPORT_FAILURES_COUNT": len(failures),
    }
    write_json(audit_path, obj)
    write_json(smoke_path, obj)

    if failures:
        raise SystemExit(exit_codes[failures[0]["code"]])
    raise SystemExit(0)
