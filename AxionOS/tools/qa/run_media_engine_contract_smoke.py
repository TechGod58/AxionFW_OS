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

SHARED = axion_path("runtime", "apps", "_shared")
if str(SHARED) not in sys.path:
    sys.path.append(str(SHARED))

from media_engine import (
    apply_filter_image,
    ensure_deterministic_image,
    ensure_deterministic_video,
    extract_video_thumbnail,
    inspect_video,
    resolve_ffmpeg,
)

OUT = axion_path("out", "qa")
OUT.mkdir(parents=True, exist_ok=True)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> int:
    media_root = axion_path("data", "apps", "media_contract")
    media_root.mkdir(parents=True, exist_ok=True)
    image_path = media_root / "contract_image.png"
    filtered_path = media_root / "contract_image_filtered.png"
    video_path = media_root / "contract_video.mp4"
    thumb_path = media_root / "contract_video_thumb.png"

    ffmpeg = resolve_ffmpeg()
    checks = []

    checks.append(
        {
            "name": "ffmpeg_available",
            "ok": bool(ffmpeg.get("available")),
            "details": ffmpeg,
        }
    )

    image_out = ensure_deterministic_image(image_path)
    checks.append(
        {
            "name": "deterministic_image_ready",
            "ok": bool(image_out.get("ok")),
            "details": {
                "code": image_out.get("code"),
                "sha256": image_out.get("sha256"),
                "width": image_out.get("width"),
                "height": image_out.get("height"),
            },
        }
    )

    filter_out = apply_filter_image(image_path, filtered_path, filter_name="edge", strength=1.0)
    checks.append(
        {
            "name": "photo_filter_pipeline_ready",
            "ok": bool(filter_out.get("ok")),
            "details": {
                "code": filter_out.get("code"),
                "output_sha256": ((filter_out.get("output") or {}).get("sha256")),
            },
        }
    )

    video_out = ensure_deterministic_video(video_path)
    checks.append(
        {
            "name": "deterministic_video_ready",
            "ok": bool(video_out.get("ok")),
            "details": {
                "code": video_out.get("code"),
                "ffmpeg": ffmpeg,
            },
        }
    )

    inspected = inspect_video(video_path)
    checks.append(
        {
            "name": "video_inspection_ready",
            "ok": bool(inspected.get("ok")) and int(inspected.get("frame_count", 0)) > 0,
            "details": {
                "code": inspected.get("code"),
                "frame_count": inspected.get("frame_count"),
                "media_signature": inspected.get("media_signature"),
            },
        }
    )

    thumb = extract_video_thumbnail(video_path, thumb_path)
    checks.append(
        {
            "name": "video_thumbnail_ready",
            "ok": bool(thumb.get("ok")),
            "details": {
                "code": thumb.get("code"),
                "thumb_sha256": ((thumb.get("thumbnail") or {}).get("sha256")),
            },
        }
    )

    checks_failed = sum(1 for c in checks if not bool(c.get("ok")))
    summary = {
        "ts": now_iso(),
        "suite": "media_engine_contract_smoke",
        "checks_total": len(checks),
        "checks_failed": checks_failed,
        "ok": checks_failed == 0,
        "checks": checks,
        "ffmpeg": ffmpeg,
        "artifacts": {
            "image": str(image_path),
            "filtered_image": str(filtered_path),
            "video": str(video_path),
            "thumbnail": str(thumb_path),
        },
    }

    out_json = OUT / "media_engine_contract_smoke_summary.json"
    out_md = OUT / "media_engine_contract_smoke_summary.md"
    out_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    out_md.write_text(
        "\n".join(
            [
                "# Media Engine Contract Smoke",
                "",
                f"- Timestamp: {summary['ts']}",
                f"- Checks: {summary['checks_total']}",
                f"- Failed: {summary['checks_failed']}",
                f"- Overall: {'PASS' if summary['ok'] else 'FAIL'}",
                f"- FFmpeg source: {ffmpeg.get('source')}",
                "",
                "## Checks",
                *[f"- [{'PASS' if c['ok'] else 'FAIL'}] {c['name']}" for c in checks],
            ]
        )
        + "\n",
        encoding="utf-8",
    )

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
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
