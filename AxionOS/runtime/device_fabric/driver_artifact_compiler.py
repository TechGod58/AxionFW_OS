from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_TOOLS_DIR = None
for _parent in Path(__file__).resolve().parents:
    if (_parent / "tools" / "common" / "pathing.py").exists():
        _TOOLS_DIR = _parent / "tools"
        break
if _TOOLS_DIR and str(_TOOLS_DIR) not in sys.path:
    sys.path.append(str(_TOOLS_DIR))

from common.pathing import axion_path


def axion_path_str(*parts: str) -> str:
    return str(axion_path(*parts))


SECURITY_DIR = Path(axion_path_str("runtime", "security"))
if str(SECURITY_DIR) not in sys.path:
    sys.path.append(str(SECURITY_DIR))

from provenance_guard import issue_provenance_envelope, verify_provenance_envelope


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return default


def _save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sanitize_driver_id(text: str) -> str:
    cleaned = "".join(ch if (ch.isalnum() or ch == "_") else "_" for ch in str(text))
    cleaned = cleaned.strip("_")
    return cleaned or "unknown_driver"


def _bundle_fingerprint(bundle_dir: Path) -> str:
    hasher = hashlib.sha256()
    files = sorted([p for p in bundle_dir.rglob("*") if p.is_file()], key=lambda p: str(p).lower())
    for path in files:
        rel = path.relative_to(bundle_dir).as_posix().encode("utf-8")
        hasher.update(rel)
        hasher.update(b"\x00")
        try:
            blob = path.read_bytes()
        except Exception:
            blob = b""
        hasher.update(hashlib.sha256(blob).digest())
        hasher.update(b"\x00")
    return hasher.hexdigest()


