import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent.parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.append(str(TOOLS_DIR))

from common.pathing import axion_path

OUT = axion_path("out", "qa")
OUT.mkdir(parents=True, exist_ok=True)


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def run_cmd(name, cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    stdout_text = (p.stdout or "").strip()
    stderr_text = (p.stderr or "").strip()
    stdout_json = None
    try:
        parsed = json.loads(stdout_text) if stdout_text else None
        if isinstance(parsed, dict):
            stdout_json = parsed
    except Exception:
        stdout_json = None
    return {
        "name": name,
        "cmd": cmd,
        "ok": p.returncode == 0,
        "exit": p.returncode,
        "stdout": stdout_text[:3000],
        "stderr": stderr_text[:2000],
        "stdout_json": stdout_json,
    }


def parse_json_stdout(step):
    parsed = step.get("stdout_json")
    if isinstance(parsed, dict):
        return parsed
    try:
        return json.loads(step.get("stdout", "") or "{}")
    except Exception:
        return None


def main():
    qa_smoke = str(axion_path("tools", "qa", "run_phase2_shell_smoke.py"))
    app_launcher = str(axion_path("runtime", "capsule", "launchers", "app_runtime_launcher.py"))
    daf_cli = str(axion_path("runtime", "device_fabric", "daf_cli.py"))

    steps = []

    # 1) Phase 2 shell smoke
    steps.append(run_cmd("phase2_shell_smoke", ["python", qa_smoke]))

    # 2) Capsule app launch smokes
    steps.append(run_cmd("launch_clock", ["python", app_launcher, "--app", "clock", "--corr", "corr_master_clock_001"]))
    steps.append(
        run_cmd(
            "launch_pad",
            [
                "python",
                app_launcher,
                "--app",
                "pad",
                "--corr",
                "corr_master_pad_001",
                "--family",
                "native_axion",
                "--profile",
                "axion_default",
            ],
        )
    )
    steps.append(run_cmd("launch_capture", ["python", app_launcher, "--app", "capture", "--corr", "corr_master_capture_001"]))
    steps.append(run_cmd("launch_command_prompt", ["python", app_launcher, "--app", "command_prompt", "--corr", "corr_master_cmd_001"]))
    steps.append(run_cmd("launch_powershell", ["python", app_launcher, "--app", "powershell", "--corr", "corr_master_ps_001"]))

    # 3) Device fabric smokes
    steps.append(run_cmd("daf_known_usb", ["python", daf_cli, "detect", "--bus", "usb", "--vendor", "1234", "--product", "5678", "--class", "storage"]))
    steps.append(run_cmd("daf_unknown_usb", ["python", daf_cli, "detect", "--bus", "usb", "--vendor", "9999", "--product", "9999", "--class", "storage"]))

    # Evaluate expectations
    checks = []

    shell = parse_json_stdout(steps[0]) or {}
    checks.append({"name": "shell_smoke_ok", "ok": bool(shell.get("ok", False))})
    checks.append({"name": "shell_hosts_failed_zero", "ok": int(shell.get("failed", 1)) == 0})
    checks.append({"name": "shell_routes_failed_zero", "ok": int(shell.get("route_failed", 1)) == 0})

    for i, nm in [(1, "clock_launch_ok"), (2, "pad_launch_ok"), (3, "capture_launch_ok"), (4, "command_prompt_launch_ok"), (5, "powershell_launch_ok")]:
        data = parse_json_stdout(steps[i]) or {}
        checks.append({"name": nm, "ok": data.get("code") == "LAUNCH_OK"})

    known = parse_json_stdout(steps[6]) or {}
    checks.append({"name": "daf_known_ok_or_shadow", "ok": known.get("decision") in ("DRV_OK", "DRV_SHADOW_RESTORE_OK")})

    unknown = parse_json_stdout(steps[7]) or {}
    checks.append({"name": "daf_unknown_quarantined", "ok": unknown.get("decision") == "DRV_QUARANTINED"})

    passed = sum(1 for c in checks if c["ok"])
    failed = len(checks) - passed

    summary = {
        "ts": now_iso(),
        "suite": "axion_master_smoke_v1",
        "checks_total": len(checks),
        "checks_passed": passed,
        "checks_failed": failed,
        "ok": failed == 0,
        "checks": checks,
        "steps": steps,
    }

    out_json = OUT / "master_smoke_summary.json"
    out_md = OUT / "master_smoke_summary.md"
    out_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    lines = [
        "# Axion Master Smoke Summary",
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
        icon = "PASS" if c["ok"] else "FAIL"
        lines.append(f"- [{icon}] {c['name']}")
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


if __name__ == "__main__":
    main()
