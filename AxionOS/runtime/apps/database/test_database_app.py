from pathlib import Path

from database_app import edit_document, export_document, open_document, snapshot


def test_database_roundtrip_runtime_contract():
    opened = open_document("unit_database")
    assert opened["ok"] is True

    edited = edit_document("unit_database", append_text="table=devices")
    assert edited["ok"] is True

    exported = export_document("unit_database", export_format="sqlite")
    assert exported["ok"] is True
    assert exported["source_sha256"] == edited["sha256"]
    assert Path(exported["file"]).exists()

    snap = snapshot()
    assert snap["operations"]["export_document"] is True
    assert "sqlite" in snap["supported_exports"]
