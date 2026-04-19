#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Third-Party Bundle Compliance Report",
        "",
        f"- Timestamp: {report['timestamp_utc']}",
        f"- Policy: `{report['policy_path']}`",
        f"- Overall: **{'PASS' if report['ok'] else 'FAIL'}**",
        f"- Checks failed: {report['checks_failed']}",
        "",
        "## Checks",
    ]
    for row in report.get("checks", []):
        lines.append(f"- [{'PASS' if row.get('ok') else 'FAIL'}] {row.get('name')}")
        if row.get("details"):
            lines.append(f"  - Details: {row.get('details')}")
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--os-root", required=True)
    ap.add_argument("--out-dir", default="")
    args = ap.parse_args()

    os_root = Path(args.os_root).resolve()
    out_dir = Path(args.out_dir).resolve() if str(args.out_dir).strip() else (os_root / "out" / "packaging")
    out_dir.mkdir(parents=True, exist_ok=True)

    policy_path = os_root / "config" / "THIRD_PARTY_APP_BUNDLE_POLICY_V1.json"
    notice_path = os_root / "compliance" / "third_party" / "NOTICE_BUNDLE_V1.md"
    source_offer_path = os_root / "compliance" / "third_party" / "SOURCE_OFFER_V1.md"

    policy = load_json(policy_path)
    targets = [dict(x) for x in policy.get("bundleTargets", []) if isinstance(x, dict)]
    gates = dict(policy.get("complianceGates", {}))

    notice_text = notice_path.read_text(encoding="utf-8-sig") if notice_path.exists() else ""
    source_text = source_offer_path.read_text(encoding="utf-8-sig") if source_offer_path.exists() else ""

    checks: list[dict[str, Any]] = []
    checks.append({"name": "notice_bundle_present", "ok": notice_path.exists(), "details": str(notice_path)})
    checks.append({"name": "source_offer_present", "ok": source_offer_path.exists(), "details": str(source_offer_path)})

    missing_notice_components = []
    missing_source_components = []
    for target in targets:
        component_id = str(target.get("component_id", "")).strip()
        if not component_id:
            continue
        marker = f"## {component_id}"
        if marker not in notice_text:
            missing_notice_components.append(component_id)
        if bool(target.get("source_code_offer_required", False)) and marker not in source_text:
            missing_source_components.append(component_id)

    checks.append(
        {
            "name": "notice_bundle_component_coverage",
            "ok": len(missing_notice_components) == 0,
            "details": {"missing_components": missing_notice_components},
        }
    )
    checks.append(
        {
            "name": "source_offer_component_coverage",
            "ok": len(missing_source_components) == 0,
            "details": {"missing_components": missing_source_components},
        }
    )

    if bool(gates.get("forbid_proprietary_brand_claims", False)):
        forbidden_phrases = [
            "contains microsoft proprietary code",
            "contains adobe proprietary code",
            "official microsoft office binary",
            "official adobe acrobat binary",
        ]
        haystack = f"{notice_text}\n{source_text}".lower()
        seen = [p for p in forbidden_phrases if p in haystack]
        checks.append(
            {
                "name": "no_proprietary_brand_claims",
                "ok": len(seen) == 0,
                "details": {"forbidden_matches": seen},
            }
        )

    checks_failed = sum(1 for c in checks if not bool(c.get("ok")))
    ok = checks_failed == 0

    report = {
        "timestamp_utc": now_iso(),
        "ok": ok,
        "checks_failed": checks_failed,
        "policy_path": str(policy_path),
        "notice_bundle_path": str(notice_path),
        "source_offer_path": str(source_offer_path),
        "targets_total": len(targets),
        "checks": checks,
    }

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report_json = out_dir / f"third_party_bundle_compliance_{stamp}.json"
    report_md = out_dir / f"third_party_bundle_compliance_{stamp}.md"
    latest_json = out_dir / "third_party_bundle_compliance_latest.json"
    latest_md = out_dir / "third_party_bundle_compliance_latest.md"

    payload = json.dumps(report, indent=2) + "\n"
    report_json.write_text(payload, encoding="utf-8")
    latest_json.write_text(payload, encoding="utf-8")
    md = render_markdown(report)
    report_md.write_text(md, encoding="utf-8")
    latest_md.write_text(md, encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": ok,
                "code": "THIRD_PARTY_COMPLIANCE_OK" if ok else "THIRD_PARTY_COMPLIANCE_FAIL",
                "report_json": str(report_json),
                "report_md": str(report_md),
                "latest_json": str(latest_json),
                "latest_md": str(latest_md),
                "checks_failed": checks_failed,
            },
            indent=2,
        )
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
