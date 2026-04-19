import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent.parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.append(str(TOOLS_DIR))

from common.pathing import axion_path

HOSTS = [
    ("home", str(axion_path("runtime", "shell_ui", "home_host", "home_host.py"))),
    ("system", str(axion_path("runtime", "shell_ui", "system_host", "system_host.py"))),
    ("accounts", str(axion_path("runtime", "shell_ui", "accounts_host", "accounts_host.py"))),
    ("privacy_security", str(axion_path("runtime", "shell_ui", "privacy_security_host", "privacy_security_host.py"))),
    ("devices", str(axion_path("runtime", "shell_ui", "devices_host", "devices_host.py"))),
    ("time_language", str(axion_path("runtime", "shell_ui", "language_host", "language_host.py"))),
    ("input", str(axion_path("runtime", "shell_ui", "input_host", "input_host.py"))),
    ("personalization", str(axion_path("runtime", "shell_ui", "personalization_host", "personalization_host.py"))),
    ("apps", str(axion_path("runtime", "shell_ui", "apps_host", "apps_host.py"))),
    ("control_panel", str(axion_path("runtime", "shell_ui", "control_panel_host", "control_panel_host.py"))),
    ("windows_tools", str(axion_path("runtime", "shell_ui", "windows_tools_host", "windows_tools_host.py"))),
    ("accessibility", str(axion_path("runtime", "shell_ui", "accessibility_host", "accessibility_host.py"))),
    ("updates", str(axion_path("runtime", "shell_ui", "updates_host", "updates_host.py"))),
    ("network", str(axion_path("runtime", "shell_ui", "network_host", "network_host.py"))),
    ("router", str(axion_path("runtime", "shell_ui", "router_host", "router_host.py"))),
]

OUT = axion_path("out", "qa")
OUT.mkdir(parents=True, exist_ok=True)
SHELL_UI_ROOT = axion_path("runtime", "shell_ui")


def shell_python_env():
    env = os.environ.copy()
    module_dirs = [str(p) for p in SHELL_UI_ROOT.iterdir() if p.is_dir()]
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = os.pathsep.join(module_dirs + ([existing] if existing else []))
    return env


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def run_one(name, path):
    p = subprocess.run(["python", path], capture_output=True, text=True, env=shell_python_env())
    return {
        "name": name,
        "path": path,
        "ok": p.returncode == 0,
        "exit": p.returncode,
        "stdout": (p.stdout or "").strip()[:1200],
        "stderr": (p.stderr or "").strip()[:1200],
    }


def route_checks():
    router_dir = str(axion_path("runtime", "shell_ui", "router_host"))
    checks = []
    tests = [
        ("/home", True),
        ("/system", True),
        ("/control-panel", True),
        ("/windows-tools", True),
        ("/privacy-security", True),
        ("/nope", False),
    ]
    # invoke tiny inline python against router module for deterministic result
    for route, expected_ok in tests:
        code = (
            "import sys, json; "
            f"sys.path.append({router_dir!r}); "
            "from router_host import resolve; "
            f"o=resolve({route!r},'corr_route_smoke'); "
            "print(json.dumps(o))"
        )
        p = subprocess.run(["python", "-c", code], capture_output=True, text=True, env=shell_python_env())
        ok = p.returncode == 0
        parsed = {}
        if ok and p.stdout.strip():
            try:
                parsed = json.loads(p.stdout.strip())
            except Exception:
                parsed = {"ok": False, "code": "ROUTE_PARSE_FAIL", "raw": p.stdout.strip()}
        checks.append(
            {
                "route": route,
                "expected_ok": expected_ok,
                "ok": bool(parsed.get("ok", False)) == expected_ok,
                "result": parsed,
            }
        )
    return checks


def main():
    results = [run_one(n, p) for n, p in HOSTS]
    route_results = route_checks()

    passed = sum(1 for r in results if r["ok"])
    failed = len(results) - passed
    route_passed = sum(1 for r in route_results if r["ok"])
    route_failed = len(route_results) - route_passed

    summary = {
        "ts": now_iso(),
        "suite": "phase2_shell_category_smoke",
        "total": len(results),
        "passed": passed,
        "failed": failed,
        "route_total": len(route_results),
        "route_passed": route_passed,
        "route_failed": route_failed,
        "results": results,
        "route_results": route_results,
    }

    out_json = OUT / "phase2_shell_smoke_summary.json"
    out_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    out_md = OUT / "phase2_shell_smoke_summary.md"
    lines = [
        "# Phase 2 Shell Category Smoke Summary",
        "",
        f"- Timestamp: {summary['ts']}",
        f"- Total Hosts: {summary['total']}",
        f"- Host Passed: {summary['passed']}",
        f"- Host Failed: {summary['failed']}",
        f"- Route Checks: {summary['route_total']}",
        f"- Route Passed: {summary['route_passed']}",
        f"- Route Failed: {summary['route_failed']}",
        "",
        "## Host Results",
    ]
    for r in results:
        icon = "PASS" if r["ok"] else "FAIL"
        lines.append(f"- [{icon}] {r['name']} (exit={r['exit']})")
    lines += ["", "## Route Results"]
    for rr in route_results:
        icon = "PASS" if rr["ok"] else "FAIL"
        lines.append(f"- [{icon}] {rr['route']} expected_ok={rr['expected_ok']} result_ok={rr['result'].get('ok')}")

    out_md.write_text("\n".join(lines), encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": failed == 0 and route_failed == 0,
                "summary_json": str(out_json),
                "summary_md": str(out_md),
                "passed": passed,
                "failed": failed,
                "route_passed": route_passed,
                "route_failed": route_failed,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
