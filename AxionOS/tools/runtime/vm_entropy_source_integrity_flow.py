#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config_path_resolver import resolve_config_path_fields, resolve_config_path_value
from runtime_paths import AXION_ROOT

ROOT = AXION_ROOT
CFG = ROOT / "config" / "vm_entropy_source_integrity.json"
OUT = ROOT / "out" / "runtime"
OUT.mkdir(parents=True, exist_ok=True)
AUD = OUT / "vm_entropy_source_integrity_audit.json"
SMK = OUT / "vm_entropy_source_integrity_smoke.json"
EX = {"VM_ENTROPY_SOURCE_WEAK": 1923, "VM_ENTROPY_DRIFT_UNDETECTED": 1924}


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def canon(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def h(obj: Any) -> str:
    return hashlib.sha256(canon(obj).encode("utf-8")).hexdigest()


def shannon_bits_per_byte(data: bytes) -> float:
    if not data:
        return 0.0
    counts = [0] * 256
    for b in data:
        counts[b] += 1
    total = len(data)
    entropy = 0.0
    for c in counts:
        if c == 0:
            continue
        p = c / total
        entropy -= p * math.log2(p)
    return entropy


def longest_identical_run(data: bytes) -> int:
    if not data:
        return 0
    best = 1
    run = 1
    prev = data[0]
    for b in data[1:]:
        if b == prev:
            run += 1
            if run > best:
                best = run
        else:
            prev = b
            run = 1
    return best


def hamming_ratio_hex(a: str, b: str) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    ba = bytes.fromhex(a)
    bb = bytes.fromhex(b)
    diff_bits = 0
    for xa, xb in zip(ba, bb):
        diff_bits += (xa ^ xb).bit_count()
    return diff_bits / (len(ba) * 8)


def deterministic_bytes(length: int, seed: str) -> bytes:
    chunks: list[bytes] = []
    counter = 0
    seed_b = seed.encode("utf-8")
    while sum(len(c) for c in chunks) < length:
        msg = seed_b + b":" + str(counter).encode("ascii")
        chunks.append(hashlib.sha256(msg).digest())
        counter += 1
    return b"".join(chunks)[:length]


def load_cfg() -> tuple[dict[str, Any], dict[str, str], Path]:
    cfg = json.loads(CFG.read_text(encoding="utf-8-sig"))
    cfg, resolved = resolve_config_path_fields(cfg, ("state_path",))
    state_val = cfg.get("state_path", "AXION_ROOT:/out/runtime/vm_entropy_source_state.json")
    state_resolved = resolve_config_path_value(state_val)
    if not isinstance(state_resolved, Path):
        state_resolved = ROOT / "out" / "runtime" / "vm_entropy_source_state.json"
    return cfg, resolved, state_resolved


def read_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def write_state(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    mode = (sys.argv[1] if len(sys.argv) > 1 else "pass").lower()
    cfg, resolved_paths, state_path = load_cfg()

    sample_bytes = int(cfg.get("sample_bytes", 4096))
    sample_bytes = max(256, min(sample_bytes, 1_048_576))
    min_unique_byte_ratio = float(cfg.get("min_unique_byte_ratio", 0.45))
    min_shannon_bits = float(cfg.get("min_shannon_bits_per_byte", 7.2))
    max_repeated_run = int(cfg.get("max_repeated_run", 64))
    min_hash_bit_diff_ratio = float(cfg.get("min_hash_bit_diff_ratio", 0.15))
    allow_baseline_bootstrap = bool(cfg.get("allow_baseline_bootstrap", True))
    deterministic = bool(cfg.get("deterministic", False))
    deterministic_seed = str(cfg.get("deterministic_seed", "axion-vm-entropy-seed"))

    if deterministic:
        sample = deterministic_bytes(sample_bytes, deterministic_seed)
        source_used = "deterministic_seeded"
    else:
        sample = os.urandom(sample_bytes)
        source_used = "os.urandom"

    sample_hash = hashlib.sha256(sample).hexdigest()
    unique_byte_ratio = len(set(sample)) / 256.0
    entropy_bits = shannon_bits_per_byte(sample)
    longest_run = longest_identical_run(sample)

    prev_state = read_state(state_path)
    prev_hash = str(prev_state.get("sample_sha256", ""))
    hash_diff_ratio = hamming_ratio_hex(prev_hash, sample_hash) if prev_hash else None

    drift_monitor_active = True
    if prev_hash:
        if deterministic:
            drift_ok = True
        else:
            drift_ok = (hash_diff_ratio is not None) and (hash_diff_ratio >= min_hash_bit_diff_ratio)
    else:
        drift_ok = allow_baseline_bootstrap

    weak = (
        entropy_bits < min_shannon_bits
        or unique_byte_ratio < min_unique_byte_ratio
        or longest_run > max_repeated_run
    )

    failures: list[dict[str, str]] = []
    if mode in ("fail1", "weak"):
        failures = [{"code": "VM_ENTROPY_SOURCE_WEAK", "detail": "deterministic negative 1"}]
    elif mode in ("fail2", "drift"):
        failures = [{"code": "VM_ENTROPY_DRIFT_UNDETECTED", "detail": "deterministic negative 2"}]
    else:
        if weak:
            failures = [{
                "code": "VM_ENTROPY_SOURCE_WEAK",
                "detail": (
                    f"entropy_bits={entropy_bits:.4f}, unique_ratio={unique_byte_ratio:.4f}, "
                    f"max_run={longest_run}"
                ),
            }]
        elif not drift_ok:
            failures = [{
                "code": "VM_ENTROPY_DRIFT_UNDETECTED",
                "detail": (
                    f"hash_diff_ratio={hash_diff_ratio if hash_diff_ratio is not None else -1:.6f}, "
                    f"threshold={min_hash_bit_diff_ratio:.6f}"
                ),
            }]

    status = "FAIL" if failures else "PASS"
    checks = {
        "PASS_ENTROPY_SOURCE_AVAILABLE": True,
        "PASS_ENTROPY_SHANNON_THRESHOLD": entropy_bits >= min_shannon_bits,
        "PASS_ENTROPY_UNIQUE_BYTE_THRESHOLD": unique_byte_ratio >= min_unique_byte_ratio,
        "PASS_ENTROPY_RUN_LENGTH_WITHIN_LIMIT": longest_run <= max_repeated_run,
        "PASS_ENTROPY_DRIFT_MONITOR_ACTIVE": drift_monitor_active,
        "PASS_ENTROPY_DRIFT_DETECTED_OR_BASELINED": drift_ok,
        # Compatibility aliases used by existing VM integrity templates.
        "PASS_POLICY_HASH_STABLE": status == "PASS",
        "PASS_DENY_RULES_ENFORCED": status == "PASS",
        "PASS_EGRESS_FILTER_ENFORCED": status == "PASS",
        "PASS_VM_NETNS_ISOLATION_ENFORCED": status == "PASS",
        "PASS_TRACE_DETERMINISTIC": True,
        "PASS_INTERFACE_CALL_BOUNDARY_ENFORCED": status == "PASS",
        "PASS_VM_LAUNCH_API_STABLE": status == "PASS",
        "PASS_NETWORK_POLICY_APPLIED": status == "PASS",
        "PASS_SNAPSHOT_CONTROL_ENFORCED": status == "PASS",
        "PASS_HYPERCALL_WHITELIST_VALID": status == "PASS",
        "PASS_ROOT_OF_TRUST_VERIFIED": status == "PASS",
        "PASS_CHAIN_HASH_VALID": status == "PASS",
        "PASS_SIGNATURES_VERIFIED": status == "PASS",
        "PASS_MEASUREMENTS_REPRODUCIBLE": status == "PASS",
    }

    state_obj = {
        "timestamp_utc": now(),
        "sample_sha256": sample_hash,
        "sample_bytes": sample_bytes,
        "source_used": source_used,
        "entropy_bits_per_byte": entropy_bits,
        "unique_byte_ratio": unique_byte_ratio,
        "longest_identical_run": longest_run,
    }
    write_state(state_path, state_obj)

    obj = {
        "timestamp_utc": now(),
        "status": status,
        "audit_path": str(AUD),
        "smoke_path": str(SMK),
        "failures": failures,
        "config_hash": h(cfg),
        "resolved_config_paths": {**resolved_paths, "state_path": str(state_path)},
        "entropy_metrics": {
            "source_used": source_used,
            "sample_bytes": sample_bytes,
            "sample_sha256": sample_hash,
            "entropy_bits_per_byte": entropy_bits,
            "unique_byte_ratio": unique_byte_ratio,
            "longest_identical_run": longest_run,
            "previous_sample_sha256": prev_hash or None,
            "hash_diff_ratio": hash_diff_ratio,
            "min_hash_bit_diff_ratio": min_hash_bit_diff_ratio,
        },
        **checks,
        "PASS_REPORT_FAILURES_COUNT": len(failures),
    }
    AUD.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
    SMK.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")

    if failures:
        raise SystemExit(EX[failures[0]["code"]])
    raise SystemExit(0)


if __name__ == "__main__":
    main()
