#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent.parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.append(str(TOOLS_DIR))

from common.pathing import axion_path


OUT_DIR = axion_path("out", "qa")
RUNTIME_APPS = axion_path("runtime", "apps")
PACKAGING_OUT = axion_path("out", "packaging")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")


def _latest_release_gate() -> Path | None:
    gates = sorted(OUT_DIR.glob("os_release_gate_*.json"))
    if not gates:
        return None
    return gates[-1]


def _check_state(gate: dict, name: str) -> dict:
    checks = gate.get("checks", {})
    row = checks.get(name, {})
    if not isinstance(row, dict):
        row = {}
    return row


def _is_skipped(row: dict) -> bool:
    evidence = str(row.get("evidence", ""))
    return evidence.startswith("SKIPPED_")


def _app_operation_count(app_id: str) -> int:
    app_path = RUNTIME_APPS / app_id / f"{app_id}_app.py"
    if not app_path.exists():
        return 0
    text = app_path.read_text(encoding="utf-8-sig")
    ops = 0
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("def "):
            continue
        fn = stripped.split("def ", 1)[1].split("(", 1)[0].strip()
        if fn in {"snapshot", "_now_iso"}:
            continue
        if fn.startswith("_"):
            continue
        ops += 1
    return ops


@dataclass
class EngineStatus:
    ffmpeg: bool
    pillow: bool
    opencv: bool

    @property
    def missing(self) -> list[str]:
        out: list[str] = []
        if not self.ffmpeg:
            out.append("ffmpeg")
        if not self.pillow:
            out.append("pillow")
        if not self.opencv:
            out.append("opencv")
        return out


def _detect_engines() -> EngineStatus:
    ffmpeg_ok = False
    try:
        shared = axion_path("runtime", "apps", "_shared")
        if str(shared) not in sys.path:
            sys.path.append(str(shared))
        from media_engine import resolve_ffmpeg  # type: ignore

        ffmpeg_ok = bool((resolve_ffmpeg() or {}).get("available"))
    except Exception:
        ffmpeg_ok = False
    try:
        import PIL  # type: ignore # noqa: F401

        pillow_ok = True
    except Exception:
        pillow_ok = False
    try:
        import cv2  # type: ignore # noqa: F401

        opencv_ok = True
    except Exception:
        opencv_ok = False
    return EngineStatus(ffmpeg=ffmpeg_ok, pillow=pillow_ok, opencv=opencv_ok)


def _latest_packaging_compliance() -> dict:
    latest = PACKAGING_OUT / "third_party_bundle_compliance_latest.json"
    if not latest.exists():
        return {"ok": False, "reason": "missing_report", "path": str(latest)}
    try:
        payload = load_json(latest)
    except Exception as exc:
        return {"ok": False, "reason": "invalid_report", "error": str(exc), "path": str(latest)}
    return {"ok": bool(payload.get("ok")), "reason": "report_present", "path": str(latest), "report": payload}


def _latest_soak_trend() -> dict:
    latest = OUT_DIR / "operational_soak_trend_latest.json"
    if not latest.exists():
        return {"ok": False, "reason": "missing_trend", "path": str(latest)}
    try:
        payload = load_json(latest)
    except Exception as exc:
        return {"ok": False, "reason": "invalid_trend", "error": str(exc), "path": str(latest)}
    runs = payload.get("runs", [])
    if not isinstance(runs, list):
        runs = []
    if len(runs) < 3:
        return {"ok": False, "reason": "insufficient_runs", "path": str(latest), "runs_total": len(runs)}
    latest_run = runs[-1] if runs else {}
    if not bool((latest_run or {}).get("weekly_shadow_copy_ok")):
        return {"ok": False, "reason": "weekly_shadow_copy_not_green", "path": str(latest), "runs_total": len(runs)}
    return {"ok": True, "reason": "trend_green", "path": str(latest), "runs_total": len(runs), "trend": payload}


def _recommend_batches(
    *,
    skipped_optional: list[str],
    metadata_only: list[str],
    missing_engines: list[str],
    compliance_ok: bool,
    soak_trend_ok: bool,
) -> list[dict]:
    batches: list[dict] = []
    if skipped_optional:
        batches.append(
            {
                "id": 1,
                "name": "Physical Boot Verification",
                "goal": "Run non-skipped kernel/stack verification on real WSL/boot path.",
                "items": [
                    "Enable and execute kernel_live_boot_wsl lane",
                    "Execute unified_stack_smoke in the same run",
                    "Capture reproducible evidence in out/qa",
                ],
                "blocked_by": skipped_optional,
            }
        )
    if metadata_only:
        batches.append(
            {
                "id": 2,
                "name": "Productivity Runtime Depth",
                "goal": "Promote metadata wrappers into operation-capable runtime apps.",
                "items": [
                    "Implement open/edit/export verbs for metadata-only productivity apps",
                    "Add deterministic file round-trip tests for office-style formats",
                    "Wire Control Panel and Windows Tools actions to new verbs",
                ],
                "target_apps": metadata_only,
            }
        )
    if missing_engines:
        batches.append(
            {
                "id": 3,
                "name": "Media Engine Closure",
                "goal": "Harden creative/media runtime dependencies and validation.",
                "items": [
                    "Ensure required media engines are available or bundled",
                    "Add preflight checks that fail closed on missing runtime engines",
                    "Add deterministic media/photo contract tests in release lane",
                ],
                "missing_engines": missing_engines,
            }
        )
    if not compliance_ok:
        batches.append(
            {
                "id": 4,
                "name": "License & Packaging Closure",
                "goal": "Enforce third-party bundle compliance at package build time.",
                "items": [
                    "Validate notice bundle and source-offer artifacts during packaging",
                    "Block package creation on compliance-gate failure",
                    "Emit compliance report alongside install bundle",
                ],
            }
        )
    if not soak_trend_ok:
        batches.append(
            {
                "id": 5,
                "name": "Operational Soak Expansion",
                "goal": "Increase confidence under long-run churn and recovery conditions.",
                "items": [
                    "Extend soak duration and crash-injection scenarios",
                    "Validate weekly shadow-copy lifecycle and rollback guarantees",
                    "Publish stability trend report over multiple runs",
                ],
            }
        )
    return batches


