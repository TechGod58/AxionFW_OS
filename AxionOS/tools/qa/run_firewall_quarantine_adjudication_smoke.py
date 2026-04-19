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

CP_HOST_DIR = axion_path("runtime", "shell_ui", "control_panel_host")
if str(CP_HOST_DIR) not in sys.path:
    sys.path.append(str(CP_HOST_DIR))

from control_panel_host import invoke_item_action

OUT = axion_path("out", "qa")
OUT.mkdir(parents=True, exist_ok=True)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def seed_quarantine_record() -> Path:
    root = axion_path("data", "quarantine", "network_packets", "external_installer", "qa-firewall-quarantine")
    root.mkdir(parents=True, exist_ok=True)
    path = root / "20260417T000000000100Z_smoke.json"
    obj = {
        "reason": "FIREWALL_REMOTE_HOST_MISMATCH",
        "session_id": "qa-firewall-quarantine",
        "app_id": "external_installer",
        "packet": {
            "direction": "egress",
            "protocol": "https",
            "remote_host": "qa-firewall-quarantine.example.net",
            "remote_port": 443,
            "flow_profile": "installer_update",
        },
        "quarantined_utc": "2026-04-17T00:00:00Z",
    }
    path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
    return path


def main() -> None:
    qpath = seed_quarantine_record()
    checks: list[dict[str, object]] = []

    listed = invoke_item_action(
        "Windows Defender Firewall",
        "review_firewall_quarantine",
        {"app_id": "external_installer", "limit": 20},
        corr="corr_fw_quarantine_smoke_list_001",
    )
    listed_items = ((listed.get("result") or {}).get("items") or []) if isinstance(listed, dict) else []
    checks.append({"name": "list_action_ok", "ok": bool(listed.get("ok"))})
    checks.append({"name": "list_contains_seed", "ok": any(str(x.get("path")) == str(qpath) for x in listed_items)})

    allowed = invoke_item_action(
        "Windows Defender Firewall",
        "allow_firewall_quarantine",
        {"path": str(qpath), "note": "qa smoke allowlist"},
        corr="corr_fw_quarantine_smoke_allow_001",
    )
    checks.append({"name": "allow_action_ok", "ok": bool(allowed.get("ok"))})
    checks.append(
        {
            "name": "allow_rule_written",
            "ok": bool((((allowed.get("result") or {}).get("allow_rule")) or {}).get("id")),
        }
    )

    replayed = invoke_item_action(
        "Windows Defender Firewall",
        "replay_firewall_quarantine",
        {"path": str(qpath)},
        corr="corr_fw_quarantine_smoke_replay_001",
    )
    checks.append({"name": "replay_action_ok", "ok": bool(replayed.get("ok"))})
    checks.append(
        {
            "name": "replay_allowed",
            "ok": str((replayed.get("result") or {}).get("code")) == "FIREWALL_QUARANTINE_REPLAY_OK",
        }
    )

    passed = sum(1 for c in checks if bool(c["ok"]))
    failed = len(checks) - passed
    summary = {
        "ts": now_iso(),
        "suite": "firewall_quarantine_adjudication_smoke",
        "checks_total": len(checks),
        "checks_passed": passed,
        "checks_failed": failed,
        "ok": failed == 0,
        "checks": checks,
        "seed_path": str(qpath),
    }

    out_json = OUT / "firewall_quarantine_adjudication_smoke_summary.json"
    out_md = OUT / "firewall_quarantine_adjudication_smoke_summary.md"
    out_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    lines = [
        "# Firewall Quarantine Adjudication Smoke Summary",
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
