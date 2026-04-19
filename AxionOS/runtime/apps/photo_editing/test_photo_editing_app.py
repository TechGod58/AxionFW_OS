from pathlib import Path

from photo_editing_app import apply_filter, snapshot


def test_photo_editing_generates_real_output():
    out = apply_filter("unit_edit", "grayscale")
    assert out["ok"] is True
    assert out["code"] == "PHOTO_EDIT_OK"
    assert Path(out["file"]).exists()
    assert (out.get("output") or {}).get("width", 0) > 0


def test_photo_editing_is_deterministic_for_same_input():
    first = apply_filter("unit_edit_deterministic", "edge")
    second = apply_filter("unit_edit_deterministic", "edge")
    assert first["ok"] is True and second["ok"] is True
    assert (first.get("output") or {}).get("sha256") == (second.get("output") or {}).get("sha256")


def test_photo_editing_snapshot_reports_outputs():
    snap = snapshot()
    assert snap["app"] == "Photo Editing"
    assert snap["engine"] == "pillow_opencv"
    assert isinstance(snap["count"], int)
