from __future__ import annotations

import json
import ntpath
import re
from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath
from typing import Any

AXION_ROOT = Path(__file__).resolve().parents[2]
PROFILE_POLICY_PATH = AXION_ROOT / "config" / "PROFILE_SHELL_FOLDERS_V1.json"
FOLDER_VAULT_POLICY_PATH = AXION_ROOT / "config" / "PROFILE_FOLDER_VAULT_DOMAINS_V1.json"
FOLDER_DOMAIN_MANIFEST = ".axion_folder_vault_domain.json"
AUDIT_PATH = AXION_ROOT / "data" / "audit" / "profile_sandbox_guard.ndjson"

FOLDER_TOKEN_ALIASES = {
    "connectios": "connections",
}

DOMAIN_ID_ALIASES = {
    "profile.vault.connectios": "profile.vault.connections",
}

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _audit(event: dict[str, Any]) -> None:
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    row = dict(event)
    row.setdefault("ts", _now_iso())
    with AUDIT_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")


def _default_policy() -> dict[str, Any]:
    return {
        "version": 2,
        "policyId": "AXION_PROFILE_SHELL_FOLDERS_V1",
        "profileRootBase": "data\\profiles",
        "savePolicy": {
            "mode": "persistent_profile_sandboxes",
            "allowedTargets": ["Documents", "Downloads", "Photos", "Music"],
        },
        "folders": {
            "archives": {"pathSegment": "Archives", "legacyAlias": "Documents"},
            "photos": {"pathSegment": "Photos", "legacyAlias": "Pictures"},
            "downloads": {"pathSegment": "Downloads", "legacyAlias": "Downloads"},
            "music": {"pathSegment": "Music", "legacyAlias": "Music"},
            "workspace": {"pathSegment": "Workspace", "legacyAlias": "Desktop"},
            "videos": {"pathSegment": "Videos", "legacyAlias": "Videos"},
            "connections": {
                "pathSegment": "Connections",
                "legacyAlias": "Links",
                "aliases": ["Connectios"],
                "pathSegmentAliases": ["Connectios"],
            },
        },
    }


def _default_folder_vault_policy() -> dict[str, Any]:
    return {
        "version": 1,
        "policyId": "AXION_PROFILE_FOLDER_VAULT_DOMAINS_V1",
        "folders": {
            "archives": {"domainId": "profile.vault.archives"},
            "downloads": {"domainId": "profile.vault.downloads"},
            "photos": {"domainId": "profile.vault.photos"},
            "music": {"domainId": "profile.vault.music"},
            "videos": {"domainId": "profile.vault.videos"},
            "workspace": {"domainId": "profile.vault.workspace"},
            "favorites_bar": {"domainId": "profile.vault.favorites_bar"},
            "searches": {"domainId": "profile.vault.searches"},
            "connections": {
                "domainId": "profile.vault.connections",
                "domainAliases": ["profile.vault.connectios"],
                "aliases": ["connectios"],
            },
        },
    }


def load_profile_policy() -> dict[str, Any]:
    if not PROFILE_POLICY_PATH.exists():
        return _default_policy()
    try:
        obj = _load_json(PROFILE_POLICY_PATH)
    except Exception:
        return _default_policy()
    if not isinstance(obj, dict):
        return _default_policy()
    if not isinstance(obj.get("folders"), dict):
        obj["folders"] = {}
    if not isinstance(obj.get("savePolicy"), dict):
        obj["savePolicy"] = {}
    obj.setdefault("profileRootBase", "data\\profiles")
    return obj


def load_folder_vault_policy() -> dict[str, Any]:
    if not FOLDER_VAULT_POLICY_PATH.exists():
        return _default_folder_vault_policy()
    try:
        obj = _load_json(FOLDER_VAULT_POLICY_PATH)
    except Exception:
        return _default_folder_vault_policy()
    if not isinstance(obj, dict):
        return _default_folder_vault_policy()
    if not isinstance(obj.get("folders"), dict):
        obj["folders"] = {}
    obj.setdefault("policyId", "AXION_PROFILE_FOLDER_VAULT_DOMAINS_V1")
    obj.setdefault("version", 1)
    return obj


def _slug(value: str | None) -> str:
    text = re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower()).strip("_")
    return text


