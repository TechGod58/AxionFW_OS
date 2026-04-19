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


def file_exists(path: Path) -> bool:
    return path.exists() and path.is_file()


def has_call_in_hook(main_src: str, hook_name: str, required_call: str) -> bool:
    pattern = rf"static\s+void\s+{re.escape(hook_name)}\s*\([^)]*\)\s*\{{[\s\S]*?{re.escape(required_call)}\s*\("
    return bool(re.search(pattern, main_src))


def has_print_only_stub(main_src: str, hook_name: str) -> bool:
    pattern = rf"static\s+void\s+{re.escape(hook_name)}\s*\([^)]*\)\s*\{{\s*\(void\)c;\s*ax_printf\(\"\\[hook\\]\s*{hook_name.split('_', 1)[1] if '_' in hook_name else hook_name}.*\"\);\s*\}}"
    return bool(re.search(pattern, main_src))


def main() -> None:
    main_path = axion_path("kernel", "src", "main.c")
    main_src = main_path.read_text(encoding="utf-8")

    checks: list[dict[str, object]] = []

    required_headers = [
        "irq.h",
        "time.h",
        "ipc.h",
        "bus.h",
        "driver.h",
        "userland.h",
        "lifecycle.h",
    ]
    for name in required_headers:
        p = axion_path("kernel", "include", "axion", "subsys", name)
        checks.append({"name": f"header_exists_{name}", "ok": file_exists(p)})

    required_sources = {
        "irq.c": ("ax_irq_init", "ax_irq_state"),
        "time.c": ("ax_time_init", "ax_time_state"),
        "ipc.c": ("ax_ipc_init", "ax_ipc_state"),
        "bus.c": ("ax_bus_init", "ax_bus_state"),
        "driver.c": ("ax_driver_init", "ax_driver_state"),
        "userland.c": ("ax_userland_init", "ax_userland_state"),
        "lifecycle.c": ("ax_lifecycle_init", "ax_lifecycle_finalize"),
    }
    for file_name, markers in required_sources.items():
        p = axion_path("kernel", "src", "subsys", file_name)
        src = p.read_text(encoding="utf-8") if file_exists(p) else ""
        checks.append({"name": f"source_exists_{file_name}", "ok": file_exists(p)})
        for marker in markers:
            checks.append({"name": f"source_marker_{file_name}_{marker}", "ok": marker in src})

    hook_calls = {
        "hook_early": "ax_lifecycle_init",
        "hook_irq_init": "ax_irq_init",
        "hook_time_init": "ax_time_init",
        "hook_ipc_init": "ax_ipc_init",
        "hook_bus_init": "ax_bus_init",
        "hook_driver_init": "ax_driver_init",
        "hook_userland_init": "ax_userland_init",
        "hook_late": "ax_lifecycle_finalize",
    }
    for hook_name, call_name in hook_calls.items():
        checks.append(
            {"name": f"main_{hook_name}_calls_{call_name}", "ok": has_call_in_hook(main_src, hook_name, call_name)}
        )
        checks.append({"name": f"main_{hook_name}_not_print_stub", "ok": not has_print_only_stub(main_src, hook_name)})

    passed = sum(1 for c in checks if bool(c["ok"]))
    failed = len(checks) - passed

    summary = {
        "ts": now_iso(),
        "suite": "kernel_subsystem_ownership_smoke",
        "checks_total": len(checks),
        "checks_passed": passed,
        "checks_failed": failed,
        "ok": failed == 0,
        "checks": checks,
    }

    out_json = OUT / "kernel_subsystem_ownership_smoke_summary.json"
    out_md = OUT / "kernel_subsystem_ownership_smoke_summary.md"
    out_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    lines = [
        "# Kernel Subsystem Ownership Smoke Summary",
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

