from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

AXION_ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = AXION_ROOT / "config" / "INSTALLER_MODULE_PROVENANCE_POLICY_V1.json"

_COMMIT_RE = re.compile(r"^[0-9a-f]{7,64}$", re.IGNORECASE)

_DEFAULT_POLICY: dict[str, Any] = {
    "version": 2,
    "policyId": "AXION_INSTALLER_MODULE_PROVENANCE_POLICY_V1",
    "defaults": {
        "signature_algorithm": "sha256-keyed-v1",
        "default_signing_key_id": "axion-release-key-01",
    },
    "allowed_signature_algorithms": ["sha256-keyed-v1"],
    "enforcement": {
        "installers": {
            "enabled": True,
            "fail_closed": True,
            "max_provenance_age_hours": 168,
            "allowed_pipeline_prefixes": ["axion-", "release-"],
        },
        "modules": {
            "enabled": True,
            "fail_closed": True,
            "max_provenance_age_hours": 168,
            "allowed_pipeline_prefixes": ["axion-", "release-"],
        },
    },
    "key_source_policy": {
        "require_external_sources": True,
        "allow_inline_material": False,
        "allowed_source_types": ["kms_env", "hsm_env"],
        "test_mode_fallback": {
            "enabled": False,
            "env_flag": "AXION_PROVENANCE_ALLOW_TEST_KEY_FALLBACK",
            "allow_pytest_context": False,
        },
    },
    "rotation_policy": {
        "enforced": True,
        "require_rotation_group": True,
        "require_monotonic_versions": True,
        "require_single_active_per_group": True,
        "require_staged_successor_for_active": True,
        "allowed_signing_statuses": ["active"],
        "verification_allowed_statuses": ["active", "retired"],
    },
    "trusted_keys": {
        "axion-release-key-01": {
            "status": "active",
            "algorithm": "sha256-keyed-v1",
            "source": {"type": "kms_env", "ref": "AXION_KMS_RELEASE_SIGNING_KEY_01"},
            "allowed_subjects": ["installer", "module"],
            "rotation_group": "axion-release-provenance",
            "version": 1,
            "activated_utc": "2026-04-01T00:00:00Z",
            "retire_after_utc": "2026-10-01T00:00:00Z",
            "next_key_id": "axion-release-key-02",
        },
        "axion-release-key-02": {
            "status": "staged",
            "algorithm": "sha256-keyed-v1",
            "source": {"type": "hsm_env", "ref": "AXION_HSM_RELEASE_SIGNING_KEY_02"},
            "allowed_subjects": ["installer", "module"],
            "rotation_group": "axion-release-provenance",
            "version": 2,
            "activated_utc": "2026-09-15T00:00:00Z",
            "retire_after_utc": "2027-03-15T00:00:00Z",
        },
    },
}


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _to_path(value: str | Path) -> Path:
    return value if isinstance(value, Path) else Path(str(value))


def _to_int(value: Any) -> int | None:
    try:
        if value is None:
            return None
        return int(value)
    except Exception:
        return None


