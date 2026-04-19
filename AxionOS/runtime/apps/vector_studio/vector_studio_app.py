import json
import sys
from pathlib import Path

SHARED = Path(__file__).resolve().parents[1] / "_shared"
if str(SHARED) not in sys.path:
    sys.path.append(str(SHARED))

from productivity_runtime import (
    edit_document as runtime_edit_document,
    export_document as runtime_export_document,
    open_document as runtime_open_document,
    snapshot as runtime_snapshot,
)


APP_ID = "vector_studio"
APP_NAME = "Vector Studio"
DEFAULT_EXTENSION = "svg"
SUPPORTED_EXPORTS = ["svg", "pdf", "png"]


def open_document(doc_name: str | None = None):
    return runtime_open_document(
        app_id=APP_ID,
        app_name=APP_NAME,
        doc_name=doc_name,
        default_extension=DEFAULT_EXTENSION,
    )


def edit_document(doc_name: str | None = None, append_text: str = ""):
    return runtime_edit_document(
        app_id=APP_ID,
        app_name=APP_NAME,
        doc_name=doc_name,
        default_extension=DEFAULT_EXTENSION,
        append_text=append_text,
    )


def export_document(doc_name: str | None = None, export_format: str | None = None):
    return runtime_export_document(
        app_id=APP_ID,
        app_name=APP_NAME,
        doc_name=doc_name,
        default_extension=DEFAULT_EXTENSION,
        export_format=export_format,
        supported_exports=SUPPORTED_EXPORTS,
    )


def snapshot():
    return runtime_snapshot(
        app_id=APP_ID,
        app_name=APP_NAME,
        replacement_for=["Illustrator"],
        engines=["inkscape_style_vector_pipeline"],
        default_extension=DEFAULT_EXTENSION,
        supported_exports=SUPPORTED_EXPORTS,
    )


if __name__ == "__main__":
    print(json.dumps(snapshot(), indent=2))
