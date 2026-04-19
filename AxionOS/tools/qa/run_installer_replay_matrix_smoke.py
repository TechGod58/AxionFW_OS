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

from app_runtime_launcher import execute_installer_request, load_installer_matrix, build_installer_provenance_envelope

OUT = axion_path("out", "qa")
OUT.mkdir(parents=True, exist_ok=True)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_vector(family: str, profile: str, extension: str) -> dict[str, Any]:
    installer = f"matrix_{family}_{profile}{extension}"
    provenance = build_installer_provenance_envelope(
        installer,
        family=family,
        profile=profile,
        app_id=f"matrix_{family}_{profile}",
        source_commit_sha="0808080808080808080808080808080808080808",
        build_pipeline_id="axion-qa-installer-matrix",
    )
    first = execute_installer_request(
        installer_path=installer,
        corr="corr_installer_replay_first",
        family=family,
        profile=profile,
        app_id=f"matrix_{family}_{profile}",
        allow_live_installer=False,
        provenance=provenance,
    )
    second = execute_installer_request(
        installer_path=installer,
        corr="corr_installer_replay_second",
        family=family,
        profile=profile,
        app_id=f"matrix_{family}_{profile}",
        allow_live_installer=False,
        provenance=provenance,
    )
    sig_a = (((first.get("installer_replay") or {}).get("signature")) or "")
    sig_b = (((second.get("installer_replay") or {}).get("signature")) or "")
    ok = bool(first.get("ok")) and bool(second.get("ok")) and bool(sig_a) and (sig_a == sig_b)
    return {
        "family": family,
        "profile": profile,
        "installer": installer,
        "ok": ok,
        "first_code": first.get("code"),
        "second_code": second.get("code"),
        "first_signature": sig_a,
        "second_signature": sig_b,
    }


def main() -> None:
    matrix = load_installer_matrix()
    families = matrix.get("families", {})

    vectors: list[dict[str, Any]] = []
    for family, meta in families.items():
        extensions = [str(x) for x in meta.get("extensions", [])]
        profiles = [str(x) for x in meta.get("profiles", [])]
        if not extensions:
            continue
        ext = extensions[0]
        for profile in profiles:
            vectors.append(run_vector(str(family), profile, ext))

    failed = [v for v in vectors if not bool(v.get("ok"))]
    summary = {
        "ts": now_iso(),
        "suite": "installer_replay_matrix_smoke",
        "total": len(vectors),
        "failed": len(failed),
        "ok": len(failed) == 0,
        "vectors": vectors,
    }

    out_json = OUT / "installer_replay_matrix_smoke_summary.json"
    out_md = OUT / "installer_replay_matrix_smoke_summary.md"
    out_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    md_lines = [
        "# Installer Replay Matrix Smoke",
        "",
        f"- Timestamp: {summary['ts']}",
        f"- Total vectors: {summary['total']}",
        f"- Failed: {summary['failed']}",
        f"- Overall: {'PASS' if summary['ok'] else 'FAIL'}",
        "",
        "## Vectors",
    ]
    for v in vectors:
        md_lines.append(f"- [{'PASS' if v['ok'] else 'FAIL'}] {v['family']} / {v['profile']} -> {v['installer']}")
    out_md.write_text("\n".join(md_lines), encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": summary["ok"],
                "summary_json": str(out_json),
                "summary_md": str(out_md),
                "total": summary["total"],
                "failed": summary["failed"],
            },
            indent=2,
        )
    )
    raise SystemExit(0 if summary["ok"] else 1)


if __name__ == "__main__":
    main()
