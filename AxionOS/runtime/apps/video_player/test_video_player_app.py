from pathlib import Path

from video_player_app import open_media, snapshot


def test_video_player_open_builds_real_media_and_thumbnail():
    out = open_media()
    assert out["ok"] is True
    assert out["container"] in ("mp4", "mkv", "webm", "avi", "wav", "mp3", "flac")
    assert Path(out["file"]).exists()
    assert (out.get("video") or {}).get("frame_count", 0) > 0
    assert (out.get("video") or {}).get("width", 0) > 0
    assert (out.get("thumbnail") or {}).get("width", 0) > 0
    assert bool(out.get("media_signature"))


def test_video_player_signature_is_deterministic_for_same_file():
    first = open_media()
    second = open_media(path=first["file"])
    assert first["ok"] is True and second["ok"] is True
    assert first["media_signature"] == second["media_signature"]


def test_video_player_snapshot_reports_engine():
    snap = snapshot()
    assert "video" in snap["app"].lower()
    assert snap["engine"] == "ffmpeg_opencv"
    assert isinstance(snap["ffmpeg_available"], bool)
