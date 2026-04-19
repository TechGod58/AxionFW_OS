from pathlib import Path

from file_explorer_app import list_folder, open_entry, search, snapshot


def test_file_explorer_snapshot_and_listing():
    snap = snapshot()
    assert snap["ok"] is True
    assert snap["app_id"] == "file_explorer"
    listed = list_folder("Workspace")
    assert listed["ok"] is True
    assert listed["code"] == "FILE_EXPLORER_LIST_OK"


def test_file_explorer_can_search_workspace():
    listed = list_folder("Workspace")
    workspace = Path(listed["path"])
    marker = workspace / "unit_explorer_marker.txt"
    marker.write_text("axion", encoding="utf-8")
    out = search("Workspace", "marker")
    assert out["ok"] is True
    assert any(item["name"] == marker.name for item in out["matches"])


def test_file_explorer_accepts_legacy_connections_alias():
    listed = list_folder("Connectios")
    assert listed["ok"] is True
    assert listed["code"] == "FILE_EXPLORER_LIST_OK"


def test_file_explorer_blocks_outside_profile_open():
    out = open_entry(r"C:\Windows\System32")
    assert out["ok"] is False
    assert out["code"] == "FILE_EXPLORER_OUTSIDE_PROFILE_BLOCKED"
