from pathlib import Path

from publisher_app import edit_document, export_document, open_document, snapshot


def test_publisher_roundtrip_runtime_contract():
    opened = open_document("unit_publisher")
    assert opened["ok"] is True

    edited = edit_document("unit_publisher", append_text="layout=brochure")
    assert edited["ok"] is True

    exported = export_document("unit_publisher", export_format="pdf")
    assert exported["ok"] is True
    assert exported["source_sha256"] == edited["sha256"]
    assert Path(exported["file"]).exists()

    snap = snapshot()
    assert snap["operations"]["open_document"] is True
    assert "pdf" in snap["supported_exports"]
