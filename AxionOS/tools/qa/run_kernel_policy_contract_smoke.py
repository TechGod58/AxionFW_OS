#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent.parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.append(str(TOOLS_DIR))

from common.pathing import axion_path

OUT = axion_path("out", "qa")
OUT.mkdir(parents=True, exist_ok=True)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def check_contains(text: str, pattern: str) -> bool:
    return pattern in text


def main() -> None:
    kernel_security = axion_path("kernel", "src", "subsys", "security.c")
    kernel_scheduler = axion_path("kernel", "src", "subsys", "scheduler.c")
    kernel_syscall = axion_path("kernel", "src", "subsys", "syscall.c")
    kernel_main = axion_path("kernel", "src", "main.c")

    sec = kernel_security.read_text(encoding="utf-8")
    sch = kernel_scheduler.read_text(encoding="utf-8")
    sysc = kernel_syscall.read_text(encoding="utf-8")
    main_src = kernel_main.read_text(encoding="utf-8")

    checks: list[dict[str, object]] = []

    checks.append(
        {
            "name": "security_selftest_function_present",
            "ok": check_contains(sec, "ax_security_selftest_rule_precedence"),
        }
    )
    for marker in [
        "selftest/precedence/prefix_deny",
        "selftest/precedence/prefix_allow/deny_exact",
        "selftest/precedence/path/allow/item",
        "selftest/precedence/path2/deny/item",
    ]:
        checks.append({"name": f"security_selftest_case_{marker}", "ok": check_contains(sec, marker)})

    checks.append(
        {
            "name": "scheduler_internal_syscall_gate_present",
            "ok": check_contains(sch, "ax_sched_internal_apply_policy_syscall")
            and check_contains(sch, "ax_sched_internal_enable_syscall_gate"),
        }
    )
    checks.append(
        {
            "name": "scheduler_direct_path_denied",
            "ok": bool(
                re.search(
                    r"int\s+ax_sched_set_policy_checked\s*\([^)]*\)\s*\{[\s\S]*?return\s+0\s*;",
                    sch,
                )
            ),
        }
    )

    checks.append(
        {
            "name": "syscall_authorizes_via_security_check",
            "ok": check_contains(sysc, "ax_security_check(")
            and check_contains(sysc, "AX_CAP0_PREBOOT_AUTH"),
        }
    )
    checks.append(
        {
            "name": "security_network_guard_model_present",
            "ok": check_contains(sec, "ax_security_net_guard_register_rule")
            and check_contains(sec, "ax_security_net_guard_check")
            and check_contains(sec, "AX_NET_GUARD_DENY_RULE_EFFECT"),
        }
    )
    checks.append(
        {
            "name": "syscall_network_guard_bridge_present",
            "ok": check_contains(sysc, "ax_syscall_network_egress_open")
            and check_contains(sysc, "ax_security_net_guard_check")
            and check_contains(sysc, "AX_EVT_SYSCALL_NET_GUARD"),
        }
    )

    main_direct_calls = re.findall(r"ax_sched_set_policy_checked\s*\(", main_src)
    checks.append(
        {
            "name": "main_direct_sched_write_single_negative_probe",
            "ok": len(main_direct_calls) == 1 and check_contains(main_src, "direct_denied"),
        }
    )
    checks.append(
        {
            "name": "main_syscall_policy_writes_present",
            "ok": check_contains(main_src, "ax_syscall_sched_policy_write(")
            and check_contains(main_src, "\"scheduler_policy_write\"")
            and check_contains(main_src, "\"scheduler_tune/unsafe_overclock\""),
        }
    )
    checks.append(
        {
            "name": "main_network_guard_bridge_probes_present",
            "ok": check_contains(main_src, "ax_security_net_guard_reset")
            and check_contains(main_src, "ax_security_net_guard_register_rule")
            and check_contains(main_src, "ax_syscall_network_egress_open"),
        }
    )

    passed = sum(1 for c in checks if bool(c["ok"]))
    failed = len(checks) - passed

    summary = {
        "ts": now_iso(),
        "suite": "kernel_policy_contract_smoke",
        "checks_total": len(checks),
        "checks_passed": passed,
        "checks_failed": failed,
        "ok": failed == 0,
        "checks": checks,
    }

    out_json = OUT / "kernel_policy_contract_smoke_summary.json"
    out_md = OUT / "kernel_policy_contract_smoke_summary.md"
    out_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    lines = [
        "# Kernel Policy Contract Smoke Summary",
        "",
        f"- Timestamp: {summary['ts']}",
        f"- Checks: {summary['checks_total']}",
        f"- Passed: {summary['checks_passed']}",
        f"- Failed: {summary['checks_failed']}",
        f"- Overall: {'PASS' if summary['ok'] else 'FAIL'}",
        "",
        "## Checks",
    ]
    for c in checks:
        lines.append(f"- [{'PASS' if c['ok'] else 'FAIL'}] {c['name']}")
    out_md.write_text("\n".join(lines), encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": summary["ok"],
                "summary_json": str(out_json),
                "summary_md": str(out_md),
                "checks_passed": passed,
                "checks_failed": failed,
            },
            indent=2,
        )
    )
    raise SystemExit(0 if summary["ok"] else 1)


if __name__ == "__main__":
    main()
