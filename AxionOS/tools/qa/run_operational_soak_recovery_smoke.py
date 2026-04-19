#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

TOOLS_DIR = Path(__file__).resolve().parent.parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.append(str(TOOLS_DIR))

from common.pathing import axion_path

LAUNCHER_DIR = axion_path("runtime", "capsule", "launchers")
BACKUP_RESTORE_DIR = axion_path("runtime", "shell_ui", "backup_restore_host")
if str(LAUNCHER_DIR) not in sys.path:
    sys.path.append(str(LAUNCHER_DIR))
if str(BACKUP_RESTORE_DIR) not in sys.path:
    sys.path.append(str(BACKUP_RESTORE_DIR))

from app_runtime_launcher import launch, build_installer_provenance_envelope
from projection_session_broker import load_session_registry, save_session_registry
from backup_restore_host import create_shadow_copy, list_shadow_copies, rollback_shadow_copy, run_shadow_copy_maintenance

OUT = axion_path("out", "qa")
OUT.mkdir(parents=True, exist_ok=True)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def allowed_packets() -> list[dict[str, Any]]:
    return [
        {
            "direction": "egress",
            "protocol": "https",
            "remote_host": "repo.axion.local",
            "remote_port": 443,
            "flow_profile": "installer_update",
        }
    ]


def blocked_packets() -> list[dict[str, Any]]:
    return [
        {
            "direction": "egress",
            "protocol": "https",
            "remote_host": "rogue.soak.invalid",
            "remote_port": 443,
            "flow_profile": "installer_update",
        }
    ]


def inject_projection_crash(session_id: str) -> bool:
    reg = load_session_registry()
    sessions = reg.get("sessions", {})
    sess = sessions.get(str(session_id)) if isinstance(sessions, dict) else None
    if not isinstance(sess, dict):
        return False
    sess["active"] = False
    sess["closed_utc"] = now_iso()
    sess["closed_reason"] = "qa_crash_injected"
    save_session_registry(reg)
    return True


def do_launch(
    *,
    corr: str,
    installer: str,
    app_id: str,
    provenance: dict[str, Any],
    traffic: list[dict[str, Any]],
) -> dict[str, Any]:
    return launch(
        app_id="external_installer",
        corr=corr,
        family="windows",
        profile="win11",
        installer=installer,
        installer_app_id=app_id,
        execute_installer=True,
        installer_provenance=provenance,
        expected_flow_profile="installer_update",
        traffic_sample=traffic,
    )


def _run_shadow_copy_weekly_validation(weeks: int) -> dict[str, Any]:
    scope_id = "soak_shadow_weekly_scope"
    shutil.rmtree(axion_path("data", "shadow_copies", scope_id), ignore_errors=True)
    target = axion_path("data", "profiles", "p1", "Workspace", scope_id)
    target.mkdir(parents=True, exist_ok=True)
    marker = target / "marker.txt"
    marker.write_text("week0", encoding="utf-8")
    rel_target = str(target.relative_to(axion_path())).replace("\\", "/")

    created = []
    rollback_ok = True
    for week_idx in range(max(2, int(weeks))):
        marker.write_text(f"week{week_idx}", encoding="utf-8")
        when = datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(weeks=week_idx)
        out = run_shadow_copy_maintenance(
            scope_id=scope_id,
            force=(week_idx == 0),
            now_utc=when.isoformat(),
            target_paths=[rel_target],
        )
        created.append(out)

    listed = list_shadow_copies(scope_id=scope_id)
    snapshots = listed.get("snapshots", []) if isinstance(listed, dict) else []
    newest_id = str((snapshots[0] or {}).get("snapshot_id") if snapshots else "")
    if newest_id:
        marker.write_text("tampered_after_snapshot", encoding="utf-8")
        rolled = rollback_shadow_copy(snapshot_id=newest_id, scope_id=scope_id)
        rollback_ok = bool(rolled.get("ok"))
    count = int(listed.get("count", 0)) if isinstance(listed, dict) else 0
    retention_ok = count <= 8
    created_ok = all(bool(x.get("ok")) for x in created if isinstance(x, dict))
    return {
        "ok": bool(created_ok and retention_ok and rollback_ok and bool(listed.get("ok"))),
        "scope_id": scope_id,
        "weeks": int(weeks),
        "snapshots_count": count,
        "retention_ok": retention_ok,
        "rollback_ok": rollback_ok,
        "created": created,
        "list": listed,
    }