def _iso_to_utc(raw: str) -> datetime | None:
    text = str(raw or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except Exception:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _sanitize_json(value: Any) -> Any:
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for k in sorted(value.keys(), key=lambda x: str(x)):
            out[str(k)] = _sanitize_json(value[k])
        return out
    if isinstance(value, list):
        return [_sanitize_json(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _subject_scope(subject_type: str) -> str | None:
    key = str(subject_type or "").strip().lower()
    if key == "installer":
        return "installers"
    if key == "module":
        return "modules"
    return None


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for k, v in (override or {}).items():
        if isinstance(out.get(k), dict) and isinstance(v, dict):
            out[k] = _deep_merge(dict(out[k]), v)
        else:
            out[k] = v
    return out


def _is_truthy(value: Any) -> bool:
    return str(value or "").strip().lower() in ("1", "true", "yes", "on")


def _test_fallback_enabled(policy: dict[str, Any]) -> bool:
    cfg = ((policy.get("key_source_policy") or {}).get("test_mode_fallback") or {})
    if not bool(cfg.get("enabled", False)):
        return False
    env_flag = str(cfg.get("env_flag") or "AXION_PROVENANCE_ALLOW_TEST_KEY_FALLBACK")
    if env_flag and _is_truthy(os.getenv(env_flag)):
        return True
    if bool(cfg.get("allow_pytest_context", False)) and bool(os.getenv("PYTEST_CURRENT_TEST")):
        return True
    return False


def load_policy() -> dict[str, Any]:
    if not POLICY_PATH.exists():
        return dict(_DEFAULT_POLICY)
    try:
        raw = json.loads(POLICY_PATH.read_text(encoding="utf-8-sig"))
    except Exception:
        return dict(_DEFAULT_POLICY)
    if not isinstance(raw, dict):
        return dict(_DEFAULT_POLICY)
    return _deep_merge(dict(_DEFAULT_POLICY), raw)


def _artifact_digest(artifact_path: str | Path) -> str:
    p = _to_path(artifact_path)
    try:
        rp = p.resolve()
    except Exception:
        rp = p
    canonical = str(rp).replace("\\", "/").strip().lower()
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _key_validity_window(key_entry: dict[str, Any]) -> tuple[datetime | None, datetime | None]:
    start = _iso_to_utc(str(key_entry.get("activated_utc") or key_entry.get("not_before_utc") or ""))
    end = _iso_to_utc(str(key_entry.get("retire_after_utc") or key_entry.get("not_after_utc") or ""))
    return (start, end)


def _source_info(key_entry: dict[str, Any]) -> tuple[str | None, str | None]:
    source = key_entry.get("source")
    if isinstance(source, dict):
        stype = str(source.get("type") or "").strip().lower()
        ref = str(source.get("ref") or source.get("env_var") or "").strip()
        return (stype or None, ref or None)
    if isinstance(source, str):
        text = source.strip()
        if text.lower().startswith("kms_env://"):
            return ("kms_env", text.split("://", 1)[1].strip() or None)
        if text.lower().startswith("hsm_env://"):
            return ("hsm_env", text.split("://", 1)[1].strip() or None)
        if text.lower().startswith("env://"):
            return ("kms_env", text.split("://", 1)[1].strip() or None)
    return (None, None)


def _resolve_key_material(policy: dict[str, Any], key_id: str, key_entry: dict[str, Any]) -> dict[str, Any]:
    source_policy = policy.get("key_source_policy", {}) if isinstance(policy, dict) else {}
    require_external = bool(source_policy.get("require_external_sources", True))
    allow_inline = bool(source_policy.get("allow_inline_material", False))
    inline_material = str(key_entry.get("material", "")).strip()

    stype, ref = _source_info(key_entry)
    if stype is None and inline_material:
        if allow_inline and not require_external:
            return {"ok": True, "material": inline_material, "source_type": "inline"}
        return {
            "ok": False,
            "code": "PROVENANCE_INLINE_KEY_MATERIAL_FORBIDDEN",
            "trusted_key_id": key_id,
        }

    if stype is None:
        if inline_material and allow_inline:
            return {"ok": True, "material": inline_material, "source_type": "inline"}
        if _test_fallback_enabled(policy):
            return {
                "ok": True,
                "material": f"AXION_TEST_FALLBACK::{key_id}",
                "source_type": "test_fallback",
                "source_ref": None,
            }
        return {
            "ok": False,
            "code": "PROVENANCE_KEY_SOURCE_MISSING",
            "trusted_key_id": key_id,
        }

    allowed_types = [str(x).strip().lower() for x in source_policy.get("allowed_source_types", []) if str(x).strip()]
    if allowed_types and stype not in allowed_types:
        return {
            "ok": False,
            "code": "PROVENANCE_KEY_SOURCE_TYPE_FORBIDDEN",
            "trusted_key_id": key_id,
            "source_type": stype,
            "allowed_source_types": allowed_types,
        }

    if not ref:
        return {
            "ok": False,
            "code": "PROVENANCE_KEY_SOURCE_INVALID",
            "trusted_key_id": key_id,
            "source_type": stype,
        }

    material = os.getenv(ref)
    if material:
        return {
            "ok": True,
            "material": material,
            "source_type": stype,
            "source_ref": ref,
        }

    if _test_fallback_enabled(policy):
        return {
            "ok": True,
            "material": f"AXION_TEST_FALLBACK::{key_id}::{ref}",
            "source_type": "test_fallback",
            "source_ref": ref,
        }

    return {
        "ok": False,
        "code": "PROVENANCE_KEY_SOURCE_UNAVAILABLE",
        "trusted_key_id": key_id,
        "source_type": stype,
        "source_ref": ref,
    }


def _enforce_rotation_lock(policy: dict[str, Any], now_utc: datetime) -> dict[str, Any]:
    settings = (policy.get("rotation_policy") or {}) if isinstance(policy, dict) else {}
    if not bool(settings.get("enforced", True)):
        return {"ok": True, "code": "PROVENANCE_ROTATION_POLICY_DISABLED", "violations": []}

    keys = policy.get("trusted_keys", {})
    if not isinstance(keys, dict) or not keys:
        return {
            "ok": False,
            "code": "PROVENANCE_KEY_ROTATION_POLICY_VIOLATION",
            "violations": [{"code": "missing_trusted_keys", "detail": "no trusted keys configured"}],
        }

    violations: list[dict[str, Any]] = []
    require_group = bool(settings.get("require_rotation_group", True))
    require_monotonic = bool(settings.get("require_monotonic_versions", True))
    require_single_active = bool(settings.get("require_single_active_per_group", True))
    require_successor = bool(settings.get("require_staged_successor_for_active", True))

    groups: dict[str, list[tuple[str, dict[str, Any]]]] = {}
    active_seen = 0

    for key_id, entry in keys.items():
        if not isinstance(entry, dict):
            violations.append({"code": "invalid_key_entry", "key_id": key_id})
            continue

        group = str(entry.get("rotation_group", "")).strip()
        if require_group and not group:
            violations.append({"code": "rotation_group_missing", "key_id": key_id})
        if not group:
            group = "__default__"
        groups.setdefault(group, []).append((str(key_id), entry))

        if require_monotonic and _to_int(entry.get("version")) is None:
            violations.append({"code": "key_version_missing", "key_id": key_id})

        st = str(entry.get("status", "active")).strip().lower()
        if st == "active":
            active_seen += 1

        start, end = _key_validity_window(entry)
        if start is not None and end is not None and start >= end:
            violations.append({"code": "key_window_invalid", "key_id": key_id})

    if active_seen == 0:
        violations.append({"code": "no_active_key"})

    for group, entries in groups.items():
        active = [(kid, e) for kid, e in entries if str(e.get("status", "active")).strip().lower() == "active"]
        if require_single_active and len(active) != 1:
            violations.append({"code": "active_key_count_invalid", "group": group, "count": len(active)})

        if require_monotonic:
            versions = []
            for kid, e in entries:
                v = _to_int(e.get("version"))
                if v is None:
                    continue
                versions.append((v, kid))
            if versions:
                raw = [v for v, _ in sorted(versions)]
                if len(raw) != len(set(raw)):
                    violations.append({"code": "duplicate_key_version", "group": group, "versions": raw})

        if not require_successor:
            continue
        for active_key_id, active_entry in active:
            next_key_id = str(active_entry.get("next_key_id", "")).strip()
            if not next_key_id:
                violations.append({"code": "active_successor_missing", "key_id": active_key_id, "group": group})
                continue
            next_entry = keys.get(next_key_id)
            if not isinstance(next_entry, dict):
                violations.append({"code": "active_successor_unknown", "key_id": active_key_id, "next_key_id": next_key_id})
                continue
            next_status = str(next_entry.get("status", "")).strip().lower()
            if next_status not in ("staged", "active"):
                violations.append({"code": "active_successor_not_staged", "key_id": active_key_id, "next_key_id": next_key_id, "next_status": next_status})
            if require_group and str(next_entry.get("rotation_group", "")).strip() != str(active_entry.get("rotation_group", "")).strip():
                violations.append({"code": "active_successor_group_mismatch", "key_id": active_key_id, "next_key_id": next_key_id})
            if require_monotonic:
                current_v = _to_int(active_entry.get("version"))
                next_v = _to_int(next_entry.get("version"))
                if current_v is not None and next_v is not None and next_v <= current_v:
                    violations.append({"code": "active_successor_version_not_newer", "key_id": active_key_id, "next_key_id": next_key_id})

    if violations:
        return {
            "ok": False,
            "code": "PROVENANCE_KEY_ROTATION_POLICY_VIOLATION",
            "violations": violations,
        }
    return {
        "ok": True,
        "code": "PROVENANCE_KEY_ROTATION_POLICY_LOCKED",
        "violations": [],
    }


def materialize_subject(
    subject_type: str,
    artifact_path: str | Path,
    *,
    family: str | None = None,
    profile: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    stype = str(subject_type or "").strip().lower()
    artifact = _to_path(artifact_path)
    out: dict[str, Any] = {
        "subject_type": stype,
        "artifact_name": artifact.name,
        "artifact_path": str(artifact),
        "artifact_sha256": _artifact_digest(artifact),
    }
    if family is not None:
        out["family"] = str(family).strip().lower()
    if profile is not None:
        out["profile"] = str(profile).strip()
    if isinstance(metadata, dict) and metadata:
        out["metadata"] = _sanitize_json(metadata)
    return out


def _sign_subject(
    *,
    subject: dict[str, Any],
    provenance: dict[str, Any],
    trusted_key_id: str,
    key_material: str,
) -> str:
    payload = {
        "subject": _sanitize_json(subject),
        "provenance": {
            "source_commit_sha": str((provenance or {}).get("source_commit_sha", "")).strip().lower(),
            "build_pipeline_id": str((provenance or {}).get("build_pipeline_id", "")).strip(),
            "issued_utc": str((provenance or {}).get("issued_utc", "")).strip(),
        },
    }
    signing_input = _canonical_json(payload) + "|" + str(trusted_key_id) + "|" + str(key_material)
    return hashlib.sha256(signing_input.encode("utf-8")).hexdigest()


def _subject_allowed(subject_type: str, key_entry: dict[str, Any]) -> bool:
    allowed_subjects = [str(x).lower() for x in key_entry.get("allowed_subjects", [])]
    return not allowed_subjects or str(subject_type).lower() in allowed_subjects


def _signing_status_allowed(policy: dict[str, Any], key_entry: dict[str, Any]) -> bool:
    settings = policy.get("rotation_policy", {}) if isinstance(policy, dict) else {}
    allowed = [str(x).strip().lower() for x in settings.get("allowed_signing_statuses", ["active"]) if str(x).strip()]
    status = str(key_entry.get("status", "active")).strip().lower()
    return status in allowed


def _signing_window_allowed(key_entry: dict[str, Any], now_utc: datetime) -> bool:
    start, end = _key_validity_window(key_entry)
    if start is not None and now_utc < start:
        return False
    if end is not None and now_utc > end:
        return False
    return True


def _select_trusted_key(policy: dict[str, Any], subject_type: str, preferred_key_id: str | None, now_utc: datetime) -> tuple[str, dict[str, Any]] | tuple[None, None]:
    keys = policy.get("trusted_keys", {})
    if not isinstance(keys, dict):
        return (None, None)

    if preferred_key_id:
        entry = keys.get(str(preferred_key_id))
        if isinstance(entry, dict) and _subject_allowed(subject_type, entry) and _signing_status_allowed(policy, entry) and _signing_window_allowed(entry, now_utc):
            return (str(preferred_key_id), entry)
        return (None, None)

    candidates: list[tuple[int, str, dict[str, Any]]] = []
    for key_id, entry in keys.items():
        if not isinstance(entry, dict):
            continue
        if not _subject_allowed(subject_type, entry):
            continue
        if not _signing_status_allowed(policy, entry):
            continue
        if not _signing_window_allowed(entry, now_utc):
            continue
        v = _to_int(entry.get("version"))
        candidates.append((v if v is not None else -1, str(key_id), entry))

    if not candidates:
        return (None, None)

    candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
    _, key_id, entry = candidates[0]
    return (key_id, entry)


def issue_provenance_envelope(
    *,
    subject_type: str,
    artifact_path: str | Path,
    family: str | None = None,
    profile: str | None = None,
    metadata: dict[str, Any] | None = None,
    source_commit_sha: str | None = None,
    build_pipeline_id: str | None = None,
    trusted_key_id: str | None = None,
    issued_utc: str | None = None,
) -> dict[str, Any]:
    policy = load_policy()
    now = _now_utc()

    lock = _enforce_rotation_lock(policy, now)
    if not bool(lock.get("ok")):
        return {
            "ok": False,
            "code": "PROVENANCE_KEY_ROTATION_POLICY_VIOLATION",
            "rotation_lock": lock,
        }

    preferred = trusted_key_id or str(((policy.get("defaults") or {}).get("default_signing_key_id") or "")).strip() or None
    key_id, key_entry = _select_trusted_key(policy, subject_type=subject_type, preferred_key_id=preferred, now_utc=now)
    if key_id is None or key_entry is None:
        return {"ok": False, "code": "PROVENANCE_TRUSTED_KEY_UNAVAILABLE"}

    key_material_resolved = _resolve_key_material(policy, key_id, key_entry)
    if not bool(key_material_resolved.get("ok")):
        return {
            "ok": False,
            "code": str(key_material_resolved.get("code") or "PROVENANCE_KEY_SOURCE_UNAVAILABLE"),
            "trusted_key_id": key_id,
            "key_source": key_material_resolved,
        }

    subject = materialize_subject(
        subject_type,
        artifact_path,
        family=family,
        profile=profile,
        metadata=metadata,
    )
    provenance = {
        "source_commit_sha": str(source_commit_sha or "0000000000000000000000000000000000000000").strip().lower(),
        "build_pipeline_id": str(build_pipeline_id or "axion-release-unknown").strip(),
        "issued_utc": str(issued_utc or now.isoformat()),
    }
    algo = str(key_entry.get("algorithm") or (policy.get("defaults", {}) or {}).get("signature_algorithm") or "sha256-keyed-v1")
    signature = _sign_subject(
        subject=subject,
        provenance=provenance,
        trusted_key_id=key_id,
        key_material=str(key_material_resolved.get("material", "")),
    )
    envelope = {
        "subject": subject,
        "provenance": provenance,
        "trusted_key_id": key_id,
        "signature_algorithm": algo,
        "signature": signature,
    }
    return {
        "ok": True,
        "code": "PROVENANCE_ENVELOPE_ISSUED",
        "envelope": envelope,
    }


def verify_provenance_envelope(
    *,
    subject_type: str,
    artifact_path: str | Path,
    envelope: dict[str, Any] | None,
    family: str | None = None,
    profile: str | None = None,
    metadata: dict[str, Any] | None = None,
    now_utc: datetime | None = None,
) -> dict[str, Any]:
    policy = load_policy()
    now = now_utc or _now_utc()

    lock = _enforce_rotation_lock(policy, now)
    if not bool(lock.get("ok")):
        return {
            "ok": False,
            "code": "PROVENANCE_KEY_ROTATION_POLICY_VIOLATION",
            "subject_type": subject_type,
            "rotation_lock": lock,
        }

    scope_name = _subject_scope(subject_type)
    if scope_name is None:
        return {
            "ok": False,
            "code": "PROVENANCE_SUBJECT_TYPE_UNKNOWN",
            "subject_type": subject_type,
        }

    scope = ((policy.get("enforcement") or {}).get(scope_name) or {})
    enabled = bool(scope.get("enabled", True))
    fail_closed = bool(scope.get("fail_closed", True))
    if not enabled:
        return {"ok": True, "code": "PROVENANCE_POLICY_DISABLED", "subject_type": subject_type}
    if not isinstance(envelope, dict):
        return {
            "ok": False if fail_closed else True,
            "code": "PROVENANCE_ENVELOPE_MISSING" if fail_closed else "PROVENANCE_ENVELOPE_SKIPPED",
            "subject_type": subject_type,
        }

    subject_expected = materialize_subject(
        subject_type,
        artifact_path,
        family=family,
        profile=profile,
        metadata=metadata,
    )
    subject = envelope.get("subject")
    if not isinstance(subject, dict):
        return {"ok": False, "code": "PROVENANCE_SUBJECT_INVALID", "subject_type": subject_type}
    if _canonical_json(_sanitize_json(subject)) != _canonical_json(_sanitize_json(subject_expected)):
        return {
            "ok": False,
            "code": "PROVENANCE_SUBJECT_MISMATCH",
            "subject_type": subject_type,
            "expected_subject": subject_expected,
            "provided_subject": _sanitize_json(subject),
        }

    provenance = envelope.get("provenance")
    if not isinstance(provenance, dict):
        return {"ok": False, "code": "PROVENANCE_FIELDS_MISSING", "subject_type": subject_type, "missing": ["provenance"]}
    missing_fields = [
        field
        for field in ("source_commit_sha", "build_pipeline_id", "issued_utc", "trusted_key_id", "signature_algorithm", "signature")
        if not str(envelope.get(field, "") if field.startswith("signature") or field == "trusted_key_id" else provenance.get(field, "")).strip()
    ]
    if missing_fields:
        return {"ok": False, "code": "PROVENANCE_FIELDS_MISSING", "subject_type": subject_type, "missing": missing_fields}

    commit = str(provenance.get("source_commit_sha", "")).strip().lower()
    if _COMMIT_RE.fullmatch(commit) is None:
        return {"ok": False, "code": "PROVENANCE_SOURCE_COMMIT_INVALID", "subject_type": subject_type, "source_commit_sha": commit}

    pipeline_id = str(provenance.get("build_pipeline_id", "")).strip()
    allowed_prefixes = [str(x) for x in scope.get("allowed_pipeline_prefixes", []) if str(x).strip()]
    if allowed_prefixes and not any(pipeline_id.startswith(prefix) for prefix in allowed_prefixes):
        return {
            "ok": False,
            "code": "PROVENANCE_PIPELINE_UNTRUSTED",
            "subject_type": subject_type,
            "build_pipeline_id": pipeline_id,
            "allowed_prefixes": allowed_prefixes,
        }

    issued = _iso_to_utc(str(provenance.get("issued_utc", "")))
    if issued is None:
        return {"ok": False, "code": "PROVENANCE_ISSUED_TIME_INVALID", "subject_type": subject_type}

    max_age = int(scope.get("max_provenance_age_hours", 168))
    age_hours = (now - issued).total_seconds() / 3600.0
    if age_hours < -1.0:
        return {
            "ok": False,
            "code": "PROVENANCE_ISSUED_TIME_IN_FUTURE",
            "subject_type": subject_type,
            "issued_utc": issued.isoformat(),
        }
    if max_age > 0 and age_hours > float(max_age):
        return {
            "ok": False,
            "code": "PROVENANCE_EXPIRED",
            "subject_type": subject_type,
            "age_hours": age_hours,
            "max_age_hours": max_age,
        }

    trusted_key_id = str(envelope.get("trusted_key_id", "")).strip()
    keys = policy.get("trusted_keys", {})
    key_entry = keys.get(trusted_key_id) if isinstance(keys, dict) else None
    if not isinstance(key_entry, dict):
        return {
            "ok": False,
            "code": "PROVENANCE_TRUSTED_KEY_UNKNOWN",
            "subject_type": subject_type,
            "trusted_key_id": trusted_key_id,
        }

    settings = policy.get("rotation_policy", {}) if isinstance(policy, dict) else {}
    verify_status_allowed = [str(x).strip().lower() for x in settings.get("verification_allowed_statuses", ["active", "retired"]) if str(x).strip()]
    key_status = str(key_entry.get("status", "active")).strip().lower()
    if key_status not in verify_status_allowed:
        return {
            "ok": False,
            "code": "PROVENANCE_TRUSTED_KEY_STATUS_REJECTED",
            "subject_type": subject_type,
            "trusted_key_id": trusted_key_id,
            "key_status": key_status,
        }

    if not _subject_allowed(subject_type, key_entry):
        allowed_subjects = [str(x).lower() for x in key_entry.get("allowed_subjects", [])]
        return {
            "ok": False,
            "code": "PROVENANCE_TRUSTED_KEY_SCOPE_MISMATCH",
            "subject_type": subject_type,
            "trusted_key_id": trusted_key_id,
            "allowed_subjects": allowed_subjects,
        }

    start, end = _key_validity_window(key_entry)
    if start is not None and issued < start:
        return {
            "ok": False,
            "code": "PROVENANCE_KEY_NOT_YET_VALID_FOR_ISSUED_TIME",
            "subject_type": subject_type,
            "trusted_key_id": trusted_key_id,
            "issued_utc": issued.isoformat(),
            "key_activated_utc": start.isoformat(),
        }
    if end is not None and issued > end:
        return {
            "ok": False,
            "code": "PROVENANCE_KEY_EXPIRED_FOR_ISSUED_TIME",
            "subject_type": subject_type,
            "trusted_key_id": trusted_key_id,
            "issued_utc": issued.isoformat(),
            "key_retire_after_utc": end.isoformat(),
        }

    signature_algorithm = str(envelope.get("signature_algorithm", "")).strip()
    globally_allowed = [str(x) for x in policy.get("allowed_signature_algorithms", [])]
    if globally_allowed and signature_algorithm not in globally_allowed:
        return {
            "ok": False,
            "code": "PROVENANCE_SIGNATURE_ALGORITHM_UNSUPPORTED",
            "subject_type": subject_type,
            "signature_algorithm": signature_algorithm,
        }
    if str(key_entry.get("algorithm", "")).strip() and str(key_entry.get("algorithm")).strip() != signature_algorithm:
        return {
            "ok": False,
            "code": "PROVENANCE_SIGNATURE_ALGORITHM_MISMATCH",
            "subject_type": subject_type,
            "signature_algorithm": signature_algorithm,
            "trusted_key_algorithm": str(key_entry.get("algorithm")),
        }

    key_material_resolved = _resolve_key_material(policy, trusted_key_id, key_entry)
    if not bool(key_material_resolved.get("ok")):
        return {
            "ok": False,
            "code": str(key_material_resolved.get("code") or "PROVENANCE_KEY_SOURCE_UNAVAILABLE"),
            "subject_type": subject_type,
            "trusted_key_id": trusted_key_id,
            "key_source": key_material_resolved,
        }

    expected_signature = _sign_subject(
        subject=_sanitize_json(subject),
        provenance=_sanitize_json(provenance),
        trusted_key_id=trusted_key_id,
        key_material=str(key_material_resolved.get("material", "")),
    )
    provided_signature = str(envelope.get("signature", "")).strip().lower()
    if not secrets.compare_digest(expected_signature, provided_signature):
        return {
            "ok": False,
            "code": "PROVENANCE_SIGNATURE_INVALID",
            "subject_type": subject_type,
            "trusted_key_id": trusted_key_id,
        }

    subject_hash = hashlib.sha256(_canonical_json(_sanitize_json(subject)).encode("utf-8")).hexdigest()
    return {
        "ok": True,
        "code": "PROVENANCE_VERIFIED",
        "subject_type": subject_type,
        "subject_hash": subject_hash,
        "trusted_key_id": trusted_key_id,
        "signature_algorithm": signature_algorithm,
        "issued_utc": issued.isoformat(),
        "build_pipeline_id": pipeline_id,
        "source_commit_sha": commit,
    }
