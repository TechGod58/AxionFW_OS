#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

TOOLS_DIR = Path(__file__).resolve().parent.parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.append(str(TOOLS_DIR))

from common.pathing import axion_path

OUT_QA = axion_path("out", "qa")
OUT_QA.mkdir(parents=True, exist_ok=True)
OUT_RUNTIME = axion_path("out", "runtime")
REPORT = OUT_QA / "ml_security_sidecar_report.json"
STATE = OUT_RUNTIME / "ml_security_sidecar_state.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def truthy(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in ("1", "true", "yes", "on")


def write_report(obj: dict[str, Any]) -> None:
    REPORT.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")


def read_json_or_none(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return None


def collect_security_corpus() -> str:
    prefixes = (
        "identity_access_integrity",
        "secrets_handling_integrity",
        "vm_entropy_source_integrity",
        "virtual_network_policy_integrity",
        "vm_attestation_quote_integrity",
        "vm_console_channel_integrity",
        "vm_device_passthrough_integrity",
        "vm_disk_encryption_integrity",
        "vm_guest_tools_channel_integrity",
        "vm_image_registry_integrity",
        "vm_kernel_cmdline_lock_integrity",
        "vm_memory_scrub_integrity",
        "vm_snapshot_restore_isolation_integrity",
        "vm_time_sync_tamper_integrity",
    )
    lines: list[str] = []
    for prefix in prefixes:
        p = OUT_RUNTIME / f"{prefix}_audit.json"
        obj = read_json_or_none(p) or {}
        status = obj.get("status", "UNKNOWN")
        failure_codes = []
        for item in obj.get("failures", []):
            if isinstance(item, dict):
                code = item.get("code")
                if code:
                    failure_codes.append(str(code))
        lines.append(f"{prefix} status={status} failures={','.join(failure_codes) if failure_codes else 'none'}")
    return "\n".join(lines) + "\n"


def estimate_char_perplexity_fallback(corpus: str) -> float:
    data = corpus.encode("utf-8", errors="ignore")
    if not data:
        return 1.0
    counts = Counter(data)
    total = float(len(data))
    # Add-one smoothing keeps deterministic finite perplexity even on tiny corpora.
    vocab = float(len(counts))
    denom = total + vocab
    nll = 0.0
    for byte in data:
        prob = (counts[byte] + 1.0) / denom
        nll += -math.log(prob)
    return math.exp(nll / total)


def main() -> None:
    enabled = truthy(os.getenv("AXION_ENABLE_ML_SIDECAR"))
    if not enabled:
        result = {
            "timestamp_utc": now_iso(),
            "status": "SKIPPED",
            "ok": True,
            "reason": "feature_flag_disabled",
            "feature_flag": "AXION_ENABLE_ML_SIDECAR",
        }
        write_report(result)
        print(json.dumps(result, indent=2))
        raise SystemExit(0)

    source_dir = Path(
        os.getenv("AXION_ML_SOURCE_DIR", r"C:\Users\Axion Industries\Desktop")
    )
    sys.path.append(str(source_dir))

    corpus = collect_security_corpus()
    history_steps = 0
    backend = "char_ngram_fallback"
    backend_error = None
    try:
        import torch
        from entropy_proof_backbone import TrainerConfig
        from autoregressive_next_token import (
            build_char_dataloader,
            build_autoregressive_fibonacci_lm,
            train_autoregressive_model,
            estimate_perplexity,
        )

        loader, tokenizer = build_char_dataloader(
            corpus,
            seq_len=32,
            batch_size=4,
            stride=16,
            shuffle=False,
        )
        model = build_autoregressive_fibonacci_lm(
            vocab_size=tokenizer.vocab_size,
            max_seq_len=32,
            embed_dim=32,
            depth=2,
            start_dim=32,
            blocks_per_stage=1,
            max_width=64,
        )
        trainer, history = train_autoregressive_model(
            model,
            loader,
            epochs=1,
            learning_rate=5e-4,
            weight_decay=0.0,
            trainer_config=TrainerConfig(warmup_steps=0, grad_spike_threshold=1e6),
            device=torch.device("cpu"),
            log_every=0,
        )
        perplexity = estimate_perplexity(trainer.model, loader, torch.device("cpu"))
        history_steps = len(history)
        backend = "torch_backbone"
    except Exception as exc:
        # Deterministic fallback keeps the release lane enforceable when optional ML deps are missing.
        perplexity = estimate_char_perplexity_fallback(corpus)
        backend_error = str(exc)

    prev = read_json_or_none(STATE) or {}
    baseline = float(prev.get("perplexity", perplexity))
    threshold = float(os.getenv("AXION_ML_SIDECAR_ANOMALY_FACTOR", "1.35"))
    anomaly = perplexity > (baseline * threshold)
    enforce = truthy(os.getenv("AXION_ML_SIDECAR_ENFORCE"))

    state_obj = {
        "timestamp_utc": now_iso(),
        "perplexity": perplexity,
        "history_steps": history_steps,
        "baseline_perplexity_used": baseline,
        "backend": backend,
    }
    STATE.write_text(json.dumps(state_obj, indent=2) + "\n", encoding="utf-8")

    result = {
        "timestamp_utc": now_iso(),
        "status": "PASS" if not anomaly else ("FAIL" if enforce else "WARN"),
        "ok": (not anomaly) or (not enforce),
        "ml_source_dir": str(source_dir),
        "feature_flag": "AXION_ENABLE_ML_SIDECAR",
        "enforce_flag": "AXION_ML_SIDECAR_ENFORCE",
        "anomaly_detected": anomaly,
        "anomaly_threshold_factor": threshold,
        "perplexity": perplexity,
        "baseline_perplexity": baseline,
        "history_steps": history_steps,
        "backend": backend,
        "backend_error": backend_error,
    }
    write_report(result)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["ok"] else 2)


if __name__ == "__main__":
    main()