def _render_md(report: dict) -> str:
    lines = [
        "# AxionOS Completion Assessment",
        "",
        f"- Timestamp (UTC): {report['timestamp_utc']}",
        f"- Latest release gate: `{report['latest_release_gate']}`",
        f"- Release critical status: **{'PASS' if report['release_gate']['critical_ok'] else 'FAIL'}**",
        f"- Release overall status: **{'PASS' if report['release_gate']['overall_ok'] else 'FAIL'}**",
        f"- Completion score: **{report['completion_score_pct']}%**",
        "",
        "## Remaining Gaps",
    ]
    if report["remaining_gaps"]:
        for gap in report["remaining_gaps"]:
            lines.append(f"- {gap}")
    else:
        lines.append("- None")
    lines.extend(["", "## Recommended Batches"])
    if not report["recommended_batches"]:
        lines.append("- None")
        return "\n".join(lines).strip() + "\n"
    for batch in report["recommended_batches"]:
        lines.append(f"### Batch {batch['id']} - {batch['name']}")
        lines.append(f"- Goal: {batch['goal']}")
        for item in batch["items"]:
            lines.append(f"- {item}")
        if batch.get("blocked_by"):
            lines.append(f"- Current blockers: {batch['blocked_by']}")
        if batch.get("target_apps"):
            lines.append(f"- Target apps: {batch['target_apps']}")
        if batch.get("missing_engines"):
            lines.append(f"- Missing engines: {batch['missing_engines']}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    gate_path = _latest_release_gate()
    if gate_path is None:
        out = {
            "ok": False,
            "code": "ASSESSMENT_RELEASE_GATE_MISSING",
            "detail": "No release gate summary found in out/qa.",
        }
        print(json.dumps(out, indent=2))
        return 1

    gate = load_json(gate_path)
    critical_ok = bool(gate.get("critical_ok"))
    overall_ok = bool(gate.get("overall_ok"))

    optional_checks = ["kernel_live_boot_wsl", "unified_stack_smoke"]
    skipped_optional = [name for name in optional_checks if _is_skipped(_check_state(gate, name))]

    productivity_apps = [
        "write",
        "sheets",
        "slides",
        "mail",
        "database",
        "publisher",
        "pdf_studio",
        "vector_studio",
        "creative_studio",
        "notepad_plus_plus",
    ]
    metadata_only: list[str] = []
    for app_id in productivity_apps:
        if _app_operation_count(app_id) == 0:
            metadata_only.append(app_id)

    engines = _detect_engines()
    missing_engines = engines.missing
    compliance = _latest_packaging_compliance()
    soak_trend = _latest_soak_trend()
    compliance_ok = bool(compliance.get("ok"))
    soak_trend_ok = bool(soak_trend.get("ok"))

    remaining_gaps: list[str] = []
    if not critical_ok:
        remaining_gaps.append("Critical release gate is not green.")
    if not overall_ok:
        remaining_gaps.append("Overall release gate is not green.")
    if skipped_optional:
        remaining_gaps.append(f"Optional execution-depth lanes skipped: {skipped_optional}")
    if metadata_only:
        remaining_gaps.append(f"Metadata-only productivity wrappers still present: {metadata_only}")
    if missing_engines:
        remaining_gaps.append(f"Required media/creative engines not fully available: {missing_engines}")
    if not compliance_ok:
        remaining_gaps.append(f"Packaging compliance gate not green: {compliance.get('reason')}")
    if not soak_trend_ok:
        remaining_gaps.append(f"Operational soak trend gate not green: {soak_trend.get('reason')}")
    score = 100.0
    if not critical_ok:
        score -= 35.0
    if not overall_ok:
        score -= 15.0
    score -= min(20.0, float(len(skipped_optional) * 7))
    if productivity_apps:
        score -= 20.0 * (float(len(metadata_only)) / float(len(productivity_apps)))
    score -= min(10.0, float(len(missing_engines) * 3))
    if not compliance_ok:
        score -= 5.0
    if not soak_trend_ok:
        score -= 5.0
    score = max(0.0, round(score, 1))

    report = {
        "timestamp_utc": now_iso(),
        "latest_release_gate": str(gate_path),
        "release_gate": {
            "critical_ok": critical_ok,
            "overall_ok": overall_ok,
        },
        "completion_score_pct": score,
        "remaining_gaps": remaining_gaps,
        "compliance": compliance,
        "soak_trend": soak_trend,
        "recommended_batches": _recommend_batches(
            skipped_optional=skipped_optional,
            metadata_only=metadata_only,
            missing_engines=missing_engines,
            compliance_ok=compliance_ok,
            soak_trend_ok=soak_trend_ok,
        ),
    }

    out_json = OUT_DIR / "os_completion_assessment_latest.json"
    out_md = OUT_DIR / "os_completion_assessment_latest.md"
    save_json(out_json, report)
    out_md.write_text(_render_md(report), encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "code": "ASSESSMENT_OK",
                "json": str(out_json),
                "md": str(out_md),
                "completion_score_pct": score,
                "remaining_gap_count": len(remaining_gaps),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
