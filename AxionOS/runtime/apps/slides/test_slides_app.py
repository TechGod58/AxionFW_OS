from pathlib import Path

from slides_app import edit_document, export_document, open_document, snapshot


def test_slides_roundtrip_runtime_contract():
    opened = open_document("unit_slides")
    assert opened["ok"] is True

    edited = edit_document("unit_slides", append_text="slide_title=Quarterly Review")
    assert edited["ok"] is True

    exported = export_document("unit_slides", export_format="pptx")
    assert exported["ok"] is True
    assert exported["source_sha256"] == edited["sha256"]
    assert Path(exported["file"]).exists()

    snap = snapshot()
    assert snap["operations"]["open_document"] is True
    assert "pptx" in snap["supported_exports"]