def _canonical_folder_token(value: str | None) -> str:
    token = _slug(value)
    if not token:
        return token
    return FOLDER_TOKEN_ALIASES.get(token, token)


def _canonical_domain_id(value: str | None) -> str:
    text = str(value or "").strip()
    if not text:
        return text
    return DOMAIN_ID_ALIASES.get(text, text)


def _resolve_profile_root_base(raw_base: str) -> Path:
    text = str(raw_base or "").strip()
    if not text:
        return AXION_ROOT / "data" / "profiles"
    pure = PureWindowsPath(text)
    if pure.is_absolute():
        parts = pure.parts
        if len(parts) >= 2 and parts[0].lower().startswith("c:") and parts[1].lower() == "axionos":
            tail = list(parts[2:])
            return AXION_ROOT.joinpath(*tail) if tail else AXION_ROOT
        return Path(text)
    return AXION_ROOT.joinpath(*Path(text).parts)


def _profile_root_aliases(raw_base: str, resolved_base: Path) -> list[Path]:
    aliases: list[Path] = [resolved_base]
    text = str(raw_base or "").strip()
    if text:
        pure = PureWindowsPath(text)
        if pure.is_absolute():
            raw_path = Path(text)
            if str(raw_path).lower() != str(resolved_base).lower():
                aliases.append(raw_path)
    return aliases


def _folder_entry_aliases(key: str, entry: dict[str, Any]) -> list[str]:
    aliases = [key]
    aliases.append(str(entry.get("displayName") or ""))
    aliases.append(str(entry.get("legacyAlias") or ""))
    aliases.append(str(entry.get("windowsBehavior") or ""))
    aliases.append(str(entry.get("pathSegment") or ""))
    for field in ("aliases", "displayAliases", "pathSegmentAliases"):
        values = entry.get(field)
        if isinstance(values, list):
            aliases.extend(str(x) for x in values)
    return [x for x in aliases if str(x).strip()]


def _folder_segment_map(policy: dict[str, Any]) -> dict[str, str]:
    folders = dict(policy.get("folders") or {})
    out: dict[str, str] = {}
    for key, raw_entry in folders.items():
        if not isinstance(raw_entry, dict):
            continue
        segment = str(raw_entry.get("pathSegment") or key).strip()
        if not segment:
            continue
        out[_canonical_folder_token(str(key))] = segment
        for alias in _folder_entry_aliases(str(key), raw_entry):
            token = _canonical_folder_token(alias)
            if token:
                out[token] = segment
    return out


def _folder_key_by_segment(policy: dict[str, Any]) -> dict[str, str]:
    folders = dict(policy.get("folders") or {})
    out: dict[str, str] = {}
    for key, raw_entry in folders.items():
        if not isinstance(raw_entry, dict):
            continue
        segment = str(raw_entry.get("pathSegment") or key).strip()
        if not segment:
            continue
        out[segment.lower()] = str(key)
        aliases = raw_entry.get("pathSegmentAliases")
        if isinstance(aliases, list):
            for alias in aliases:
                text = str(alias).strip()
                if text:
                    out[text.lower()] = str(key)
    return out


def _selected_segments(
    policy: dict[str, Any],
    *,
    allowed_folders: list[str] | None = None,
) -> list[str]:
    segment_map = _folder_segment_map(policy)
    if allowed_folders:
        selected: list[str] = []
        for item in allowed_folders:
            token = _canonical_folder_token(item)
            if token and token in segment_map:
                seg = segment_map[token]
                if seg not in selected:
                    selected.append(seg)
        return selected

    targets = list((policy.get("savePolicy") or {}).get("allowedTargets") or [])
    if targets:
        selected = []
        for item in targets:
            token = _canonical_folder_token(str(item))
            if token and token in segment_map:
                seg = segment_map[token]
                if seg not in selected:
                    selected.append(seg)
        if selected:
            return selected

    seen: list[str] = []
    for seg in segment_map.values():
        if seg not in seen:
            seen.append(seg)
    return seen


