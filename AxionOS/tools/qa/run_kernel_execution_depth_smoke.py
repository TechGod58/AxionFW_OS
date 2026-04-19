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


def contains(path: Path, marker: str) -> bool:
    if not path.exists():
        return False
    return marker in path.read_text(encoding="utf-8")


def hook_calls(main_src: str, hook_name: str, call_name: str) -> bool:
    pattern = rf"static\s+void\s+{re.escape(hook_name)}\s*\([^)]*\)\s*\{{[\s\S]*?{re.escape(call_name)}\s*\("
    return bool(re.search(pattern, main_src))


def main() -> None:
    checks: list[dict[str, object]] = []

    mem_h = axion_path("kernel", "include", "axion", "subsys", "memory.h")
    mem_c = axion_path("kernel", "src", "subsys", "memory.c")
    sch_h = axion_path("kernel", "include", "axion", "subsys", "scheduler.h")
    sch_c = axion_path("kernel", "src", "subsys", "scheduler.c")
    sec_h = axion_path("kernel", "include", "axion", "subsys", "security.h")
    sec_c = axion_path("kernel", "src", "subsys", "security.c")
    life_h = axion_path("kernel", "include", "axion", "subsys", "lifecycle.h")
    life_c = axion_path("kernel", "src", "subsys", "lifecycle.c")
    main_c = axion_path("kernel", "src", "main.c")

    main_src = main_c.read_text(encoding="utf-8")

    for marker in ["ax_mem_health_t", "ax_mem_alloc_page", "ax_mem_release_page", "ax_mem_run_stress", "ax_mem_health"]:
        checks.append({"name": f"memory_header_{marker}", "ok": contains(mem_h, marker)})
    for marker in ["AX_MEM_TRACKED_PAGE_CAP", "ax_mem_run_stress", "AX_EVT_MEM_STRESS", "ax_mem_alloc_page", "ax_mem_release_page"]:
        checks.append({"name": f"memory_source_{marker}", "ok": contains(mem_c, marker)})

    for marker in ["ax_sched_stress_state_t", "ax_sched_run_stress", "ax_sched_stress_state"]:
        checks.append({"name": f"scheduler_header_{marker}", "ok": contains(sch_h, marker)})
    for marker in ["g_stress", "ax_sched_run_stress", "AX_EVT_SCHED_STRESS", "ax_sched_stress_state"]:
        checks.append({"name": f"scheduler_source_{marker}", "ok": contains(sch_c, marker)})

    for marker in ["ax_security_stress_state_t", "ax_security_stress_reset", "ax_security_run_stress_cycle", "ax_security_stress_state"]:
        checks.append({"name": f"security_header_{marker}", "ok": contains(sec_h, marker)})
    for marker in ["ax_security_stress_reset", "ax_security_run_stress_cycle", "AX_EVT_SECURITY_STRESS", "ax_security_stress_state"]:
        checks.append({"name": f"security_source_{marker}", "ok": contains(sec_c, marker)})

    for marker in ["required_stage_mask", "stage_ok_mask", "ax_lifecycle_set_required_mask", "ax_lifecycle_is_ready"]:
        checks.append({"name": f"lifecycle_header_{marker}", "ok": contains(life_h, marker)})
    for marker in ["required_stage_mask", "stage_ok_mask", "ax_lifecycle_set_required_mask", "AX_EVT_LIFECYCLE_READY", "ax_lifecycle_is_ready"]:
        checks.append({"name": f"lifecycle_source_{marker}", "ok": contains(life_c, marker)})

    checks.append({"name": "main_hook_early_required_mask", "ok": hook_calls(main_src, "hook_early", "ax_lifecycle_set_required_mask")})
    checks.append({"name": "main_hook_mm_stress", "ok": hook_calls(main_src, "hook_mm_init", "ax_mem_run_stress")})
    checks.append({"name": "main_hook_sched_stress", "ok": hook_calls(main_src, "hook_sched_init", "ax_sched_run_stress")})
    checks.append({"name": "main_hook_security_stress", "ok": hook_calls(main_src, "hook_security_init", "ax_security_run_stress_cycle")})
    checks.append({"name": "main_hook_late_lifecycle_ready", "ok": hook_calls(main_src, "hook_late", "ax_lifecycle_is_ready")})

    for stage in range(0, 9):
        checks.append({"name": f"main_hook_late_marks_stage_{stage}", "ok": f"ax_lifecycle_mark_stage({stage}," in main_src})

    passed = sum(1 for c in checks if bool(c["ok"]))
    failed = len(checks) - passed
    summary = {
        "ts": now_iso(),
        "suite": "kernel_execution_depth_smoke",
        "checks_total": len(checks),
        "checks_passed": passed,
        "checks_failed": failed,
        "ok": failed == 0,
        "checks": checks,
    }

    out_json = OUT / "kernel_execution_depth_smoke_summary.json"
    out_md = OUT / "kernel_execution_depth_smoke_summary.md"
    out_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    lines = [
        "# Kernel Execution Depth Smoke Summary",
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
