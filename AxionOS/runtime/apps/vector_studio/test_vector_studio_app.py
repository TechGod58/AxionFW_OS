from pathlib import Path

from vector_studio_app import edit_document, export_document, open_document, snapshot


def test_vector_studio_roundtrip_runtime_contract():
    opened = open_document("unit_vector")
    assert opened["ok"] is True

    edited = edit_document("unit_vector", append_text="shape=triangle")
    assert edited["ok"] is True

    exported = export_document("unit_vector", export_format="png")
    assert exported["ok"] is True
    assert exported["source_sha256"] == edited["sha256"]
    assert Path(exported["file"]).exists()

    snap = snapshot()
    assert snap["operations"]["edit_document"] is True
    assert "png" in snap["supported_exports"]
