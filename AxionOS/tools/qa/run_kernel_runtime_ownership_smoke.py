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


def check(path: Path, marker: str) -> bool:
    if not path.exists():
        return False
    return marker in path.read_text(encoding="utf-8")


def hook_calls(main_src: str, hook_name: str, call_name: str) -> bool:
    pattern = rf"static\s+void\s+{re.escape(hook_name)}\s*\([^)]*\)\s*\{{[\s\S]*?{re.escape(call_name)}\s*\("
    return bool(re.search(pattern, main_src))


def main() -> None:
    checks: list[dict[str, object]] = []
    main_path = axion_path("kernel", "src", "main.c")
    main_src = main_path.read_text(encoding="utf-8")

    runtime_files = [
        ("kernel/include/axion/runtime/e_runtime.h", ["axion_e_policy_t", "axion_e_execute_ex", "axion_e_state_t"]),
        ("kernel/include/axion/runtime/qm.h", ["axion_qm_policy_t", "axion_qm_transition_ex", "axion_qm_state_t"]),
        ("kernel/src/runtime/e_runtime.c", ["axion_e_set_policy_checked", "AXION_E_REASON_DENY_SANDBOX_REQUIRED", "axion_ig_validate"]),
        ("kernel/src/runtime/qm.c", ["axion_qm_set_policy_checked", "AXION_QM_REASON_DENY_STRICT_PATH", "axion_qm_transition_ex"]),
        ("kernel/src/runtime/ig.c", ["axion_ig_validate", "AX_EVT_RUNTIME_IG_VALIDATE"]),
        ("kernel/src/runtime/ledger.c", ["axion_ledger_commit", "AX_EVT_RUNTIME_LEDGER_COMMIT"]),
        ("kernel/src/runtime/qecc.c", ["axion_qecc_attach", "AX_EVT_RUNTIME_QECC_ATTACH"]),
    ]

    for rel, markers in runtime_files:
        p = axion_path(*rel.split("/"))
        checks.append({"name": f"exists_{rel}", "ok": p.exists()})
        for m in markers:
            checks.append({"name": f"marker_{rel}_{m}", "ok": check(p, m)})

    hook_requirements = [
        ("hook_userland_init", "axion_qm_init"),
        ("hook_userland_init", "axion_qm_transition"),
        ("hook_userland_init", "axion_e_init"),
        ("hook_userland_init", "axion_e_execute_ex"),
    ]
    for hook_name, call_name in hook_requirements:
        checks.append({"name": f"{hook_name}_calls_{call_name}", "ok": hook_calls(main_src, hook_name, call_name)})

    makefile = axion_path("Makefile")
    for marker in [
        "kernel/src/runtime/e_runtime.c",
        "kernel/src/runtime/qm.c",
        "build/kernel/runtime_e_runtime.o",
        "build/kernel/runtime_qm.o",
    ]:
        checks.append({"name": f"makefile_marker_{marker}", "ok": check(makefile, marker)})

    passed = sum(1 for c in checks if bool(c["ok"]))
    failed = len(checks) - passed
    summary = {
        "ts": now_iso(),
        "suite": "kernel_runtime_ownership_smoke",
        "checks_total": len(checks),
        "checks_passed": passed,
        "checks_failed": failed,
        "ok": failed == 0,
        "checks": checks,
    }

    out_json = OUT / "kernel_runtime_ownership_smoke_summary.json"
    out_md = OUT / "kernel_runtime_ownership_smoke_summary.md"
    out_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    lines = [
        "# Kernel Runtime Ownership Smoke Summary",
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

