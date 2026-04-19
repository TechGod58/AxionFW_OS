from pathlib import Path

from notepad_plus_plus_app import edit_document, export_document, open_document, snapshot


def test_notepad_plus_plus_roundtrip_runtime_contract():
    opened = open_document("unit_npp")
    assert opened["ok"] is True

    edited = edit_document("unit_npp", append_text="line=hello from npp")
    assert edited["ok"] is True

    exported = export_document("unit_npp", export_format="md")
    assert exported["ok"] is True
    assert exported["source_sha256"] == edited["sha256"]
    assert Path(exported["file"]).exists()

    snap = snapshot()
    assert snap["operations"]["export_document"] is True
    assert "md" in snap["supported_exports"]
