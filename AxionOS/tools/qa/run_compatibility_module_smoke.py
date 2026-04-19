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
LAUNCHER_DIR = axion_path("runtime", "capsule", "launchers")
if str(LAUNCHER_DIR) not in sys.path:
    sys.path.append(str(LAUNCHER_DIR))

from app_runtime_launcher import build_installer_provenance_envelope


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return None


def run_step(name: str, cmd: list[str]) -> dict[str, Any]:
    p = subprocess.run(cmd, capture_output=True, text=True)
    return {
        "name": name,
        "cmd": cmd,
        "ok": p.returncode == 0,
        "exit": p.returncode,
        "stdout": (p.stdout or "").strip(),
        "stdout_tail": (p.stdout or "").strip()[-600:],
        "stderr_tail": (p.stderr or "").strip()[-400:],
    }


def write_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    runtime_flow = axion_path("tools", "runtime", "sandbox_shell_cache_flow.py")
    modules_flow = axion_path("tools", "runtime", "program_modules_flow.py")
    launcher = axion_path("runtime", "capsule", "launchers", "app_runtime_launcher.py")
    windows_prov_path = OUT / "compat_windows_installer_provenance.json"
    linux_prov_path = OUT / "compat_linux_installer_provenance.json"
    write_json(
        windows_prov_path,
        build_installer_provenance_envelope(
            "setup_legacy.msi",
            family="windows",
            profile="win95",
            app_id="legacy_windows_installer",
            source_commit_sha="1010101010101010101010101010101010101010",
            build_pipeline_id="axion-qa-compatibility",
        ),
    )
    write_json(
        linux_prov_path,
        build_installer_provenance_envelope(
            "setup_new.deb",
            family="linux",
            profile="linux_current",
            app_id="legacy_linux_installer",
            source_commit_sha="1111111111111111111111111111111111111111",
            build_pipeline_id="axion-qa-compatibility",
        ),
    )

    steps: list[dict[str, Any]] = []
    checks: list[dict[str, Any]] = []

    steps.append(run_step("sandbox_shell_cache_flow", ["python", str(runtime_flow)]))
    shell_smoke = read_json(axion_path("out", "runtime", "sandbox_shell_cache_smoke.json")) or {}
    checks.append({"name": "sandbox_shell_cache_flow_ok", "ok": steps[-1]["ok"]})
    checks.append({
        "name": "windows_shell_is_sandbox",
        "ok": str(((shell_smoke.get("resolved") or {}).get("legacy_winapp") or {}).get("execution_model", "")).startswith("sandbox_"),
    })
    checks.append({
        "name": "linux_shell_is_sandbox",
        "ok": str(((shell_smoke.get("resolved") or {}).get("legacy_linux_app") or {}).get("execution_model", "")).startswith("sandbox_"),
    })

    steps.append(run_step("program_modules_flow", ["python", str(modules_flow)]))
    modules_smoke = read_json(axion_path("out", "runtime", "program_modules_smoke.json")) or {}
    checks.append({"name": "program_modules_flow_ok", "ok": steps[-1]["ok"]})
    checks.append({
        "name": "program_modules_one_click_registered",
        "ok": str((modules_smoke.get("registered") or {}).get("code", "")).startswith("PROGRAM_MODULE_"),
    })

    native_system = run_step(
        "native_system_command_prompt_launch",
        [
            "python",
            str(launcher),
            "--app",
            "command_prompt",
            "--corr",
            "corr_compat_native_system_001",
        ],
    )
    steps.append(native_system)
    ns_obj = {}
    try:
        ns_obj = json.loads(native_system["stdout"])
    except Exception:
        ns_obj = {}
    checks.append({"name": "native_system_command_prompt_launch_ok", "ok": native_system["ok"] and bool(ns_obj.get("ok", False))})
    checks.append({
        "name": "native_system_not_sandbox_execution_model",
        "ok": str(((ns_obj.get("compatibility") or {}).get("execution_model", ""))) == "host_native_guarded",
    })
    checks.append({
        "name": "native_system_internet_not_required",
        "ok": bool(((ns_obj.get("firewall_guard_session") or {}).get("internet_required", False))) is False,
    })

    windows_inst = run_step(
        "installer_windows_prepare",
        [
            "python",
            str(launcher),
            "--app",
            "legacy_windows_installer",
            "--family",
            "windows",
            "--profile",
            "win95",
            "--installer",
            "setup_legacy.msi",
            "--installer-app-id",
            "legacy_windows_installer",
            "--execute-installer",
            "--installer-provenance-json",
            str(windows_prov_path),
        ],
    )
    steps.append(windows_inst)
    w_obj = {}
    try:
        w_obj = json.loads(windows_inst["stdout"])
    except Exception:
        w_obj = {}
    checks.append({"name": "installer_windows_prepare_ok", "ok": windows_inst["ok"] and bool(w_obj.get("ok", False))})
    checks.append({
        "name": "installer_windows_sandbox_enforced",
        "ok": str(((w_obj.get("installer_runtime") or {}).get("execution_model", ""))).startswith("sandbox_"),
    })
    checks.append({
        "name": "installer_windows_execution_simulated",
        "ok": str(((w_obj.get("installer_execution") or {}).get("code", ""))) == "INSTALLER_EXECUTION_SIMULATED",
    })
    checks.append({
        "name": "installer_windows_replay_present",
        "ok": bool((w_obj.get("installer_replay") or {}).get("signature")),
    })
    checks.append({
        "name": "installer_windows_projection_present",
        "ok": bool((w_obj.get("installer_projection") or {}).get("projection_id")),
    })
    checks.append({
        "name": "installer_windows_projection_session_present",
        "ok": bool((w_obj.get("installer_projection_session") or {}).get("session_id")),
    })
    checks.append({
        "name": "installer_windows_firewall_guard_attached",
        "ok": bool((w_obj.get("firewall_guard_session") or {}).get("internet_required", False)),
    })
    checks.append({
        "name": "installer_windows_capture_provider_mapped",
        "ok": str((w_obj.get("firewall_packet_source") or {}).get("provider_id", "")) == "windows_tcp_snapshot_provider_v1",
    })

    linux_inst = run_step(
        "installer_linux_prepare",
        [
            "python",
            str(launcher),
            "--app",
            "legacy_linux_installer",
            "--family",
            "linux",
            "--profile",
            "linux_current",
            "--installer",
            "setup_new.deb",
            "--installer-app-id",
            "legacy_linux_installer",
            "--execute-installer",
            "--installer-provenance-json",
            str(linux_prov_path),
        ],
    )
    steps.append(linux_inst)
    l_obj = {}
    try:
        l_obj = json.loads(linux_inst["stdout"])
    except Exception:
        l_obj = {}
    checks.append({"name": "installer_linux_prepare_ok", "ok": linux_inst["ok"] and bool(l_obj.get("ok", False))})
    checks.append({
        "name": "installer_linux_sandbox_enforced",
        "ok": str(((l_obj.get("installer_runtime") or {}).get("execution_model", ""))).startswith("sandbox_"),
    })
    checks.append({
        "name": "installer_linux_execution_simulated",
        "ok": str(((l_obj.get("installer_execution") or {}).get("code", ""))) == "INSTALLER_EXECUTION_SIMULATED",
    })
    checks.append({
        "name": "installer_linux_replay_present",
        "ok": bool((l_obj.get("installer_replay") or {}).get("signature")),
    })
    checks.append({
        "name": "installer_linux_projection_present",
        "ok": bool((l_obj.get("installer_projection") or {}).get("projection_id")),
    })
    checks.append({
        "name": "installer_linux_projection_session_present",
        "ok": bool((l_obj.get("installer_projection_session") or {}).get("session_id")),
    })
    checks.append({
        "name": "installer_linux_firewall_guard_attached",
        "ok": bool((l_obj.get("firewall_guard_session") or {}).get("internet_required", False)),
    })
    checks.append({
        "name": "installer_linux_capture_provider_mapped",
        "ok": str((l_obj.get("firewall_packet_source") or {}).get("provider_id", "")) == "linux_ss_snapshot_provider_v1",
    })

    passed = sum(1 for c in checks if bool(c["ok"]))
    failed = len(checks) - passed

    summary = {
        "ts": now_iso(),
        "suite": "compatibility_module_smoke",
        "checks_total": len(checks),
        "checks_passed": passed,
        "checks_failed": failed,
        "ok": failed == 0,
        "checks": checks,
        "steps": steps,
    }

    out_json = OUT / "compatibility_module_smoke_summary.json"
    out_md = OUT / "compatibility_module_smoke_summary.md"
    out_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    lines = [
        "# Compatibility + Module Smoke Summary",
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