def profile_sandbox_roots(
    *,
    profile_id: str = "p1",
    allowed_folders: list[str] | None = None,
    include_alias_segments: bool = False,
) -> list[Path]:
    policy = load_profile_policy()
    raw_base = str(policy.get("profileRootBase") or "")
    base = _resolve_profile_root_base(raw_base)
    aliases = _profile_root_aliases(raw_base, base)
    segments = _selected_segments(policy, allowed_folders=allowed_folders)
    alias_segments: list[str] = []
    if include_alias_segments:
        folders = dict(policy.get("folders") or {})
        selected_set = {str(x).strip().lower() for x in segments}
        for entry in folders.values():
            if not isinstance(entry, dict):
                continue
            canonical = str(entry.get("pathSegment") or "").strip()
            if not canonical or canonical.lower() not in selected_set:
                continue
            values = entry.get("pathSegmentAliases")
            if not isinstance(values, list):
                continue
            for value in values:
                alias = str(value).strip()
                if alias and alias not in alias_segments:
                    alias_segments.append(alias)
    all_segments = list(segments) + alias_segments

    roots: list[Path] = []
    seen: set[str] = set()
    for root_base in aliases:
        for segment in all_segments:
            p = root_base / str(profile_id) / str(segment)
            key = str(p).lower()
            if key not in seen:
                seen.add(key)
                roots.append(p)
    return roots


def _ensure_folder_vault_manifest(
    root: Path,
    *,
    profile_id: str,
    policy: dict[str, Any],
    folder_key_by_segment: dict[str, str],
    vault_policy: dict[str, Any],
) -> dict[str, Any]:
    segment = str(root.name)
    folder_key = str(folder_key_by_segment.get(segment.lower(), _canonical_folder_token(segment) or segment))
    folder_entry = dict((vault_policy.get("folders") or {}).get(folder_key, {}) or {})
    domain_id = _canonical_domain_id(str(folder_entry.get("domainId") or f"profile.vault.{folder_key}"))
    domain_aliases = []
    values = folder_entry.get("domainAliases")
    if isinstance(values, list):
        for value in values:
            alias = str(value).strip()
            if alias and alias not in domain_aliases:
                domain_aliases.append(alias)
    manifest = root / FOLDER_DOMAIN_MANIFEST
    obj = {
        "policyId": str(vault_policy.get("policyId") or "AXION_PROFILE_FOLDER_VAULT_DOMAINS_V1"),
        "profilePolicyId": str(policy.get("policyId") or "AXION_PROFILE_SHELL_FOLDERS_V1"),
        "profileId": str(profile_id),
        "folderKey": folder_key,
        "folderSegment": segment,
        "domainId": domain_id,
        "domainAliases": domain_aliases,
        "sandboxTier": "folder_vault",
        "lastIssuedUtc": _now_iso(),
    }
    manifest.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
    return {"ok": True, "manifest": str(manifest), "domainId": domain_id, "folderKey": folder_key}


def ensure_profile_sandbox_storage(
    *,
    profile_id: str = "p1",
    allowed_folders: list[str] | None = None,
    corr: str | None = None,
) -> dict[str, Any]:
    policy = load_profile_policy()
    vault_policy = load_folder_vault_policy()
    segment_key_map = _folder_key_by_segment(policy)
    roots = profile_sandbox_roots(profile_id=profile_id, allowed_folders=allowed_folders)
    created: list[str] = []
    manifests: list[dict[str, str]] = []
    errors: list[dict[str, str]] = []
    for root in roots:
        try:
            root.mkdir(parents=True, exist_ok=True)
            created.append(str(root))
            mf = _ensure_folder_vault_manifest(
                root,
                profile_id=str(profile_id),
                policy=policy,
                folder_key_by_segment=segment_key_map,
                vault_policy=vault_policy,
            )
            manifests.append(
                {
                    "manifest": str(mf.get("manifest")),
                    "domainId": str(mf.get("domainId")),
                    "folderKey": str(mf.get("folderKey")),
                }
            )
        except Exception as ex:
            errors.append({"path": str(root), "error": str(ex)})
    ok = len(errors) == 0
    out = {
        "ok": ok,
        "code": "PROFILE_SANDBOX_STORAGE_READY" if ok else "PROFILE_SANDBOX_STORAGE_FAILED",
        "profile_id": str(profile_id),
        "roots": created,
        "vault_manifests": manifests,
        "errors": errors,
    }
    _audit(
        {
            "event": "profile.sandbox.storage.ensure",
            "ok": ok,
            "profile_id": profile_id,
            "roots": len(created),
            "vault_manifests": len(manifests),
            "errors": len(errors),
            "corr": corr,
        }
    )
    return out


