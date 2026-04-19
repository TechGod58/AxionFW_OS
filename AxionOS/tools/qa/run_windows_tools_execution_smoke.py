#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent.parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.append(str(TOOLS_DIR))

from common.pathing import axion_path

SHELL_UI_ROOT = axion_path("runtime", "shell_ui")
for mod in ("windows_tools_host", "action_contract", "start_menu_host", "control_panel_host"):
    p = SHELL_UI_ROOT / mod
    if str(p) not in sys.path:
        sys.path.append(str(p))

from windows_tools_host import get_tool_contract, launch_tool
from shell_action_contract import dispatch_ui_action
from start_menu_host import apply_profile, invoke_quick_action

OUT = axion_path("out", "qa")
OUT.mkdir(parents=True, exist_ok=True)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def check(name: str, ok: bool, details: dict | None = None) -> dict:
    return {"name": name, "ok": bool(ok), "details": details or {}}


def main() -> int:
    checks: list[dict] = []

    contract = get_tool_contract("command_prompt")
    checks.append(check("cmd_contract_ok", bool(contract.get("ok")), {"code": contract.get("code")}))
    checks.append(check("cmd_contract_launch_supported", bool(contract.get("launch_supported")), {"launch_app_id": contract.get("launch_app_id")}))

    cmd_launch = launch_tool("command_prompt", corr="corr_wt_smoke_cmd_001")
    checks.append(check("cmd_launch_ok", bool(cmd_launch.get("ok")), {"code": cmd_launch.get("code")}))
    checks.append(check("cmd_runtime_launch_ok", str((cmd_launch.get("result") or {}).get("code")) == "LAUNCH_OK", {"runtime": (cmd_launch.get("result") or {}).get("code")}))

    ps_dispatch = dispatch_ui_action("windows_tools", "launch_tool", item="powershell", args={}, corr="corr_wt_smoke_ps_001")
    checks.append(check("powershell_dispatch_launch_ok", bool(ps_dispatch.get("ok")), {"code": ps_dispatch.get("code")}))
    checks.append(check("powershell_runtime_launch_ok", str(((ps_dispatch.get("result") or {}).get("result") or {}).get("code")) == "LAUNCH_OK", {"runtime": ((ps_dispatch.get("result") or {}).get("result") or {}).get("code")}))

    cp_dispatch = dispatch_ui_action("control_panel", "launch_item", item="Command Prompt", args={}, corr="corr_wt_smoke_cp_001")
    checks.append(check("control_panel_launch_item_ok", bool(cp_dispatch.get("ok")), {"code": cp_dispatch.get("code")}))

    apply_profile(corr="corr_wt_smoke_startmenu_profile_001")
    sm_cmd = invoke_quick_action("quick_launch_command_prompt", {}, corr="corr_wt_smoke_sm_cmd_001")
    sm_run = invoke_quick_action("quick_launch_run_dialog", {}, corr="corr_wt_smoke_sm_run_001")
    checks.append(check("startmenu_quick_cmd_ok", bool(sm_cmd.get("ok")), {"code": sm_cmd.get("code")}))
    checks.append(check("startmenu_quick_run_ok", bool(sm_run.get("ok")), {"code": sm_run.get("code")}))

    passed = sum(1 for c in checks if c["ok"])
    failed = len(checks) - passed

    summary = {
        "ts": now_iso(),
        "suite": "windows_tools_execution_smoke",
        "checks_total": len(checks),
        "checks_passed": passed,
        "checks_failed": failed,
        "ok": failed == 0,
        "checks": checks,
    }

    out_json = OUT / "windows_tools_execution_smoke_summary.json"
    out_md = OUT / "windows_tools_execution_smoke_summary.md"
    out_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    lines = [
        "# Windows Tools Execution Smoke",
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
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
