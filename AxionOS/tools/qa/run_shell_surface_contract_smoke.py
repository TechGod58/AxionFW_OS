import json
import sys
from datetime import datetime, timezone
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent.parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.append(str(TOOLS_DIR))

from common.pathing import axion_path

CP_HOST_DIR = axion_path("runtime", "shell_ui", "control_panel_host")
WT_HOST_DIR = axion_path("runtime", "shell_ui", "windows_tools_host")
ROUTER_DIR = axion_path("runtime", "shell_ui", "router_host")
for path in (CP_HOST_DIR, WT_HOST_DIR, ROUTER_DIR):
    if str(path) not in sys.path:
        sys.path.append(str(path))

from control_panel_host import snapshot as control_panel_snapshot, list_all_items, get_item_version
from windows_tools_host import snapshot as windows_tools_snapshot, get_tool_contract
from router_host import resolve as resolve_route

OUT = axion_path("out", "qa")
OUT.mkdir(parents=True, exist_ok=True)


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def _pass(name: str, details=None):
    return {"name": name, "ok": True, "details": details or {}}


def _fail(name: str, details=None):
    return {"name": name, "ok": False, "details": details or {}}


def _check_route(route: str):
    result = resolve_route(route, corr="corr_shell_surface_route")
    return bool(result.get("ok")), result


def main():
    checks = []

    cp = control_panel_snapshot("corr_shell_surface_cp")
    wt = windows_tools_snapshot("corr_shell_surface_wt")

    checks.append(
        _pass("control_panel_implementation_version")
        if str(cp.get("implementationVersion", "")).strip()
        else _fail("control_panel_implementation_version", {"implementationVersion": cp.get("implementationVersion")})
    )
    checks.append(
        _pass("windows_tools_implementation_version")
        if str(wt.get("implementationVersion", "")).strip()
        else _fail("windows_tools_implementation_version", {"implementationVersion": wt.get("implementationVersion")})
    )

    cp_items = [dict(x) for x in list_all_items() if isinstance(x, dict)]
    wt_items = [dict(x) for x in wt.get("items", []) if isinstance(x, dict)]

    cp_missing_ver = [str(x.get("id")) for x in cp_items if not str(x.get("implementation_version", "")).strip()]
    wt_missing_ver = [str(x.get("tool_id")) for x in wt_items if not str(x.get("version", "")).strip()]
    checks.append(_pass("control_panel_item_versions_present") if not cp_missing_ver else _fail("control_panel_item_versions_present", {"missing": cp_missing_ver}))
    checks.append(_pass("windows_tools_item_versions_present") if not wt_missing_ver else _fail("windows_tools_item_versions_present", {"missing": wt_missing_ver}))

    cp_bad_routes = []
    for item in cp_items:
        route = str(item.get("route", "")).strip()
        ok, result = _check_route(route)
        if not ok:
            cp_bad_routes.append({"id": item.get("id"), "route": route, "result": result})
    checks.append(_pass("control_panel_routes_resolve") if not cp_bad_routes else _fail("control_panel_routes_resolve", {"bad_routes": cp_bad_routes[:20], "count": len(cp_bad_routes)}))

    wt_bad_contracts = []
    for item in wt_items:
        tool_id = str(item.get("tool_id", "")).strip()
        result = get_tool_contract(tool_id)
        if not bool(result.get("ok")):
            wt_bad_contracts.append({"tool_id": tool_id, "result": result})
    checks.append(_pass("windows_tools_contracts_resolve") if not wt_bad_contracts else _fail("windows_tools_contracts_resolve", {"bad_contracts": wt_bad_contracts[:20], "count": len(wt_bad_contracts)}))

    windows_tools_item = next((x for x in cp_items if str(x.get("id")) == "windows_tools"), None)
    if windows_tools_item is None:
        checks.append(_fail("control_panel_has_windows_tools_item", {"reason": "missing windows_tools id"}))
    elif str(windows_tools_item.get("route", "")) != "/windows-tools":
        checks.append(
            _fail(
                "control_panel_windows_tools_route",
                {"route": windows_tools_item.get("route"), "expected": "/windows-tools"},
            )
        )
    else:
        checks.append(_pass("control_panel_windows_tools_route"))

    for required_id in ("command_prompt", "powershell"):
        version_result = get_item_version(required_id)
        if bool(version_result.get("ok")) and str(version_result.get("implementation_version", "")).strip():
            checks.append(_pass(f"control_panel_windows_tool_present_{required_id}", {"version": version_result.get("implementation_version")}))
        else:
            checks.append(_fail(f"control_panel_windows_tool_present_{required_id}", {"result": version_result}))

    for launch_required in ("command_prompt", "powershell", "run"):
        contract = get_tool_contract(launch_required)
        if not bool(contract.get("ok")):
            checks.append(_fail(f"windows_tools_launch_contract_{launch_required}", {"result": contract}))
            continue
        checks.append(
            _pass(
                f"windows_tools_launch_contract_{launch_required}",
                {"launch_app_id": contract.get("launch_app_id")},
            )
            if bool(contract.get("launch_supported"))
            else _fail(
                f"windows_tools_launch_contract_{launch_required}",
                {"launch_supported": contract.get("launch_supported"), "launch_app_id": contract.get("launch_app_id")},
            )
        )

    passed = sum(1 for c in checks if c["ok"])
    failed = len(checks) - passed
    summary = {
        "ts": now_iso(),
        "suite": "shell_surface_contract_smoke",
        "checks_total": len(checks),
        "checks_passed": passed,
        "checks_failed": failed,
        "ok": failed == 0,
        "checks": checks,
    }

    out_json = OUT / "shell_surface_contract_smoke_summary.json"
    out_md = OUT / "shell_surface_contract_smoke_summary.md"
    out_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    lines = [
        "# Shell Surface Contract Smoke",
        "",
        f"- Timestamp: {summary['ts']}",
        f"- Checks: {summary['checks_total']}",
        f"- Passed: {summary['checks_passed']}",
        f"- Failed: {summary['checks_failed']}",
        f"- Overall: {'PASS' if summary['ok'] else 'FAIL'}",
        "",
        "## Checks",
    ]
    for check in checks:
        icon = "PASS" if check["ok"] else "FAIL"
        lines.append(f"- [{icon}] {check['name']}")
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

    if summary["ok"]:
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
