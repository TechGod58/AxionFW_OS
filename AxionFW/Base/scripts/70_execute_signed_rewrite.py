#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from fw_rewrite_engine import FW_BASE, execute_rewrite_plan


def main() -> None:
    parser = argparse.ArgumentParser(description="Execute signed firmware rewrite plan with backup + A/B stage + rollback protection")
    parser.add_argument("--plan", default="", help="Rewrite plan path")
    parser.add_argument("--signature", default="", help="Rewrite signature path")
    parser.add_argument("--out-report", default="", help="Execution report path")
    parser.add_argument("--allow-physical-flash", action="store_true", help="Request physical flash path (still policy-gated)")
    args = parser.parse_args()

    plan_path = Path(args.plan).resolve() if str(args.plan).strip() else (FW_BASE / "out" / "rewrite" / "rewrite_plan_v1.json")
    sig_path = Path(args.signature).resolve() if str(args.signature).strip() else (FW_BASE / "out" / "rewrite" / "rewrite_signature_v1.json")
    report_path = (
        Path(args.out_report).resolve()
        if str(args.out_report).strip()
        else (FW_BASE / "out" / "rewrite" / "rewrite_execution_report.json")
    )

    out = execute_rewrite_plan(
        plan_path=plan_path,
        signature_path=sig_path,
        report_path=report_path,
        allow_physical_flash=bool(args.allow_physical_flash),
    )
    result = {
        "ok": bool(out.get("ok")),
        "code": str(out.get("code") or ""),
        "plan_path": str(plan_path),
        "signature_path": str(sig_path),
        "report_path": str(report_path),
        "rollback_slot": str(out.get("rollback_slot") or ""),
        "target_slot": str(out.get("target_slot") or ""),
        "physical_flash_requested": bool(((out.get("physical_flash") or {}).get("requested"))),
        "physical_flash_status": str(((out.get("physical_flash") or {}).get("status") or "")),
    }
    print(json.dumps(result, indent=2))
    if not bool(out.get("ok")):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