def _update_soak_trend(summary: dict[str, Any]) -> dict[str, Any]:
    trend_path = OUT / "operational_soak_trend_latest.json"
    if trend_path.exists():
        try:
            trend = json.loads(trend_path.read_text(encoding="utf-8-sig"))
            if not isinstance(trend, dict):
                trend = {}
        except Exception:
            trend = {}
    else:
        trend = {}
    runs = trend.get("runs")
    if not isinstance(runs, list):
        runs = []

    runs.append(
        {
            "ts": summary["ts"],
            "cycles": summary["cycles"],
            "checks_failed": summary["checks_failed"],
            "failures": len(summary.get("failures", [])),
            "quarantine_expected": summary.get("quarantine_expected"),
            "quarantine_observed": summary.get("quarantine_observed"),
            "weekly_shadow_copy_ok": bool((summary.get("weekly_shadow_copy") or {}).get("ok")),
            "weekly_shadow_copy_count": int((summary.get("weekly_shadow_copy") or {}).get("snapshots_count", 0)),
        }
    )
    runs = runs[-12:]
    trend = {
        "suite": "operational_soak_trend",
        "updated_utc": now_iso(),
        "runs_total": len(runs),
        "runs": runs,
    }
    trend_path.write_text(json.dumps(trend, indent=2), encoding="utf-8")
    return trend


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cycles", type=int, default=24)
    ap.add_argument("--crash-interval", type=int, default=6)
    ap.add_argument("--quarantine-interval", type=int, default=5)
    ap.add_argument("--weekly-shadow-weeks", type=int, default=10)
    args = ap.parse_args()

    cycles = max(8, int(args.cycles))
    crash_interval = max(2, int(args.crash_interval))
    quarantine_interval = max(2, int(args.quarantine_interval))
    weekly_shadow_weeks = max(8, int(args.weekly_shadow_weeks))

    installer = "soak_recovery_setup.msi"
    app_id = "soak_recovery_installer_app"
    provenance = build_installer_provenance_envelope(
        installer,
        family="windows",
        profile="win11",
        app_id=app_id,
        source_commit_sha="1313131313131313131313131313131313131313",
        build_pipeline_id="axion-qa-operational-soak",
    )

    cycles_data: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    crash_events: list[dict[str, Any]] = []
    last_session_id = ""
    quarantine_expected = 0
    quarantine_observed = 0

    for idx in range(1, cycles + 1):
        expect_quarantine = (idx % quarantine_interval) == 0
        if expect_quarantine:
            quarantine_expected += 1
        traffic = blocked_packets() if expect_quarantine else allowed_packets()
        out = do_launch(
            corr=f"corr_soak_cycle_{idx:03d}",
            installer=installer,
            app_id=app_id,
            provenance=provenance,
            traffic=traffic,
        )
        code = str(out.get("code", ""))
        ok = bool(out.get("ok"))
        sid = str(((out.get("installer_projection_session") or {}).get("session_id")) or "")
        if code == "LAUNCH_FIREWALL_QUARANTINED":
            quarantine_observed += 1
        cycle_row = {
            "cycle": idx,
            "expected_quarantine": expect_quarantine,
            "ok": ok,
            "code": code,
            "session_id": sid or None,
        }
        cycles_data.append(cycle_row)

        if expect_quarantine:
            if ok or code != "LAUNCH_FIREWALL_QUARANTINED":
                failures.append(
                    {
                        "cycle": idx,
                        "code": "SOAK_EXPECTED_QUARANTINE_MISMATCH",
                        "observed": code,
                    }
                )
            continue

        if not ok or code != "LAUNCH_INSTALLER_EXECUTED":
            failures.append(
                {
                    "cycle": idx,
                    "code": "SOAK_EXPECTED_SUCCESS_MISMATCH",
                    "observed": code,
                }
            )
            continue
        if not sid:
            failures.append({"cycle": idx, "code": "SOAK_SESSION_MISSING"})
            continue
        last_session_id = sid

        if idx % crash_interval != 0:
            continue

        crashed = inject_projection_crash(last_session_id)
        if not crashed:
            failures.append({"cycle": idx, "code": "SOAK_CRASH_INJECTION_FAILED", "session_id": last_session_id})
            continue

        after_crash = do_launch(
            corr=f"corr_soak_recover_{idx:03d}",
            installer=installer,
            app_id=app_id,
            provenance=provenance,
            traffic=allowed_packets(),
        )
        new_sid = str(((after_crash.get("installer_projection_session") or {}).get("session_id")) or "")
        recover_ok = bool(after_crash.get("ok")) and str(after_crash.get("code")) == "LAUNCH_INSTALLER_EXECUTED"
        new_session_ok = bool(new_sid) and new_sid != last_session_id

        reconnect = do_launch(
            corr=f"corr_soak_reconnect_{idx:03d}",
            installer=installer,
            app_id=app_id,
            provenance=provenance,
            traffic=allowed_packets(),
        )
        reconnect_sid = str(((reconnect.get("installer_projection_session") or {}).get("session_id")) or "")
        recovery_close = after_crash.get("installer_projection_session_close") or {}
        closes_session_on_exit = str(recovery_close.get("code") or "") == "PROJECTION_SESSION_CLOSED"
        if closes_session_on_exit:
            reconnect_ok = bool(reconnect.get("ok")) and bool(reconnect_sid) and reconnect_sid != last_session_id
        else:
            reconnect_ok = bool(reconnect.get("ok")) and reconnect_sid == new_sid

        crash_row = {
            "cycle": idx,
            "crashed_session_id": last_session_id,
            "recovery_code": after_crash.get("code"),
            "recovery_session_id": new_sid or None,
            "reconnect_code": reconnect.get("code"),
            "reconnect_session_id": reconnect_sid or None,
            "session_closes_on_exit": closes_session_on_exit,
            "ok": bool(recover_ok and new_session_ok and reconnect_ok),
        }
        crash_events.append(crash_row)
        if not crash_row["ok"]:
            failures.append(
                {
                    "cycle": idx,
                    "code": "SOAK_CRASH_RECOVERY_FAILED",
                    "recovery_code": after_crash.get("code"),
                    "reconnect_code": reconnect.get("code"),
                }
            )
        if new_sid:
            last_session_id = new_sid

    expected_crash_events = sum(1 for x in range(1, cycles + 1) if (x % crash_interval == 0) and (x % quarantine_interval != 0))
    weekly_shadow_copy = _run_shadow_copy_weekly_validation(weekly_shadow_weeks)
    checks = [
        {"name": "soak_cycles_completed", "ok": len(cycles_data) == cycles},
        {"name": "no_unexpected_soak_failures", "ok": len(failures) == 0, "details": {"failures": len(failures)}},
        {"name": "quarantine_enforced_during_soak", "ok": quarantine_observed >= quarantine_expected, "details": {"expected": quarantine_expected, "observed": quarantine_observed}},
        {"name": "crash_recovery_events_completed", "ok": len(crash_events) >= expected_crash_events, "details": {"expected": expected_crash_events, "observed": len(crash_events)}},
        {"name": "weekly_shadow_copy_lifecycle", "ok": bool(weekly_shadow_copy.get("ok")), "details": {"snapshots_count": weekly_shadow_copy.get("snapshots_count"), "weeks": weekly_shadow_weeks}},
    ]

    checks_failed = sum(1 for c in checks if not bool(c.get("ok")))
    summary = {
        "ts": now_iso(),
        "suite": "operational_soak_recovery_smoke",
        "cycles": cycles,
        "crash_interval": crash_interval,
        "quarantine_interval": quarantine_interval,
        "weekly_shadow_weeks": weekly_shadow_weeks,
        "quarantine_expected": quarantine_expected,
        "quarantine_observed": quarantine_observed,
        "checks_total": len(checks),
        "checks_failed": checks_failed,
        "ok": checks_failed == 0,
        "checks": checks,
        "failures": failures,
        "cycles_data": cycles_data,
        "crash_events": crash_events,
        "weekly_shadow_copy": weekly_shadow_copy,
    }
    trend = _update_soak_trend(summary)
    summary["trend"] = {
        "runs_total": trend.get("runs_total"),
        "trend_path": str(OUT / "operational_soak_trend_latest.json"),
    }

    out_json = OUT / "operational_soak_recovery_smoke_summary.json"
    out_md = OUT / "operational_soak_recovery_smoke_summary.md"
    out_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    lines = [
        "# Operational Soak + Crash Recovery Smoke",
        "",
        f"- Timestamp: {summary['ts']}",
        f"- Cycles: {cycles}",
        f"- Crash interval: {crash_interval}",
        f"- Quarantine interval: {quarantine_interval}",
        f"- Weekly shadow weeks: {weekly_shadow_weeks}",
        f"- Checks: {summary['checks_total']}",
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
                "checks_failed": summary["checks_failed"],
                "failures": len(failures),
            },
            indent=2,
        )
    )
    raise SystemExit(0 if summary["ok"] else 1)


if __name__ == "__main__":
    main()
