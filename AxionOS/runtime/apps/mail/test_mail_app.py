from pathlib import Path

from mail_app import edit_document, export_document, open_document, snapshot


def test_mail_roundtrip_runtime_contract():
    opened = open_document("unit_mail")
    assert opened["ok"] is True

    edited = edit_document("unit_mail", append_text="subject=Axion Test Message")
    assert edited["ok"] is True

    exported = export_document("unit_mail", export_format="mbox")
    assert exported["ok"] is True
    assert exported["source_sha256"] == edited["sha256"]
    assert Path(exported["file"]).exists()

    snap = snapshot()
    assert snap["operations"]["edit_document"] is True
    assert "mbox" in snap["supported_exports"]
