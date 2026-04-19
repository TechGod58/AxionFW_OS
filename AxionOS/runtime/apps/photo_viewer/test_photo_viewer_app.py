from pathlib import Path

from photo_viewer_app import open_photo, snapshot


def test_photo_viewer_opens_real_image():
    out = open_photo("unit_photo.png")
    assert out["ok"] is True
    assert out["code"] == "PHOTO_VIEW_OK"
    assert Path(out["file"]).exists()
    assert (out.get("image") or {}).get("width", 0) > 0
    assert (out.get("image") or {}).get("channels", 0) == 3


def test_photo_viewer_snapshot_exposes_engine():
    snap = snapshot()
    assert snap["app"] == "Photo Viewer"
    assert snap["engine"] == "pillow_opencv"
