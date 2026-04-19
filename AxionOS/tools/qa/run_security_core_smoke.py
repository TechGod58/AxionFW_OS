#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

TOOLS_DIR = Path(__file__).resolve().parent.parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.append(str(TOOLS_DIR))

from common.pathing import axion_path

OUT = axion_path("out", "qa")
OUT.mkdir(parents=True, exist_ok=True)
RUNTIME_OUT = axion_path("out", "runtime")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json_or_none(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return None


def run_flow(flow_name: str, mode: str, expected_exit: int, expected_code: str | None) -> dict[str, Any]:
    script = axion_path("tools", "runtime", f"{flow_name}_flow.py")
    smoke = RUNTIME_OUT / f"{flow_name}_smoke.json"
    audit = RUNTIME_OUT / f"{flow_name}_audit.json"

    cmd = ["python", str(script), mode]
    p = subprocess.run(cmd, capture_output=True, text=True)
    smoke_obj = read_json_or_none(smoke)
    audit_obj = read_json_or_none(audit)

    observed_code = None
    if smoke_obj:
        failures = smoke_obj.get("failures", [])
        if isinstance(failures, list) and failures:
            first = failures[0]
            if isinstance(first, dict):
                observed_code = first.get("code")

    ok_exit = p.returncode == expected_exit
    ok_code = observed_code == expected_code
    if expected_code is None:
        ok_code = observed_code is None
    ok_status = (smoke_obj or {}).get("status") == ("PASS" if expected_exit == 0 else "FAIL")

    return {
        "flow": flow_name,
        "mode": mode,
        "expected_exit": expected_exit,
        "actual_exit": p.returncode,
        "expected_code": expected_code,
        "actual_code": observed_code,
        "smoke_path": str(smoke),
        "audit_path": str(audit),
        "stdout_tail": (p.stdout or "").strip()[-400:],
        "stderr_tail": (p.stderr or "").strip()[-400:],
        "ok": bool(ok_exit and ok_code and ok_status and smoke_obj is not None and audit_obj is not None),
    }


def main() -> None:
    plan = [
        ("identity_access_integrity", "pass", 0, None),
        ("identity_access_integrity", "token_forged", 681, "IDENTITY_TOKEN_FORGED"),
        ("identity_access_integrity", "policy_bypass", 682, "ACCESS_POLICY_BYPASS"),
        ("secrets_handling_integrity", "pass", 0, None),
        ("secrets_handling_integrity", "exposed_in_log", 541, "SECRET_EXPOSED_IN_LOG"),
        ("secrets_handling_integrity", "storage_unencrypted", 542, "SECRET_STORAGE_UNENCRYPTED"),
        ("vm_entropy_source_integrity", "pass", 0, None),
        ("vm_entropy_source_integrity", "fail1", 1923, "VM_ENTROPY_SOURCE_WEAK"),
        ("vm_entropy_source_integrity", "fail2", 1924, "VM_ENTROPY_DRIFT_UNDETECTED"),
        ("firewall_guard_integrity", "pass", 0, None),
        ("firewall_guard_integrity", "unauthorized_host", 3601, "FIREWALL_PACKET_QUARANTINED"),
        ("firewall_guard_integrity", "flow_mismatch", 3602, "FIREWALL_FLOW_PROFILE_MISMATCH"),
        ("firewall_guard_integrity", "rule_precedence", 3603, "FIREWALL_RULE_PRECEDENCE_BROKEN"),
        ("firewall_guard_integrity", "pid_mismatch", 3604, "FIREWALL_PID_CORRELATION_ENFORCED"),
        ("firewall_guard_integrity", "correlated_stream_missing", 3605, "FIREWALL_CORRELATED_STREAM_REQUIRED"),
        ("qm_ecc_integrity", "pass", 0, None),
        ("qm_ecc_integrity", "halt_action", 3611, "QM_ECC_HALT_REQUIRED"),
        ("qm_ecc_integrity", "rollback_action", 3612, "QM_ECC_ROLLBACK_REQUIRED"),
    ]

    results = [run_flow(*item) for item in plan]
    passed = sum(1 for r in results if r["ok"])
    failed = len(results) - passed

    summary = {
        "ts": now_iso(),
        "suite": "security_core_smoke",
        "total": len(results),
        "passed": passed,
        "failed": failed,
        "ok": failed == 0,
        "results": results,
    }

    out_json = OUT / "security_core_smoke_summary.json"
    out_md = OUT / "security_core_smoke_summary.md"
    out_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    lines = [
        "# Security Core Smoke Summary",
        "",
        f"- Timestamp: {summary['ts']}",
        f"- Checks: {summary['total']}",
        f"- Passed: {summary['passed']}",
        f"- Failed: {summary['failed']}",
        f"- Overall: {'PASS' if summary['ok'] else 'FAIL'}",
        "",
        "## Results",
    ]
    for r in results:
        icon = "PASS" if r["ok"] else "FAIL"
        lines.append(
            f"- [{icon}] {r['flow']} mode={r['mode']} "
            f"exit={r['actual_exit']} code={r['actual_code']}"
        )
    out_md.write_text("\n".join(lines), encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": summary["ok"],
                "summary_json": str(out_json),
                "summary_md": str(out_md),
                "passed": passed,
                "failed": failed,
            },
            indent=2,
        )
    )

    raise SystemExit(0 if summary["ok"] else 1)


if __name__ == "__main__":
    main()
