from __future__ import annotations

import os
import sys
from pathlib import Path


def _seed_test_sys_path() -> None:
    root = Path(__file__).resolve().parent
    extra = [
        root / "runtime" / "allocator",
        root / "runtime" / "device_fabric",
    ]
    for p in extra:
        s = str(p)
        if p.exists() and s not in sys.path:
            sys.path.insert(0, s)


def _seed_test_runtime_path() -> None:
    root = Path(__file__).resolve().parent
    py_dir = root / "tools" / "runtime" / "python311"
    py_scripts = py_dir / "Scripts"
    parts = [str(root), str(py_dir), str(py_scripts)]
    current = os.environ.get("PATH", "")
    merged = ";".join(parts + [current])
    os.environ["PATH"] = merged


def pytest_sessionstart(session) -> None:  # type: ignore[no-untyped-def]
    _seed_test_sys_path()
    _seed_test_runtime_path()
    # Test-only seed keys so provenance signatures stay deterministic in pytest.
    os.environ.setdefault("AXION_KMS_RELEASE_SIGNING_KEY_01", "pytest-kms-release-signing-key-01")
    os.environ.setdefault("AXION_HSM_RELEASE_SIGNING_KEY_02", "pytest-hsm-release-signing-key-02")