def _norm_windows_path(value: str) -> str:
    return ntpath.normcase(ntpath.normpath(str(value or "").strip()))


def _path_within(path: str, root: str) -> bool:
    p = _norm_windows_path(path)
    r = _norm_windows_path(root)
    if not p or not r:
        return False
    if p == r:
        return True
    return p.startswith(r + "\\")


def _matched_profile_root(path: str, roots: list[str]) -> str | None:
    best: str | None = None
    best_len = -1
    for root in roots:
        if not _path_within(path, root):
            continue
        size = len(_norm_windows_path(root))
        if size > best_len:
            best = root
            best_len = size
    return best


def _read_folder_domain(root: str) -> str | None:
    manifest = Path(root) / FOLDER_DOMAIN_MANIFEST
    if not manifest.exists():
        return None
    try:
        obj = _load_json(manifest)
    except Exception:
        return None
    domain = _canonical_domain_id(str(obj.get("domainId") or "").strip())
    return domain or None


def evaluate_web_download_target(
    *,
    save_path: str | None,
    profile_id: str = "p1",
    allowed_folders: list[str] | None = None,
    require_target: bool = True,
    require_profile_sandbox_target: bool = True,
    deny_direct_c_root: bool = True,
    required_vault_domains: list[str] | None = None,
    app_id: str | None = None,
    corr: str | None = None,
) -> dict[str, Any]:
    raw = str(save_path or "").strip()
    if not raw:
        out = {
            "ok": not require_target,
            "code": "PROFILE_SANDBOX_TARGET_REQUIRED" if require_target else "PROFILE_SANDBOX_TARGET_SKIPPED",
            "save_path": None,
            "profile_id": profile_id,
            "app_id": app_id,
        }
        _audit({"event": "profile.sandbox.web_download.evaluate", **out, "corr": corr})
        return out

    if not ntpath.isabs(raw):
        out = {
            "ok": True,
            "code": "PROFILE_SANDBOX_TARGET_NONABS_UNCHECKED",
            "save_path": raw,
            "profile_id": profile_id,
            "app_id": app_id,
        }
        _audit({"event": "profile.sandbox.web_download.evaluate", **out, "corr": corr})
        return out

    roots = [
        str(x)
        for x in profile_sandbox_roots(
            profile_id=profile_id,
            allowed_folders=allowed_folders,
            include_alias_segments=True,
        )
    ]
    in_profile_root = any(_path_within(raw, root) for root in roots)
    c_drive = _norm_windows_path(raw).startswith(_norm_windows_path("C:\\"))

    code = "PROFILE_SANDBOX_WEB_DOWNLOAD_ALLOWED"
    ok = True
    matched_root = _matched_profile_root(raw, roots) if in_profile_root else None
    target_vault_domain = _read_folder_domain(str(matched_root)) if matched_root else None
    if require_profile_sandbox_target and not in_profile_root:
        ok = False
        code = "PROFILE_SANDBOX_TARGET_OUTSIDE_ALLOWED_ROOTS"
    if deny_direct_c_root and c_drive and not in_profile_root:
        ok = False
        code = "PROFILE_SANDBOX_C_ROOT_BLOCKED"
    if ok and in_profile_root and required_vault_domains:
        allow = {_canonical_domain_id(str(x).strip()) for x in required_vault_domains if str(x).strip()}
        if not target_vault_domain:
            ok = False
            code = "PROFILE_SANDBOX_FOLDER_DOMAIN_UNRESOLVED"
        elif target_vault_domain not in allow:
            ok = False
            code = "PROFILE_SANDBOX_FOLDER_DOMAIN_BLOCKED"

    out = {
        "ok": ok,
        "code": code,
        "save_path": raw,
        "profile_id": profile_id,
        "app_id": app_id,
        "in_profile_root": in_profile_root,
        "target_vault_domain": target_vault_domain,
        "allowed_roots": roots,
    }
    _audit({"event": "profile.sandbox.web_download.evaluate", **{k: v for k, v in out.items() if k != "allowed_roots"}, "corr": corr})
    return out
