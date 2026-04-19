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


APP_ID = "notepad_plus_plus"
APP_NAME = "Notepad++"
DEFAULT_EXTENSION = "txt"
SUPPORTED_EXPORTS = ["txt", "md", "html"]


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
    out = runtime_snapshot(
        app_id=APP_ID,
        app_name=APP_NAME,
        replacement_for=["Notepad++"],
        engines=["text_editor_runtime"],
        default_extension=DEFAULT_EXTENSION,
        supported_exports=SUPPORTED_EXPORTS,
    )
    out["distribution_mode"] = "preinstalled_open_source_binary"
    out["license"] = "GPL-3.0-or-later"
    return out


if __name__ == "__main__":
    print(json.dumps(snapshot(), indent=2))
