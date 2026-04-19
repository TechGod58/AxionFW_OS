import json
from hashlib import sha256
from pathlib import Path

import promoted
from codes import EXIT_OK, EXIT_POLICY, EXIT_SCAN


def _policy(approved_root: Path, max_bytes: int = 4096) -> dict:
    return {
        "zones": {
            "projects": {
                "enabled": True,
                "root": str(approved_root),
                "maxBytes": max_bytes,
                "allowedMimePrefixes": ["application/", "text/"],
                "blockedExtensions": [".exe", ".dll", ".ps1", ".bat", ".sys"],
            }
        },
        "disallowedZones": [],
    }


def _meta_for(path: Path, *, safe_uri: str, mime_type: str) -> dict:
    return {
        "corr": "corr_test_001",
        "artifact_id": "art_test_001",
        "component_id": "comp_test",
        "source_vm": "vm_test",
        "safe_uri": safe_uri,
        "sha256": sha256(path.read_bytes()).hexdigest(),
        "mimeType": mime_type,
        "sizeBytes": path.stat().st_size,
        "ts": "2026-04-17T00:00:00Z",
    }


def _write_meta(meta_path: Path, meta_obj: dict) -> None:
    meta_path.write_text(json.dumps(meta_obj, indent=2), encoding="utf-8")


def test_process_once_promotes_valid_json(tmp_path, monkeypatch):
    inbox = tmp_path / "inbox"
    quarantine = tmp_path / "quarantine"
    approved = tmp_path / "approved"
    audit = tmp_path / "promotion.ndjson"
    inbox.mkdir(parents=True)

    monkeypatch.setattr(promoted, "load_policy", lambda: _policy(approved))

    artifact = inbox / "payload.json"
    artifact.write_text('{"status":"ok"}', encoding="utf-8")
    meta_obj = _meta_for(
        artifact,
        safe_uri="safe://projects/demo/payload.json",
        mime_type="application/json",
    )
    meta_path = inbox / "payload.meta.json"
    _write_meta(meta_path, meta_obj)

    rc = promoted.process_once(str(artifact), str(meta_path), str(quarantine), str(audit))
    assert rc == EXIT_OK

    ok, code, resolved = promoted.resolve_safe_uri(meta_obj["safe_uri"], _policy(approved), meta_obj)
    assert ok and code == "MAP_OK"
    assert resolved is not None
    assert Path(resolved).exists()
    assert "PROMOTE_OK" in audit.read_text(encoding="utf-8")


def test_process_once_rejects_executable_magic(tmp_path, monkeypatch):
    inbox = tmp_path / "inbox"
    quarantine = tmp_path / "quarantine"
    approved = tmp_path / "approved"
    audit = tmp_path / "promotion.ndjson"
    inbox.mkdir(parents=True)

    monkeypatch.setattr(promoted, "load_policy", lambda: _policy(approved))

    artifact = inbox / "payload.bin"
    artifact.write_bytes(b"MZ\x90\x00not-a-real-exe")
    meta_obj = _meta_for(
        artifact,
        safe_uri="safe://projects/demo/payload.bin",
        mime_type="application/octet-stream",
    )
    meta_path = inbox / "payload.meta.json"
    _write_meta(meta_path, meta_obj)

    rc = promoted.process_once(str(artifact), str(meta_path), str(quarantine), str(audit))
    assert rc == EXIT_SCAN
    assert (quarantine / "payload.bin").exists()

    audit_text = audit.read_text(encoding="utf-8")
    assert "REJECT_SCAN" in audit_text
    assert "SCAN_FAIL_EXECUTABLE_MAGIC" in audit_text


def test_process_once_rejects_policy_size(tmp_path, monkeypatch):
    inbox = tmp_path / "inbox"
    quarantine = tmp_path / "quarantine"
    approved = tmp_path / "approved"
    audit = tmp_path / "promotion.ndjson"
    inbox.mkdir(parents=True)

    monkeypatch.setattr(promoted, "load_policy", lambda: _policy(approved, max_bytes=8))

    artifact = inbox / "oversize.json"
    artifact.write_text('{"big":"payload"}', encoding="utf-8")
    meta_obj = _meta_for(
        artifact,
        safe_uri="safe://projects/demo/oversize.json",
        mime_type="application/json",
    )
    meta_path = inbox / "oversize.meta.json"
    _write_meta(meta_path, meta_obj)

    rc = promoted.process_once(str(artifact), str(meta_path), str(quarantine), str(audit))
    assert rc == EXIT_POLICY
    assert (quarantine / "oversize.json").exists()

    audit_text = audit.read_text(encoding="utf-8")
    assert "REJECT_POLICY" in audit_text
    assert "MAP_FAIL_POLICY_SIZE" in audit_text