def compile_driver_bundle_to_signed_artifact(
    *,
    bundle_dir: str | Path,
    artifact_root: str | Path,
    build_pipeline_id: str,
    source_commit_sha: str,
    trusted_key_id: str | None = None,
) -> dict[str, Any]:
    bundle_path = Path(bundle_dir)
    manifest_path = bundle_path / "bundle_manifest.json"
    manifest = _load_json(manifest_path, {})
    if not isinstance(manifest, dict):
        return {
            "ok": False,
            "code": "DRIVER_ARTIFACT_MANIFEST_INVALID",
            "bundle_dir": str(bundle_path),
            "manifest_path": str(manifest_path),
        }

    driver_id = _sanitize_driver_id(str(manifest.get("driver_id", "")).strip())
    if not driver_id:
        return {
            "ok": False,
            "code": "DRIVER_ARTIFACT_DRIVER_ID_MISSING",
            "bundle_dir": str(bundle_path),
            "manifest_path": str(manifest_path),
        }

    driver_class = str(manifest.get("driver_class", "device_io")).strip() or "device_io"
    target_family = str(manifest.get("target_family", "generic_x64_uefi")).strip() or "generic_x64_uefi"
    version = str(manifest.get("version", "0.1.0")).strip() or "0.1.0"
    bundle_hash = _bundle_fingerprint(bundle_path)

    artifact_dir = Path(artifact_root) / driver_id
    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = artifact_dir / f"{driver_id}.axdrv.json"
    provenance_path = artifact_dir / f"{driver_id}.provenance.json"
    receipt_path = artifact_dir / f"{driver_id}.receipt.json"

    build_identity = {
        "driver_id": driver_id,
        "driver_class": driver_class,
        "target_family": target_family,
        "version": version,
        "bundle_hash": bundle_hash,
    }
    image_digest = _sha256_bytes(json.dumps(build_identity, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    loadable = {
        "version": 1,
        "artifact_kind": "axion_kernel_driver_loadable_v1",
        "driver_id": driver_id,
        "driver_class": driver_class,
        "target_family": target_family,
        "driver_version": version,
        "entry_symbol": f"axdrv_{driver_id}_entry",
        "abi": "axion-kernel-abi-v1",
        "bundle_manifest_path": str(manifest_path),
        "bundle_hash": bundle_hash,
        "image_digest_sha256": image_digest,
        "generated_utc": _now_iso(),
    }
    _save_json(artifact_path, loadable)

    issue = issue_provenance_envelope(
        subject_type="module",
        artifact_path=str(artifact_path),
        metadata={
            "driver_id": driver_id,
            "driver_class": driver_class,
            "target_family": target_family,
            "artifact_kind": "driver_loadable",
        },
        source_commit_sha=source_commit_sha,
        build_pipeline_id=build_pipeline_id,
        trusted_key_id=trusted_key_id,
    )
    if not bool(issue.get("ok")):
        return {
            "ok": False,
            "code": str(issue.get("code") or "DRIVER_ARTIFACT_SIGN_FAILED"),
            "bundle_dir": str(bundle_path),
            "artifact_path": str(artifact_path),
            "issue": issue,
        }

    envelope = dict(issue.get("envelope") or {})
    _save_json(provenance_path, envelope)
    verify = verify_provenance_envelope(
        subject_type="module",
        artifact_path=str(artifact_path),
        envelope=envelope,
        metadata={
            "driver_id": driver_id,
            "driver_class": driver_class,
            "target_family": target_family,
            "artifact_kind": "driver_loadable",
        },
    )
    if not bool(verify.get("ok")):
        return {
            "ok": False,
            "code": str(verify.get("code") or "DRIVER_ARTIFACT_VERIFY_FAILED"),
            "bundle_dir": str(bundle_path),
            "artifact_path": str(artifact_path),
            "provenance_path": str(provenance_path),
            "verify": verify,
        }

    receipt = {
        "version": 1,
        "driver_id": driver_id,
        "driver_class": driver_class,
        "target_family": target_family,
        "artifact_path": str(artifact_path),
        "provenance_path": str(provenance_path),
        "status": "compiled_signed_verified",
        "signed_utc": _now_iso(),
        "build_pipeline_id": build_pipeline_id,
        "source_commit_sha": source_commit_sha,
        "trusted_key_id": verify.get("trusted_key_id"),
        "subject_hash": verify.get("subject_hash"),
        "bundle_hash": bundle_hash,
    }
    _save_json(receipt_path, receipt)
    return {
        "ok": True,
        "code": "DRIVER_ARTIFACT_COMPILED_SIGNED",
        "driver_id": driver_id,
        "driver_class": driver_class,
        "target_family": target_family,
        "artifact_path": str(artifact_path),
        "provenance_path": str(provenance_path),
        "receipt_path": str(receipt_path),
        "trusted_key_id": verify.get("trusted_key_id"),
        "subject_hash": verify.get("subject_hash"),
        "bundle_hash": bundle_hash,
    }


def compile_smart_fabric_artifacts(
    *,
    synthesized_drivers: list[dict[str, Any]],
    artifact_root: str | Path | None = None,
    artifact_registry_path: str | Path | None = None,
    build_pipeline_id: str = "axion-smart-driver-fabric",
    source_commit_sha: str = "0000000000000000000000000000000000000000",
    trusted_key_id: str | None = None,
) -> dict[str, Any]:
    output_root = Path(artifact_root) if artifact_root is not None else Path(axion_path_str("data", "drivers", "loadable_artifacts"))
    registry_path = Path(artifact_registry_path) if artifact_registry_path is not None else Path(
        axion_path_str("data", "drivers", "smart_driver_fabric_artifact_registry.json")
    )

    compiled: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []
    for entry in synthesized_drivers or []:
        if not isinstance(entry, dict):
            continue
        bundle_dir = entry.get("bundle_dir")
        if not bundle_dir:
            failed.append({"ok": False, "code": "DRIVER_ARTIFACT_BUNDLE_DIR_MISSING", "entry": entry})
            continue
        result = compile_driver_bundle_to_signed_artifact(
            bundle_dir=Path(str(bundle_dir)),
            artifact_root=output_root,
            build_pipeline_id=str(build_pipeline_id),
            source_commit_sha=str(source_commit_sha),
            trusted_key_id=trusted_key_id,
        )
        if bool(result.get("ok")):
            compiled.append(result)
        else:
            failed.append(result)

    registry = _load_json(registry_path, {"version": 1, "generated_utc": None, "artifacts": []})
    if not isinstance(registry, dict):
        registry = {"version": 1, "generated_utc": None, "artifacts": []}
    existing = {}
    for item in registry.get("artifacts", []):
        if not isinstance(item, dict):
            continue
        key = str(item.get("driver_id", "")).strip()
        if key:
            existing[key] = item
    for item in compiled:
        existing[str(item.get("driver_id"))] = {
            "driver_id": item.get("driver_id"),
            "driver_class": item.get("driver_class"),
            "target_family": item.get("target_family"),
            "artifact_path": item.get("artifact_path"),
            "provenance_path": item.get("provenance_path"),
            "receipt_path": item.get("receipt_path"),
            "trusted_key_id": item.get("trusted_key_id"),
            "subject_hash": item.get("subject_hash"),
            "status": "compiled_signed_verified",
        }
    registry["generated_utc"] = _now_iso()
    registry["artifacts"] = [existing[k] for k in sorted(existing.keys())]
    _save_json(registry_path, registry)

    return {
        "ok": len(failed) == 0,
        "code": "SMART_DRIVER_ARTIFACTS_COMPILED" if len(failed) == 0 else "SMART_DRIVER_ARTIFACTS_PARTIAL",
        "artifact_root": str(output_root),
        "artifact_registry_path": str(registry_path),
        "compiled_artifacts": compiled,
        "failures": failed,
    }
