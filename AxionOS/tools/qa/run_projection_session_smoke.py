#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

TOOLS_DIR = Path(__file__).resolve().parent.parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.append(str(TOOLS_DIR))

from common.pathing import axion_path

LAUNCHER_DIR = axion_path("runtime", "capsule", "launchers")
if str(LAUNCHER_DIR) not in sys.path:
    sys.path.append(str(LAUNCHER_DIR))

from app_runtime_launcher import launch, build_installer_provenance_envelope
from projection_session_broker import load_session_registry, reap_expired_sessions, save_session_registry

OUT = axion_path("out", "qa")
OUT.mkdir(parents=True, exist_ok=True)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> None:
    app_id = "projection_session_smoke_app"
    provenance = build_installer_provenance_envelope(
        "projection_session_smoke_app.deb",
        family="linux",
        profile="linux_current",
        app_id=app_id,
        source_commit_sha="0909090909090909090909090909090909090909",
        build_pipeline_id="axion-qa-projection",
    )
    install = launch(
        app_id="external_installer",
        corr="corr_projection_smoke_install_001",
        family="linux",
        profile="linux_current",
        installer="projection_session_smoke_app.deb",
        installer_app_id=app_id,
        execute_installer=True,
        installer_provenance=provenance,
    )
    first = launch(app_id=app_id, corr="corr_projection_smoke_launch_001")
    second = launch(app_id=app_id, corr="corr_projection_smoke_launch_002")

    sid_a = (((first.get("projection_session") or {}).get("session_id")) or "")
    sid_b = (((second.get("projection_session") or {}).get("session_id")) or "")
    reg = load_session_registry()
    if sid_b and sid_b in (reg.get("sessions") or {}):
        sess = reg["sessions"][sid_b]
        sess["idle_timeout_sec"] = 1
        sess["last_seen_utc"] = "2000-01-01T00:00:00+00:00"
        save_session_registry(reg)
    reaped = reap_expired_sessions(corr="corr_projection_smoke_reap_001")
    third = launch(app_id=app_id, corr="corr_projection_smoke_launch_003")
    sid_c = (((third.get("projection_session") or {}).get("session_id")) or "")

    cow_mode = str((((first.get("projection_session") or {}).get("runtime_layer") or {}).get("mode")) or "")
    checks = [
        {"name": "installer_projection_created", "ok": bool((install.get("installer_projection") or {}).get("projection_id"))},
        {"name": "installer_projection_session_created", "ok": bool((install.get("installer_projection_session") or {}).get("session_id"))},
        {"name": "launch_projection_session_first", "ok": bool(sid_a)},
        {"name": "launch_projection_session_reconnect", "ok": bool(sid_a) and sid_a == sid_b},
        {"name": "launch_projection_session_reap_expired", "ok": bool(reaped.get("expired_count", 0) >= 1 and sid_c and sid_c != sid_b)},
        {"name": "launch_projection_cow_mode", "ok": cow_mode == "copy_on_write"},
    ]

    failed = [c for c in checks if not bool(c.get("ok"))]
    summary: dict[str, Any] = {
        "ts": now_iso(),
        "suite": "projection_session_smoke",
        "ok": len(failed) == 0,
        "checks_total": len(checks),
        "checks_failed": len(failed),
        "checks": checks,
        "install": install,
        "first_launch": first,
        "second_launch": second,
        "third_launch": third,
        "reap": reaped,
    }
    out_json = OUT / "projection_session_smoke_summary.json"
    out_md = OUT / "projection_session_smoke_summary.md"
    out_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    lines = [
        "# Projection Session Smoke Summary",
        "",
        f"- Timestamp: {summary['ts']}",
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
            },
            indent=2,
        )
    )
    raise SystemExit(0 if summary["ok"] else 1)


if __name__ == "__main__":
    main()
