#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from fw_rewrite_engine import FW_BASE, build_rewrite_plan, find_latest_json, load_json, save_json, sign_rewrite_plan


def main() -> None:
    parser = argparse.ArgumentParser(description="Plan and sign firmware rewrite execution")
    parser.add_argument("--graph", default="", help="Capability graph path. Defaults to out/rewrite/capability_graph_v1.json")
    parser.add_argument("--pending-bios-settings", default="", help="Pending BIOS settings path")
    parser.add_argument("--out-plan", default="", help="Rewrite plan output path")
    parser.add_argument("--out-signature", default="", help="Rewrite signature output path")
    parser.add_argument("--source-commit-sha", default="0000000000000000000000000000000000000000", help="Source commit sha for provenance")
    parser.add_argument("--build-pipeline-id", default="axion-firmware-rewrite-engine", help="Build pipeline id for provenance")
    parser.add_argument("--trusted-key-id", default="", help="Optional trusted key id override")
    args = parser.parse_args()

    graph_path = Path(args.graph).resolve() if str(args.graph).strip() else (FW_BASE / "out" / "rewrite" / "capability_graph_v1.json")
    if not graph_path.exists():
        graph_path = find_latest_json(FW_BASE / "out" / "rewrite", pattern="*capability_graph*.json")

    pending_bios = (
        Path(args.pending_bios_settings).resolve()
        if str(args.pending_bios_settings).strip()
        else (FW_BASE / "out" / "handoff" / "pending_bios_settings_v1.json")
    )
    out_plan = Path(args.out_plan).resolve() if str(args.out_plan).strip() else (FW_BASE / "out" / "rewrite" / "rewrite_plan_v1.json")
    out_sig = Path(args.out_signature).resolve() if str(args.out_signature).strip() else (FW_BASE / "out" / "rewrite" / "rewrite_signature_v1.json")

    graph = load_json(graph_path, {})
    if not isinstance(graph, dict) or not graph:
        raise SystemExit(f"Invalid capability graph payload: {graph_path}")

    plan = build_rewrite_plan(
        fw_base=FW_BASE,
        capability_graph=graph,
        pending_bios_settings_path=pending_bios,
        rewrite_plan_path=out_plan,
    )
    save_json(out_plan, plan)
    signature = sign_rewrite_plan(
        plan_path=out_plan,
        signature_path=out_sig,
        source_commit_sha=str(args.source_commit_sha).strip().lower() or "0000000000000000000000000000000000000000",
        build_pipeline_id=str(args.build_pipeline_id).strip() or "axion-firmware-rewrite-engine",
        trusted_key_id=(str(args.trusted_key_id).strip() or None),
    )

    result = {
        "ok": bool(signature.get("ok")),
        "code": "AXION_FW_REWRITE_PLAN_SIGNED" if bool(signature.get("ok")) else str(signature.get("code") or "AXION_FW_REWRITE_PLAN_SIGN_FAIL"),
        "graph_path": str(graph_path),
        "pending_bios_settings_path": str(pending_bios),
        "plan_path": str(out_plan),
        "signature_path": str(out_sig),
        "adapter_id": str(((plan.get("rewrite_adapter") or {}).get("adapter_id") or "")),
        "target_slot": str(((plan.get("slots") or {}).get("target_slot") or "")),
        "signature": signature,
    }
    print(json.dumps(result, indent=2))
    if not bool(signature.get("ok")):
        raise SystemExit(1)


if __name__ == "__main__":
    main()

