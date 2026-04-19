import importlib.util
from pathlib import Path


def _load_module(module_name: str, file_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load module: {file_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_productivity_creative_wrapper_snapshots():
    root = Path(__file__).resolve().parent
    targets = [
        ("write_app", root / "write" / "write_app.py", "write"),
        ("sheets_app", root / "sheets" / "sheets_app.py", "sheets"),
        ("slides_app", root / "slides" / "slides_app.py", "slides"),
        ("mail_app", root / "mail" / "mail_app.py", "mail"),
        ("database_app", root / "database" / "database_app.py", "database"),
        ("publisher_app", root / "publisher" / "publisher_app.py", "publisher"),
        ("pdf_studio_app", root / "pdf_studio" / "pdf_studio_app.py", "pdf_studio"),
        ("vector_studio_app", root / "vector_studio" / "vector_studio_app.py", "vector_studio"),
        ("creative_studio_app", root / "creative_studio" / "creative_studio_app.py", "creative_studio"),
        ("notepad_plus_plus_app", root / "notepad_plus_plus" / "notepad_plus_plus_app.py", "notepad_plus_plus"),
    ]
    for module_name, file_path, app_id in targets:
        module = _load_module(module_name, file_path)
        out = module.snapshot()
        assert out.get("ready") is True
        assert out.get("app_id") == app_id


def test_productivity_creative_replacement_metadata():
    root = Path(__file__).resolve().parent
    write = _load_module("write_app_meta", root / "write" / "write_app.py").snapshot()
    sheets = _load_module("sheets_app_meta", root / "sheets" / "sheets_app.py").snapshot()
    slides = _load_module("slides_app_meta", root / "slides" / "slides_app.py").snapshot()
    pdf = _load_module("pdf_studio_app_meta", root / "pdf_studio" / "pdf_studio_app.py").snapshot()
    vector = _load_module("vector_studio_app_meta", root / "vector_studio" / "vector_studio_app.py").snapshot()
    creative = _load_module("creative_studio_app_meta", root / "creative_studio" / "creative_studio_app.py").snapshot()
    assert "Word" in (write.get("replacement_for") or [])
    assert "Excel" in (sheets.get("replacement_for") or [])
    assert "PowerPoint" in (slides.get("replacement_for") or [])
    assert "Acrobat" in (pdf.get("replacement_for") or [])
    assert "Illustrator" in (vector.get("replacement_for") or [])
    assert "Photoshop" in (creative.get("replacement_for") or [])
