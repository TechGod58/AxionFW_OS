import json
import argparse
import os
import subprocess
import sys
import re
import importlib.util
from pathlib import Path
from datetime import datetime, timezone
from typing import Any

from installer_execution_adapters import build_adapter, build_replay_signature, extension_chain
from sandbox_projection import ensure_projection, get_projection, projection_app_id
from projection_session_broker import start_or_reconnect_session, heartbeat_session, close_session

AXION_ROOT = Path(__file__).resolve().parents[3]
SECURITY_DIR = AXION_ROOT / "runtime" / "security"
DEVICE_FABRIC_DIR = AXION_ROOT / "runtime" / "device_fabric"
if str(SECURITY_DIR) not in sys.path:
    sys.path.append(str(SECURITY_DIR))
if str(DEVICE_FABRIC_DIR) not in sys.path:
    sys.path.append(str(DEVICE_FABRIC_DIR))

from firewall_guard import start_guard_session, inspect_packets
from packet_source_resolver import resolve_packet_sample
from provenance_guard import verify_provenance_envelope, issue_provenance_envelope
try:
    from smart_driver_fabric import ensure_fabric_initialized as ensure_smart_driver_fabric_initialized
except Exception:
    ensure_smart_driver_fabric_initialized = None
try:
    from qm_ecc_bridge import evaluate_runtime_launch as qm_ecc_evaluate_runtime_launch
except Exception:
    qm_ecc_evaluate_runtime_launch = None
try:
    from network_sandbox_hub import share_internet_to_sandbox as network_share_internet_to_sandbox
except Exception:
    network_share_internet_to_sandbox = None
try:
    from install_sandbox_orchestrator import (
        register_installer_runtime_image,
        find_runtime_image,
        prepare_installer_runtime_context,
    )
except Exception:
    register_installer_runtime_image = None
    find_runtime_image = None
    prepare_installer_runtime_context = None

POLICY_PATH = AXION_ROOT / "config" / "APP_VM_ENFORCEMENT_V1.json"
COMPAT_PATH = AXION_ROOT / "config" / "APP_COMPATIBILITY_ENVIRONMENTS_V1.json"
SYSTEM_POLICY_PATH = AXION_ROOT / "config" / "SYSTEM_PROGRAM_EXECUTION_POLICY_V1.json"
LAYER_PATH = AXION_ROOT / "config" / "COMPATIBILITY_LAYER_CATALOG_V1.json"
CACHE_PATH = AXION_ROOT / "config" / "SANDBOX_SHELL_CACHE_V1.json"
INSTALLER_MATRIX_PATH = AXION_ROOT / "config" / "INSTALLER_COMPATIBILITY_MATRIX_V1.json"
AUDIT_PATH = AXION_ROOT / "data" / "audit" / "app_launch.ndjson"
INSTALLER_REPLAY_PATH = AXION_ROOT / "out" / "runtime" / "installer_execution_replay.ndjson"

APP_ENTRYPOINTS = {
    "command_prompt": str(AXION_ROOT / "runtime" / "apps" / "command_prompt" / "command_prompt_app.py"),
    "powershell": str(AXION_ROOT / "runtime" / "apps" / "powershell" / "powershell_app.py"),
    "run": str(AXION_ROOT / "runtime" / "apps" / "run_dialog" / "run_dialog_app.py"),
    "access_center": str(AXION_ROOT / "runtime" / "apps" / "access_center" / "access_center_app.py"),
    "arcade": str(AXION_ROOT / "runtime" / "apps" / "arcade" / "arcade_app.py"),
    "browser_manager": str(AXION_ROOT / "runtime" / "apps" / "browser_manager" / "browser_manager_app.py"),
    "brave_browser": str(AXION_ROOT / "runtime" / "apps" / "brave_browser" / "brave_browser_app.py"),
    "clock": str(AXION_ROOT / "runtime" / "apps" / "clock" / "clock_app.py"),
    "calendar": str(AXION_ROOT / "runtime" / "apps" / "calendar" / "calendar_app.py"),
    "creative_studio": str(AXION_ROOT / "runtime" / "apps" / "creative_studio" / "creative_studio_app.py"),
    "gallery": str(AXION_ROOT / "runtime" / "apps" / "gallery" / "gallery_app.py"),
    "notes": str(AXION_ROOT / "runtime" / "apps" / "notes" / "notes_app.py"),
    "pdf_studio": str(AXION_ROOT / "runtime" / "apps" / "pdf_studio" / "pdf_studio_app.py"),
    "pdf_view": str(AXION_ROOT / "runtime" / "apps" / "pdf_view" / "pdf_view_app.py"),
    "prompt": str(AXION_ROOT / "runtime" / "apps" / "prompt" / "prompt_app.py"),
    "pulse_monitor": str(AXION_ROOT / "runtime" / "apps" / "pulse_monitor" / "pulse_monitor_app.py"),
    "pad": str(AXION_ROOT / "runtime" / "apps" / "pad" / "pad_app.py"),
    "capture": str(AXION_ROOT / "runtime" / "apps" / "capture" / "capture_app.py"),
    "calculator": str(AXION_ROOT / "runtime" / "apps" / "calculator" / "calculator_app.py"),
    "camera": str(AXION_ROOT / "runtime" / "apps" / "camera" / "camera_app.py"),
    "sheets": str(AXION_ROOT / "runtime" / "apps" / "sheets" / "sheets_app.py"),
    "slides": str(AXION_ROOT / "runtime" / "apps" / "slides" / "slides_app.py"),
    "mail": str(AXION_ROOT / "runtime" / "apps" / "mail" / "mail_app.py"),
    "database": str(AXION_ROOT / "runtime" / "apps" / "database" / "database_app.py"),
    "publisher": str(AXION_ROOT / "runtime" / "apps" / "publisher" / "publisher_app.py"),
    "vector_studio": str(AXION_ROOT / "runtime" / "apps" / "vector_studio" / "vector_studio_app.py"),
    "notepad_plus_plus": str(AXION_ROOT / "runtime" / "apps" / "notepad_plus_plus" / "notepad_plus_plus_app.py"),
    "shell": str(AXION_ROOT / "runtime" / "apps" / "shell" / "shell_app.py"),
    "utilities": str(AXION_ROOT / "runtime" / "apps" / "utilities" / "utilities_app.py"),
    "video_studio": str(AXION_ROOT / "runtime" / "apps" / "video_studio" / "video_studio_app.py"),
    "write": str(AXION_ROOT / "runtime" / "apps" / "write" / "write_app.py"),
    "photo_editing": str(AXION_ROOT / "runtime" / "apps" / "photo_editing" / "photo_editing_app.py"),
    "photo_viewer": str(AXION_ROOT / "runtime" / "apps" / "photo_viewer" / "photo_viewer_app.py"),
    "notepad": str(AXION_ROOT / "runtime" / "apps" / "notepad" / "notepad_app.py"),
    "registry_editor": str(AXION_ROOT / "runtime" / "apps" / "registry_editor" / "registry_editor_app.py"),
    "disk_cleanup": str(AXION_ROOT / "runtime" / "apps" / "disk_cleanup" / "disk_cleanup_app.py"),
    "control_panel": str(AXION_ROOT / "runtime" / "apps" / "control_panel" / "control_panel_app.py"),
    "users_tools": str(AXION_ROOT / "runtime" / "apps" / "users_tools" / "users_tools_app.py"),
    "accessibilities": str(AXION_ROOT / "runtime" / "apps" / "accessibilities" / "accessibilities_app.py"),
    "media_codecs": str(AXION_ROOT / "runtime" / "apps" / "media_codecs" / "media_codecs_app.py"),
    "video_player": str(AXION_ROOT / "runtime" / "apps" / "video_player" / "video_player_app.py"),
    "audio_recorder": str(AXION_ROOT / "runtime" / "apps" / "audio_recorder" / "audio_recorder_app.py"),
    "video_recorder": str(AXION_ROOT / "runtime" / "apps" / "video_recorder" / "video_recorder_app.py"),
    "windows_tools": str(AXION_ROOT / "runtime" / "apps" / "windows_tools" / "windows_tools_app.py"),
    "smart_driver_builder": str(AXION_ROOT / "runtime" / "apps" / "smart_driver_builder" / "smart_driver_builder_app.py"),
    "task_manager": str(AXION_ROOT / "runtime" / "apps" / "task_manager" / "task_manager_app.py"),
    "services": str(AXION_ROOT / "runtime" / "apps" / "services" / "services_app.py"),
    "file_explorer": str(AXION_ROOT / "runtime" / "apps" / "file_explorer" / "file_explorer_app.py"),
    "codex": str(AXION_ROOT / "runtime" / "apps" / "codex" / "codex_app.py"),
}


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def _load_app_module(app_id: str):
    entry = APP_ENTRYPOINTS.get(str(app_id))
    if not entry:
        return None
    entry_path = Path(str(entry))
    if not entry_path.exists():
        return None
    module_name = f"axion_runtime_app_{str(app_id)}"
    spec = importlib.util.spec_from_file_location(module_name, str(entry_path))
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def invoke_app_operation(app_id: str, operation: str, payload: dict[str, Any] | None = None, corr: str = "corr_app_operation_001"):
    op = str(operation or "").strip()
    if not op:
        return {"ok": False, "code": "APP_OPERATION_REQUIRED", "app": str(app_id)}
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", op) is None or op.startswith("_"):
        return {"ok": False, "code": "APP_OPERATION_INVALID_NAME", "app": str(app_id), "operation": op}

    module = _load_app_module(app_id)
    if module is None:
        return {"ok": False, "code": "APP_OPERATION_APP_UNKNOWN", "app": str(app_id), "operation": op}

    fn = getattr(module, op, None)
    if not callable(fn):
        return {"ok": False, "code": "APP_OPERATION_UNSUPPORTED", "app": str(app_id), "operation": op}

    args = dict(payload or {})
    try:
        result = fn(**args)
    except TypeError:
        # Compatibility fallback for zero-arg operations.
        result = fn()
    except Exception as exc:
        out = {
            "ok": False,
            "code": "APP_OPERATION_FAIL",
            "app": str(app_id),
            "operation": op,
            "error": str(exc),
        }
        audit({"corr": corr, "event": "app.operation.fail", **out})
        return out

    ok = bool(result.get("ok")) if isinstance(result, dict) and "ok" in result else True
    out = {
        "ok": ok,
        "code": "APP_OPERATION_OK" if ok else "APP_OPERATION_FAIL",
        "app": str(app_id),
        "operation": op,
        "result": result,
    }
    audit({"corr": corr, "event": "app.operation", **{k: v for k, v in out.items() if k != "result"}})
    return out


def load_json(path: Path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def save_json(path: Path, obj):
    path.write_text(json.dumps(obj, indent=2) + "\n", encoding='utf-8')


def load_policy():
    return load_json(POLICY_PATH)


def load_external_policy():
    cfg = load_json(COMPAT_PATH)
    return cfg.get("external_program_policy", {})


def load_system_program_policy():
    if not SYSTEM_POLICY_PATH.exists():
        return {"apps": {}}
    cfg = load_json(SYSTEM_POLICY_PATH)
    if not isinstance(cfg, dict):
        return {"apps": {}}
    apps = cfg.get("apps", {})
    if not isinstance(apps, dict):
        apps = {}
    return {"apps": apps}


def system_program_entry(app_id: str):
    cfg = load_system_program_policy()
    return dict((cfg.get("apps") or {}).get(str(app_id), {}) or {})


def load_installer_matrix():
    return load_json(INSTALLER_MATRIX_PATH)


def resolve_mode(app_id: str):
    p = load_policy()
    return p.get('apps', {}).get(app_id, p.get('defaultMode', 'capsule'))


def resolve_compatibility(app_id: str, family: str = None, profile: str = None):
    compat = load_json(COMPAT_PATH)
    layers = load_json(LAYER_PATH)
    defaults = layers.get('defaults', {})
    app_cfg = compat.get('apps', {}).get(app_id, {})
    chosen_family = family or app_cfg.get('family', 'native_axion')
    chosen_profile = profile or app_cfg.get('profile') or defaults.get(chosen_family)
    return {
        'family': chosen_family,
        'profile': chosen_profile,
        'execution_model': layers.get('families', {}).get(chosen_family, {}).get('execution_model', 'capsule_native')
    }


def _infer_installer_family(installer_path: str, matrix: dict[str, Any]) -> str | None:
    exts = extension_chain(installer_path)
    if not exts:
        return None
    families = matrix.get("families", {})
    for family in ("windows", "linux"):
        allowed = [str(x).lower() for x in families.get(family, {}).get("extensions", [])]
        if any(ext in allowed for ext in exts):
            return family
    return None


def _resolve_installer_extension(installer_path: str, family: str, matrix: dict[str, Any]) -> str | None:
    allowed = [str(x).lower() for x in matrix.get("families", {}).get(family, {}).get("extensions", [])]
    for ext in extension_chain(installer_path):
        if ext in allowed:
            return ext
    return None


def _resolve_installer_profile(family: str, profile: str | None, matrix: dict[str, Any]) -> str | None:
    profiles = [str(x) for x in matrix.get("families", {}).get(family, {}).get("profiles", [])]
    if not profiles:
        return None
    if profile is None:
        return profiles[-1]
    if str(profile) in profiles:
        return str(profile)
    return None


def resolve_installer_runtime(installer_path: str, family: str = None, profile: str = None) -> dict[str, Any]:
    external = load_external_policy()
    matrix = load_installer_matrix()
    chosen_family = family or _infer_installer_family(installer_path, matrix)
    if chosen_family is None:
        return {
            "ok": False,
            "code": "INSTALLER_UNSUPPORTED_EXTENSION",
            "installer_path": installer_path,
            "family": None,
            "profile": None,
            "execution_model": None,
            "sandbox_enforced": bool(external.get("run_in_sandbox_only", True)),
        }
    chosen_family = str(chosen_family).lower()

    if chosen_family == "windows" and not bool(external.get("allow_windows_programs", False)):
        return {
            "ok": False,
            "code": "INSTALLER_WINDOWS_DISABLED",
            "installer_path": installer_path,
            "family": chosen_family,
            "profile": None,
            "execution_model": None,
            "sandbox_enforced": bool(external.get("run_in_sandbox_only", True)),
        }
    if chosen_family == "linux" and not bool(external.get("allow_linux_programs", False)):
        return {
            "ok": False,
            "code": "INSTALLER_LINUX_DISABLED",
            "installer_path": installer_path,
            "family": chosen_family,
            "profile": None,
            "execution_model": None,
            "sandbox_enforced": bool(external.get("run_in_sandbox_only", True)),
        }

    installer_ext = _resolve_installer_extension(installer_path, chosen_family, matrix)
    if installer_ext is None:
        return {
            "ok": False,
            "code": "INSTALLER_EXTENSION_FAMILY_MISMATCH",
            "installer_path": installer_path,
            "family": chosen_family,
            "profile": profile,
            "execution_model": None,
            "sandbox_enforced": bool(external.get("run_in_sandbox_only", True)),
        }

    chosen_profile = _resolve_installer_profile(chosen_family, profile, matrix)
    if chosen_profile is None:
        return {
            "ok": False,
            "code": "INSTALLER_PROFILE_UNSUPPORTED",
            "installer_path": installer_path,
            "family": chosen_family,
            "profile": profile,
            "execution_model": None,
            "sandbox_enforced": bool(external.get("run_in_sandbox_only", True)),
        }

    compat = resolve_compatibility("external_installer", family=chosen_family, profile=chosen_profile)
    # External Windows/Linux installers always run as sandboxed compatibility images.
    sandbox_required = True if chosen_family in ("windows", "linux") else bool(external.get("run_in_sandbox_only", True))
    execution_model = str(compat.get("execution_model", ""))
    if sandbox_required and not execution_model.startswith("sandbox_"):
        return {
            "ok": False,
            "code": "INSTALLER_SANDBOX_ENFORCEMENT_FAIL",
            "installer_path": installer_path,
            "family": chosen_family,
            "profile": compat.get("profile"),
            "execution_model": execution_model,
            "sandbox_enforced": sandbox_required,
        }

    adapter = build_adapter(chosen_family, chosen_profile, execution_model, sandbox_required)
    adapter_id = None
    if adapter is not None:
        plan = adapter.plan(installer_path)
        if plan.get("ok"):
            adapter_id = plan.get("adapter_id")

    return {
        "ok": True,
        "code": "INSTALLER_RUNTIME_READY",
        "installer_path": installer_path,
        "family": chosen_family,
        "profile": chosen_profile,
        "installer_extension": installer_ext,
        "execution_model": execution_model,
        "sandbox_enforced": sandbox_required,
        "adapter_id": adapter_id,
    }


def _installer_provenance_metadata(app_id: str | None) -> dict[str, Any] | None:
    meta: dict[str, Any] = {}
    if str(app_id or "").strip():
        meta["installer_app_id"] = str(app_id).strip()
    return meta or None


def build_installer_provenance_envelope(
    installer_path: str,
    *,
    family: str | None = None,
    profile: str | None = None,
    app_id: str | None = None,
    source_commit_sha: str | None = None,
    build_pipeline_id: str | None = None,
    trusted_key_id: str | None = None,
) -> dict[str, Any]:
    issued = issue_provenance_envelope(
        subject_type="installer",
        artifact_path=installer_path,
        family=family,
        profile=profile,
        metadata=_installer_provenance_metadata(app_id),
        source_commit_sha=source_commit_sha,
        build_pipeline_id=build_pipeline_id,
        trusted_key_id=trusted_key_id,
    )
    if not bool(issued.get("ok")):
        return {}
    envelope = issued.get("envelope")
    return dict(envelope) if isinstance(envelope, dict) else {}


def _verify_installer_provenance(
    installer_path: str,
    *,
    runtime: dict[str, Any],
    app_id: str | None = None,
    provenance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return verify_provenance_envelope(
        subject_type="installer",
        artifact_path=installer_path,
        envelope=provenance,
        family=str(runtime.get("family", "") or ""),
        profile=str(runtime.get("profile", "") or ""),
        metadata=_installer_provenance_metadata(app_id),
    )


def _write_installer_replay(record: dict[str, Any]) -> None:
    INSTALLER_REPLAY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with INSTALLER_REPLAY_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def execute_installer_request(
    installer_path: str,
    corr: str,
    family: str = None,
    profile: str = None,
    app_id: str = None,
    allow_live_installer: bool = False,
    timeout_sec: int = 120,
    traffic_sample: list[dict[str, Any]] | None = None,
    expected_flow_profile: str | None = None,
    provenance: dict[str, Any] | None = None,
    ingress_adapter: str | None = None,
) -> dict[str, Any]:
    runtime = resolve_installer_runtime(installer_path, family=family, profile=profile)
    if not runtime.get("ok"):
        return {
            "ok": False,
            "code": runtime.get("code"),
            "installer_runtime": runtime,
            "installer_execution": None,
            "installer_replay": None,
            "installer_projection": None,
            "installer_projection_session": None,
            "installer_projection_session_close": None,
            "installer_provenance_check": None,
            "firewall_guard_session": None,
            "firewall_guard_inspection": None,
            "firewall_packet_source": None,
        }

    provenance_check = _verify_installer_provenance(
        installer_path,
        runtime=runtime,
        app_id=app_id,
        provenance=provenance,
    )
    if not bool(provenance_check.get("ok")):
        return {
            "ok": False,
            "code": "INSTALLER_PROVENANCE_REJECTED",
            "installer_runtime": runtime,
            "installer_execution": None,
            "installer_replay": None,
            "installer_projection": None,
            "installer_projection_session": None,
            "installer_projection_session_close": None,
            "installer_provenance_check": provenance_check,
            "firewall_guard_session": None,
            "firewall_guard_inspection": None,
            "firewall_packet_source": None,
        }

    adapter = build_adapter(
        str(runtime.get("family", "")),
        str(runtime.get("profile", "")),
        str(runtime.get("execution_model", "")),
        bool(runtime.get("sandbox_enforced", False)),
    )
    if adapter is None:
        return {
            "ok": False,
            "code": "INSTALLER_ADAPTER_UNAVAILABLE",
            "installer_runtime": runtime,
            "installer_execution": None,
            "installer_replay": None,
            "installer_projection": None,
            "installer_projection_session": None,
            "installer_projection_session_close": None,
            "installer_provenance_check": provenance_check,
            "firewall_guard_session": None,
            "firewall_guard_inspection": None,
            "firewall_packet_source": None,
        }

    proj_app_id = projection_app_id(app_id=app_id, installer_path=installer_path)
    projection = ensure_projection(
        app_id=proj_app_id,
        family=str(runtime.get("family", "")),
        profile=str(runtime.get("profile", "")),
        execution_model=str(runtime.get("execution_model", "")),
        source="installer_execution",
        installer_path=installer_path,
    )
    install_context = None
    if callable(prepare_installer_runtime_context):
        install_context = prepare_installer_runtime_context(
            app_id=proj_app_id,
            family=str(runtime.get("family", "")),
            profile=str(runtime.get("profile", "")),
            execution_model=str(runtime.get("execution_model", "")),
            installer_path=installer_path,
            projection=projection if isinstance(projection, dict) else None,
            corr=corr,
        )

    plan = adapter.plan(installer_path, install_context=install_context if isinstance(install_context, dict) else None)
    if not plan.get("ok"):
        return {
            "ok": False,
            "code": plan.get("code"),
            "installer_runtime": runtime,
            "installer_execution": {"ok": False, "code": plan.get("code"), "plan": plan},
            "installer_replay": None,
            "installer_projection": projection if isinstance(projection, dict) else None,
            "installer_projection_session": None,
            "installer_projection_session_close": None,
            "installer_provenance_check": provenance_check,
            "firewall_guard_session": None,
            "firewall_guard_inspection": None,
            "firewall_packet_source": None,
            "installer_runtime_context": install_context if isinstance(install_context, dict) else None,
        }

    execution = adapter.execute(plan, live_execution=bool(allow_live_installer), timeout_sec=timeout_sec)
    replay = {
        "corr": corr,
        "ts": now_iso(),
        "family": plan.get("family"),
        "profile": plan.get("profile"),
        "installer_path": installer_path,
        "installer_artifact": plan.get("installer_artifact"),
        "installer_extension": plan.get("installer_extension"),
        "execution_model": plan.get("execution_model"),
        "adapter_id": plan.get("adapter_id"),
        "signature": build_replay_signature(plan),
        "provenance_subject_hash": provenance_check.get("subject_hash"),
        "provenance_key_id": provenance_check.get("trusted_key_id"),
        "provenance_pipeline_id": provenance_check.get("build_pipeline_id"),
        "execution_code": execution.get("code"),
        "execution_ok": bool(execution.get("ok")),
        "live_execution": bool(allow_live_installer),
    }
    _write_installer_replay(replay)
    projection_session = None
    if bool(execution.get("ok")) and projection is not None:
        s = start_or_reconnect_session(proj_app_id, projection, corr=corr)
        projection_session = s.get("session") if bool(s.get("ok")) else None
    projection_session_close = None
    installer_runtime_image = None
    if bool(execution.get("ok")) and isinstance(projection, dict) and callable(register_installer_runtime_image):
        image_receipt = register_installer_runtime_image(
            app_id=proj_app_id,
            family=str(runtime.get("family", "")),
            profile=str(runtime.get("profile", "")),
            execution_model=str(runtime.get("execution_model", "")),
            installer_path=installer_path,
            projection=projection,
            provenance_check=provenance_check if isinstance(provenance_check, dict) else None,
            replay_signature=str(replay.get("signature") or ""),
            corr=corr,
        )
        installer_runtime_image = image_receipt.get("image") if isinstance(image_receipt, dict) else None

    guard_app_id = "external_installer"
    guard = start_guard_session(
        app_id=guard_app_id,
        corr=corr,
        internet_hint=True,
    )
    firewall_session = guard.get("session")
    firewall_inspection = None
    network_share = _share_network_sandbox_for_runtime(
        app_id=guard_app_id,
        corr=corr,
        guard_session=firewall_session if isinstance(firewall_session, dict) else None,
        projection_session=projection_session if isinstance(projection_session, dict) else None,
        ingress_adapter=ingress_adapter,
    )
    capture_ctx = _firewall_capture_context(
        app_id=guard_app_id,
        guard_session=firewall_session if isinstance(firewall_session, dict) else None,
        projection_session=projection_session if isinstance(projection_session, dict) else None,
        network_hub_session_id=network_share.get("hub_session_id"),
        network_sandbox_id=network_share.get("sandbox_id"),
        ingress_adapter=network_share.get("ingress_adapter"),
        process_pid=execution.get("pid"),
        process_name=execution.get("process_name"),
        execution_live=bool(execution.get("live_execution", False)),
        family=str(runtime.get("family", "")),
        profile=str(runtime.get("profile", "")),
        execution_model=str(runtime.get("execution_model", "")),
        capture_provider_id=str(plan.get("capture_provider_id", "")),
    )
    packet_source = _resolve_firewall_packets(
        traffic_sample=traffic_sample,
        expected_flow_profile=expected_flow_profile or "installer_update",
        capture_context=capture_ctx,
    )
    packets = _decorate_installer_packets_for_transfer_policy(
        _normalize_traffic_sample(packet_source.get("packets")),
        installer_path=installer_path,
        expected_flow_profile=expected_flow_profile or "installer_update",
    )
    firewall_inspection = inspect_packets(
        app_id=guard_app_id,
        packets=packets,
        corr=corr,
        session_id=(firewall_session or {}).get("session_id") if isinstance(firewall_session, dict) else None,
        expected_flow_profile=expected_flow_profile or "installer_update",
        internet_hint=True,
        correlation=_firewall_correlation_requirements(
            guard_session=firewall_session if isinstance(firewall_session, dict) else None,
            packet_source=packet_source,
            capture_context=capture_ctx,
        ),
    )
    projection_session_close = _close_projection_session(
        projection_session if isinstance(projection_session, dict) else None,
        corr=corr,
        reason="installer_execution_complete",
    )
    return {
        "ok": bool(execution.get("ok")),
        "code": execution.get("code"),
        "installer_runtime": runtime,
        "installer_runtime_context": install_context if isinstance(install_context, dict) else None,
        "installer_execution": execution,
        "installer_replay": replay,
        "installer_projection": projection,
        "installer_projection_session": projection_session,
        "installer_projection_session_close": projection_session_close,
        "installer_provenance_check": provenance_check,
        "firewall_guard_session": firewall_session,
        "firewall_guard_inspection": firewall_inspection,
        "firewall_packet_source": packet_source,
        "network_sandbox_share": network_share.get("share_receipt"),
        "installer_runtime_image": installer_runtime_image,
    }


def warm_shell_cache(app_id: str, family: str = None, profile: str = None, projection: dict[str, Any] = None):
    cache = load_json(CACHE_PATH)
    compat = resolve_compatibility(app_id, family=family, profile=profile)
    shell_entry = {
        'app_id': app_id,
        'family': compat['family'],
        'profile': compat['profile'],
        'execution_model': compat['execution_model'],
        'prepared_utc': now_iso(),
        'reuse_ready': True
    }
    if projection:
        shell_entry['projection_id'] = projection.get('projection_id')
        shell_entry['projection_root'] = projection.get('projection_root')
        shell_entry['projection_profile'] = projection.get('profile')
        shell_entry['projection_family'] = projection.get('family')
    cache.setdefault('shells', {})[app_id] = shell_entry
    save_json(CACHE_PATH, cache)
    return shell_entry


def shell_cache_entry(app_id: str):
    cache = load_json(CACHE_PATH)
    return cache.get('shells', {}).get(app_id)


def audit(evt: dict):
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    evt['ts'] = evt.get('ts', now_iso())
    with AUDIT_PATH.open('a', encoding='utf-8') as f:
        f.write(json.dumps(evt) + '\n')


def _internet_hint_for_app(app_id: str, compat: dict[str, Any]) -> bool:
    if str(app_id) == "external_installer":
        return True
    return str((compat or {}).get("family", "")).lower() in ("windows", "linux")


def _normalize_ingress_adapter(value: str | None) -> str:
    text = str(value or "").strip().lower()
    if text in {"wired", "wifi", "bluetooth", "vpn", "rdp_admin", "rdp_user"}:
        return text
    return "wired"


def _share_network_sandbox_for_runtime(
    *,
    app_id: str,
    corr: str,
    guard_session: dict[str, Any] | None,
    projection_session: dict[str, Any] | None,
    ingress_adapter: str | None = None,
) -> dict[str, Any]:
    fallback_sandbox = str(
        ((guard_session or {}).get("network_sandbox_id") if isinstance(guard_session, dict) else "")
        or f"app:{app_id}"
    ).strip()
    sandbox_id = fallback_sandbox or f"app:{app_id}"
    hub_session_id = str(
        ((guard_session or {}).get("network_hub_session_id") if isinstance(guard_session, dict) else "")
        or ""
    ).strip()
    if isinstance(projection_session, dict):
        projection_sid = str(projection_session.get("session_id", "") or "").strip()
        if projection_sid:
            sandbox_id = f"projection:{projection_sid}"
    adapter = _normalize_ingress_adapter(ingress_adapter)
    share_receipt = None
    if callable(network_share_internet_to_sandbox):
        allow_upload = None
        allow_download = None
        if isinstance(guard_session, dict):
            if "allow_upload" in guard_session:
                allow_upload = bool(guard_session.get("allow_upload"))
            if "allow_download" in guard_session:
                allow_download = bool(guard_session.get("allow_download"))
        share_receipt = network_share_internet_to_sandbox(
            app_id=str(app_id),
            sandbox_id=str(sandbox_id),
            corr=corr,
            allowed_adapters=[adapter],
            allow_upload=allow_upload,
            allow_download=allow_download,
        )
        if isinstance(share_receipt, dict) and bool(share_receipt.get("ok", False)):
            share = dict(share_receipt.get("share") or {})
            sandbox_id = str(share.get("sandbox_id") or sandbox_id)
            hub_session_id = str(share.get("hub_session_id") or hub_session_id)
    return {
        "hub_session_id": hub_session_id or None,
        "sandbox_id": sandbox_id,
        "ingress_adapter": adapter,
        "share_receipt": share_receipt,
    }


def _normalize_traffic_sample(raw: Any) -> list[dict[str, Any]]:
    if raw is None:
        return []
    if isinstance(raw, list):
        out = []
        for item in raw:
            if isinstance(item, dict):
                out.append(dict(item))
        return out
    return []


def _resolve_firewall_packets(
    traffic_sample: Any,
    expected_flow_profile: str | None = None,
    capture_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    out = resolve_packet_sample(
        explicit_packets=traffic_sample,
        expected_flow_profile=expected_flow_profile,
        capture_context=capture_context,
    )
    packets = out.get("packets")
    if not isinstance(packets, list):
        out["packets"] = []
    return out


def _decorate_installer_packets_for_transfer_policy(
    packets: list[dict[str, Any]],
    *,
    installer_path: str,
    expected_flow_profile: str,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for item in packets:
        if not isinstance(item, dict):
            continue
        pkt = dict(item)
        pkt.setdefault("flow_profile", expected_flow_profile)
        pkt.setdefault("transfer_type", "download")
        pkt.setdefault("origin", "web")
        pkt.setdefault("save_path", str(installer_path))
        out.append(pkt)

    if out:
        return out

    # Ensure save-target policy is still evaluated when packet stream is empty.
    return [
        {
            "direction": "egress",
            "protocol": "https",
            "remote_host": "repo.axion.local",
            "remote_port": 443,
            "flow_profile": expected_flow_profile,
            "transfer_type": "download",
            "origin": "web",
            "save_path": str(installer_path),
        }
    ]


def _norm_proc_name(value: str | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip().lower()
    if not text:
        return None
    return Path(text).name.lower()


def _firewall_capture_context(
    *,
    app_id: str,
    guard_session: dict[str, Any] | None,
    projection_session: dict[str, Any] | None,
    network_hub_session_id: str | None = None,
    network_sandbox_id: str | None = None,
    ingress_adapter: str | None = None,
    process_pid: int | None = None,
    process_name: str | None = None,
    execution_live: bool | None = None,
    family: str | None = None,
    profile: str | None = None,
    execution_model: str | None = None,
    capture_provider_id: str | None = None,
) -> dict[str, Any]:
    guard_sid = None
    if isinstance(guard_session, dict):
        guard_sid = str(guard_session.get("session_id", "")).strip() or None
    proj_sid = None
    if isinstance(projection_session, dict):
        proj_sid = str(projection_session.get("session_id", "")).strip() or None
    out: dict[str, Any] = {
        "source": "process_bound_live",
        "app_id": str(app_id),
        "guard_session_id": guard_sid,
        "capture_session_id": proj_sid,
        "runtime_family": str(family or "").strip().lower() or None,
        "runtime_profile": str(profile or "").strip().lower() or None,
        "runtime_execution_model": str(execution_model or "").strip().lower() or None,
    }
    provider = str(capture_provider_id or "").strip()
    if provider:
        out["capture_provider_id"] = provider
    net_hub_sid = str(network_hub_session_id or "").strip()
    if net_hub_sid:
        out["network_hub_session_id"] = net_hub_sid
    net_sandbox_id = str(network_sandbox_id or "").strip()
    if net_sandbox_id:
        out["network_sandbox_id"] = net_sandbox_id
    net_adapter = _normalize_ingress_adapter(ingress_adapter)
    if net_adapter:
        out["ingress_adapter"] = net_adapter
    if process_pid is not None:
        out["process_pid"] = int(process_pid)
        name = _norm_proc_name(process_name)
        if name:
            out["process_name"] = name
    if execution_live is not None:
        out["execution_live"] = bool(execution_live)
    return out


def _firewall_correlation_requirements(
    *,
    guard_session: dict[str, Any] | None,
    packet_source: dict[str, Any] | None,
    capture_context: dict[str, Any] | None,
) -> dict[str, Any]:
    pid = None
    names: list[str] = []
    capture_sid = ""
    execution_live = False
    if isinstance(capture_context, dict):
        raw_pid = capture_context.get("process_pid")
        if raw_pid is not None:
            try:
                pid = int(raw_pid)
            except Exception:
                pid = None
        raw_name = capture_context.get("process_name")
        nm = _norm_proc_name(raw_name if raw_name is not None else "")
        if nm:
            names.append(nm)
        raw_capture_sid = capture_context.get("capture_session_id")
        capture_sid = str(raw_capture_sid).strip() if raw_capture_sid is not None else ""
        execution_live = bool(capture_context.get("execution_live", False))

    source = str(((packet_source or {}).get("source")) or "").strip().lower()
    correlated = bool((packet_source or {}).get("correlated", False)) or source == "process_bound_live"
    guard_corr_enabled = True
    guard_require_pid = True
    guard_require_process_name = True
    guard_require_session = False
    guard_require_live_identity = True
    if isinstance(guard_session, dict):
        guard_corr_enabled = bool(guard_session.get("process_correlation_enabled", True))
        guard_require_pid = bool(guard_session.get("process_correlation_require_pid_match", True))
        guard_require_process_name = bool(guard_session.get("process_correlation_require_process_name_match", True))
        guard_require_session = bool(guard_session.get("process_correlation_require_session_tags", False))
        guard_require_live_identity = bool(guard_session.get("process_correlation_require_live_process_identity", True))
    requires_live_identity = guard_corr_enabled and correlated and guard_require_live_identity and execution_live
    require_pid_match = guard_corr_enabled and correlated and guard_require_pid and (pid is not None or requires_live_identity)
    require_process_name_match = guard_corr_enabled and correlated and guard_require_process_name and (bool(names) or requires_live_identity)
    # Session tags are only enforceable when we can correlate to process identity.
    require_session_tags = (
        guard_corr_enabled
        and correlated
        and guard_require_session
        and bool(capture_sid)
        and (pid is not None or bool(names) or requires_live_identity)
    )
    return {
        "expected_pid": pid,
        "expected_process_names": sorted(set(names)),
        "capture_session_id": capture_sid or None,
        "require_pid_match": require_pid_match,
        "require_process_name_match": require_process_name_match,
        "require_session_tags": require_session_tags,
        "require_expected_identity": requires_live_identity,
        "source": source or None,
        "correlated_stream": correlated,
        "execution_live": execution_live,
    }


def _close_projection_session(
    projection_session: dict[str, Any] | None,
    *,
    corr: str,
    reason: str,
) -> dict[str, Any] | None:
    if not isinstance(projection_session, dict):
        return None
    sid = str(projection_session.get("session_id") or "").strip()
    if not sid:
        return None
    try:
        return close_session(sid, reason=reason)
    except Exception as ex:
        return {
            "ok": False,
            "code": "PROJECTION_SESSION_CLOSE_EXCEPTION",
            "session_id": sid,
            "reason": reason,
            "error": str(ex),
            "corr": corr,
        }


def launch(
    app_id: str,
    corr: str,
    family: str = None,
    profile: str = None,
    installer: str = None,
    execute_installer: bool = False,
    allow_live_installer: bool = False,
    installer_timeout_sec: int = 120,
    installer_app_id: str = None,
    installer_provenance: dict[str, Any] | None = None,
    expected_flow_profile: str = None,
    traffic_sample: list[dict[str, Any]] | None = None,
    ingress_adapter: str | None = None,
):
    pinned_projection = get_projection(app_id)
    effective_family = family
    effective_profile = profile
    if pinned_projection and family is None and profile is None:
        effective_family = str(pinned_projection.get("family", "native_axion"))
        effective_profile = str(pinned_projection.get("profile", "axion_default"))

    mode = resolve_mode(app_id)
    compat = resolve_compatibility(app_id, family=effective_family, profile=effective_profile)
    runtime_image = find_runtime_image(app_id) if callable(find_runtime_image) else None
    smart_driver_fabric = None
    if callable(ensure_smart_driver_fabric_initialized):
        try:
            smart_driver_fabric = ensure_smart_driver_fabric_initialized(corr=corr)
        except Exception as ex:
            smart_driver_fabric = {
                "ok": False,
                "code": "SMART_DRIVER_FABRIC_EXCEPTION",
                "corr": corr,
                "error": str(ex),
                "fail_closed": False,
            }
        if isinstance(smart_driver_fabric, dict):
            if bool(smart_driver_fabric.get("ok")):
                audit(
                    {
                        "corr": corr,
                        "event": "app.launch.smart_driver_fabric_ready",
                        "fabric_code": smart_driver_fabric.get("code"),
                        "load_once_token": smart_driver_fabric.get("load_once_token"),
                    }
                )
            else:
                audit(
                    {
                        "corr": corr,
                        "event": "app.launch.smart_driver_fabric_error",
                        "fabric_code": smart_driver_fabric.get("code"),
                        "error": smart_driver_fabric.get("error"),
                        "fail_closed": bool(smart_driver_fabric.get("fail_closed", False)),
                    }
                )
                if bool(smart_driver_fabric.get("fail_closed", False)):
                    out = {
                        'ok': False,
                        'code': 'LAUNCH_SMART_DRIVER_FABRIC_BLOCKED',
                        'app': app_id,
                        'mode': mode,
                        'compatibility': compat,
                        'smart_driver_fabric': smart_driver_fabric,
                    }
                    audit({'corr': corr, 'event': 'app.launch.smart_driver_fabric_block', **out})
                    return out
    system_policy = system_program_entry(app_id)
    if system_policy:
        required_family = str(system_policy.get("family", "")).strip()
        required_profile = str(system_policy.get("profile", "")).strip()
        required_model = str(system_policy.get("execution_model", "")).strip()
        required_internet = bool(system_policy.get("internet_required", False))
        if required_family and str(compat.get("family", "")) != required_family:
            out = {
                'ok': False,
                'code': 'LAUNCH_SYSTEM_POLICY_FAMILY_MISMATCH',
                'app': app_id,
                'mode': mode,
                'compatibility': compat,
                'required_family': required_family,
                'required_profile': required_profile or None,
                'required_execution_model': required_model or None,
                'system_policy': system_policy,
            }
            audit({'corr': corr, 'event': 'app.launch.system_policy_reject', **out})
            return out
        if required_profile and str(compat.get("profile", "")) != required_profile:
            out = {
                'ok': False,
                'code': 'LAUNCH_SYSTEM_POLICY_PROFILE_MISMATCH',
                'app': app_id,
                'mode': mode,
                'compatibility': compat,
                'required_family': required_family or None,
                'required_profile': required_profile,
                'required_execution_model': required_model or None,
                'system_policy': system_policy,
            }
            audit({'corr': corr, 'event': 'app.launch.system_policy_reject', **out})
            return out
        if required_model and str(compat.get("execution_model", "")) != required_model:
            out = {
                'ok': False,
                'code': 'LAUNCH_SYSTEM_POLICY_MODEL_MISMATCH',
                'app': app_id,
                'mode': mode,
                'compatibility': compat,
                'required_family': required_family or None,
                'required_profile': required_profile or None,
                'required_execution_model': required_model,
                'system_policy': system_policy,
            }
            audit({'corr': corr, 'event': 'app.launch.system_policy_reject', **out})
            return out
    qm_ecc_decision = None
    if callable(qm_ecc_evaluate_runtime_launch):
        qm_ecc_decision = qm_ecc_evaluate_runtime_launch(app_id, corr=corr, compatibility=compat)
        if isinstance(qm_ecc_decision, dict) and not bool(qm_ecc_decision.get('ok', True)):
            out = {
                'ok': False,
                'code': 'LAUNCH_QM_ECC_BLOCKED',
                'app': app_id,
                'mode': mode,
                'compatibility': compat,
                'system_policy': system_policy if system_policy else None,
                'qm_ecc_decision': qm_ecc_decision,
            }
            audit({'corr': corr, 'event': 'app.launch.qm_ecc_reject', **out})
            return out
    internet_hint = _internet_hint_for_app(app_id, compat)
    if system_policy and bool(system_policy.get("internet_required", False)) != bool(internet_hint):
        out = {
            'ok': False,
            'code': 'LAUNCH_SYSTEM_POLICY_INTERNET_MISMATCH',
            'app': app_id,
            'mode': mode,
            'compatibility': compat,
            'system_policy': system_policy,
            'internet_hint': bool(internet_hint),
        }
        audit({'corr': corr, 'event': 'app.launch.system_policy_reject', **out})
        return out
    firewall_guard = start_guard_session(app_id=app_id, corr=corr, internet_hint=internet_hint)
    firewall_guard_session = firewall_guard.get("session")
    firewall_guard_inspection = None
    packet_source: dict[str, Any] = {"packets": [], "source": "none", "correlated": False}

    projection_session = None
    network_share = {
        "hub_session_id": str(
            ((firewall_guard_session or {}).get("network_hub_session_id") if isinstance(firewall_guard_session, dict) else "")
            or ""
        ).strip() or None,
        "sandbox_id": str(
            ((firewall_guard_session or {}).get("network_sandbox_id") if isinstance(firewall_guard_session, dict) else "")
            or f"app:{app_id}"
        ),
        "ingress_adapter": _normalize_ingress_adapter(ingress_adapter),
        "share_receipt": None,
    }
    if pinned_projection is not None:
        s = start_or_reconnect_session(app_id, pinned_projection, corr=corr)
        projection_session = s.get("session") if bool(s.get("ok")) else None
        if projection_session and projection_session.get("session_id"):
            heartbeat_session(str(projection_session["session_id"]), corr=corr)
    network_share = _share_network_sandbox_for_runtime(
        app_id=app_id,
        corr=corr,
        guard_session=firewall_guard_session if isinstance(firewall_guard_session, dict) else None,
        projection_session=projection_session if isinstance(projection_session, dict) else None,
        ingress_adapter=ingress_adapter,
    )
    external_policy = load_external_policy()
    sandbox_required = bool(external_policy.get("run_in_sandbox_only", True))
    if sandbox_required and compat.get("family") in ("windows", "linux") and not str(compat.get("execution_model", "")).startswith("sandbox_"):
        out = {
            'ok': False,
            'code': 'LAUNCH_SANDBOX_POLICY_FAIL',
            'app': app_id,
            'mode': mode,
            'compatibility': compat,
            'system_policy': system_policy if system_policy else None,
            'qm_ecc_decision': qm_ecc_decision,
            'shell_cache': None,
            'cache_state': 'policy_rejected',
            'projection': pinned_projection,
            'projection_session': projection_session,
            'firewall_guard_session': firewall_guard_session,
            'firewall_guard_inspection': firewall_guard_inspection,
            'firewall_packet_source': packet_source,
            'network_sandbox_share': network_share.get('share_receipt'),
            'runtime_image': runtime_image,
        }
        audit({'corr': corr, 'event': 'app.launch.policy_reject', **out})
        return out

    cache_entry = shell_cache_entry(app_id)
    if cache_entry is None:
        cache_entry = warm_shell_cache(
            app_id,
            family=compat['family'],
            profile=compat['profile'],
            projection=pinned_projection,
        )
        cache_state = 'prepared_on_first_run'
    else:
        cache_state = 'reused_warm_shell'

    entry = APP_ENTRYPOINTS.get(app_id)
    if not entry:
        if not (installer and execute_installer):
            capture_ctx = _firewall_capture_context(
                app_id=app_id,
                guard_session=firewall_guard_session if isinstance(firewall_guard_session, dict) else None,
                projection_session=projection_session if isinstance(projection_session, dict) else None,
                network_hub_session_id=network_share.get("hub_session_id"),
                network_sandbox_id=network_share.get("sandbox_id"),
                ingress_adapter=network_share.get("ingress_adapter"),
                family=str((compat or {}).get("family", "")),
                profile=str((compat or {}).get("profile", "")),
                execution_model=str((compat or {}).get("execution_model", "")),
            )
            packet_source = _resolve_firewall_packets(
                traffic_sample=traffic_sample,
                expected_flow_profile=expected_flow_profile,
                capture_context=capture_ctx,
            )
            packets = _normalize_traffic_sample(packet_source.get("packets"))
            if packets:
                firewall_guard_inspection = inspect_packets(
                    app_id=app_id,
                    packets=packets,
                    corr=corr,
                    session_id=(firewall_guard_session or {}).get("session_id") if isinstance(firewall_guard_session, dict) else None,
                    expected_flow_profile=expected_flow_profile,
                    internet_hint=internet_hint,
                    correlation=_firewall_correlation_requirements(
                        guard_session=firewall_guard_session if isinstance(firewall_guard_session, dict) else None,
                        packet_source=packet_source,
                        capture_context=capture_ctx,
                    ),
                )
        installer_runtime = None
        installer_execution = None
        installer_replay = None
        installer_projection = None
        installer_projection_session = None
        installer_projection_session_close = None
        installer_provenance_check = None
        installer_runtime_image = None
        if installer:
            installer_runtime = resolve_installer_runtime(installer, family=effective_family, profile=effective_profile)
            if not installer_runtime.get("ok"):
                out = {
                    'ok': False,
                    'code': installer_runtime.get("code"),
                    'app': app_id,
                    'mode': mode,
                    'compatibility': compat,
                    'system_policy': system_policy if system_policy else None,
                    'qm_ecc_decision': qm_ecc_decision,
                    'shell_cache': cache_entry,
                    'cache_state': cache_state,
                    'installer_runtime': installer_runtime,
                    'installer_provenance_check': installer_provenance_check,
                    'runtime_image': runtime_image,
                }
                audit({'corr': corr, 'event': 'app.launch.installer_reject', **{k: v for k, v in out.items() if k != 'shell_cache'}})
                return out
            if execute_installer:
                exec_out = execute_installer_request(
                    installer_path=installer,
                    corr=corr,
                    family=effective_family,
                    profile=effective_profile,
                    app_id=installer_app_id,
                    allow_live_installer=allow_live_installer,
                    timeout_sec=installer_timeout_sec,
                    traffic_sample=traffic_sample,
                    expected_flow_profile=expected_flow_profile,
                    provenance=installer_provenance,
                    ingress_adapter=ingress_adapter,
                )
                installer_execution = exec_out.get("installer_execution")
                installer_replay = exec_out.get("installer_replay")
                installer_projection = exec_out.get("installer_projection")
                installer_projection_session = exec_out.get("installer_projection_session")
                installer_projection_session_close = exec_out.get("installer_projection_session_close")
                installer_provenance_check = exec_out.get("installer_provenance_check")
                installer_runtime_image = exec_out.get("installer_runtime_image")
                runtime_image = installer_runtime_image if isinstance(installer_runtime_image, dict) else runtime_image
                out = {
                    'ok': bool(exec_out.get("ok")) and (not bool((exec_out.get("firewall_guard_inspection") or {}).get("quarantined", 0))),
                    'code': 'LAUNCH_INSTALLER_EXECUTED' if bool(exec_out.get("ok")) else str(exec_out.get("code")),
                    'app': app_id,
                    'mode': mode,
                    'compatibility': compat,
                    'system_policy': system_policy if system_policy else None,
                    'qm_ecc_decision': qm_ecc_decision,
                    'shell_cache': cache_entry,
                    'cache_state': cache_state,
                    'installer_runtime': exec_out.get("installer_runtime"),
                    'installer_execution': installer_execution,
                    'installer_replay': installer_replay,
                    'installer_projection': installer_projection,
                    'installer_projection_session': installer_projection_session,
                    'installer_projection_session_close': installer_projection_session_close,
                    'installer_provenance_check': installer_provenance_check,
                    'installer_runtime_image': installer_runtime_image,
                    'installer_runtime_context': exec_out.get("installer_runtime_context"),
                    'projection': pinned_projection,
                    'projection_session': projection_session,
                    'firewall_guard_session': exec_out.get("firewall_guard_session", firewall_guard_session),
                    'firewall_guard_inspection': exec_out.get("firewall_guard_inspection", firewall_guard_inspection),
                    'firewall_packet_source': exec_out.get("firewall_packet_source", packet_source),
                    'network_sandbox_share': exec_out.get("network_sandbox_share"),
                    'runtime_image': runtime_image,
                }
                if bool((out.get('firewall_guard_inspection') or {}).get('quarantined', 0)):
                    out['code'] = 'LAUNCH_FIREWALL_QUARANTINED'
                audit({
                    'corr': corr,
                    'event': 'app.launch.installer_executed',
                    **{k: v for k, v in out.items() if k not in ('shell_cache',)},
                })
                return out
            installer_provenance_check = _verify_installer_provenance(
                installer,
                runtime=installer_runtime,
                app_id=installer_app_id,
                provenance=installer_provenance,
            )
            if not bool(installer_provenance_check.get("ok")):
                out = {
                    'ok': False,
                    'code': 'INSTALLER_PROVENANCE_REJECTED',
                    'app': app_id,
                    'mode': mode,
                    'compatibility': compat,
                    'system_policy': system_policy if system_policy else None,
                    'qm_ecc_decision': qm_ecc_decision,
                    'shell_cache': cache_entry,
                    'cache_state': cache_state,
                    'installer_runtime': installer_runtime,
                    'installer_provenance_check': installer_provenance_check,
                    'network_sandbox_share': network_share.get('share_receipt'),
                    'runtime_image': runtime_image,
                }
                audit({'corr': corr, 'event': 'app.launch.installer_provenance_reject', **{k: v for k, v in out.items() if k != 'shell_cache'}})
                return out
        out = {
            'ok': True,
            'code': 'LAUNCH_ENVIRONMENT_PREPARED',
            'app': app_id,
            'mode': mode,
            'compatibility': compat,
            'system_policy': system_policy if system_policy else None,
            'qm_ecc_decision': qm_ecc_decision,
            'shell_cache': cache_entry,
            'cache_state': cache_state,
            'installer_runtime': installer_runtime,
            'installer_execution': installer_execution,
            'installer_replay': installer_replay,
            'installer_projection': installer_projection,
            'installer_projection_session': installer_projection_session,
            'installer_projection_session_close': installer_projection_session_close,
            'installer_provenance_check': installer_provenance_check,
            'installer_runtime_image': installer_runtime_image,
            'runtime_image': runtime_image,
            'projection': pinned_projection,
            'projection_session': projection_session,
            'firewall_guard_session': firewall_guard_session,
            'firewall_guard_inspection': firewall_guard_inspection,
            'firewall_packet_source': packet_source,
            'network_sandbox_share': network_share.get('share_receipt'),
        }
        audit({'corr': corr, 'event': 'app.launch.prepare_only', **{k: v for k, v in out.items() if k != 'shell_cache'}})
        return out

    cmd = ['python', entry]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = proc.communicate()
    capture_ctx = _firewall_capture_context(
        app_id=app_id,
        guard_session=firewall_guard_session if isinstance(firewall_guard_session, dict) else None,
        projection_session=projection_session if isinstance(projection_session, dict) else None,
        network_hub_session_id=network_share.get("hub_session_id"),
        network_sandbox_id=network_share.get("sandbox_id"),
        ingress_adapter=network_share.get("ingress_adapter"),
        process_pid=int(proc.pid),
        process_name=cmd[0],
        execution_live=True,
        family=str((compat or {}).get("family", "")),
        profile=str((compat or {}).get("profile", "")),
        execution_model=str((compat or {}).get("execution_model", "")),
    )
    packet_source = _resolve_firewall_packets(
        traffic_sample=traffic_sample,
        expected_flow_profile=expected_flow_profile,
        capture_context=capture_ctx,
    )
    packets = _normalize_traffic_sample(packet_source.get("packets"))
    firewall_guard_inspection = inspect_packets(
        app_id=app_id,
        packets=packets,
        corr=corr,
        session_id=(firewall_guard_session or {}).get("session_id") if isinstance(firewall_guard_session, dict) else None,
        expected_flow_profile=expected_flow_profile,
        internet_hint=internet_hint,
        correlation=_firewall_correlation_requirements(
            guard_session=firewall_guard_session if isinstance(firewall_guard_session, dict) else None,
            packet_source=packet_source,
            capture_context=capture_ctx,
        ),
    )
    projection_session_close = _close_projection_session(
        projection_session if isinstance(projection_session, dict) else None,
        corr=corr,
        reason="runtime_process_exit",
    )
    out = {
        'ok': (proc.returncode == 0) and (not bool((firewall_guard_inspection or {}).get("quarantined", 0))),
        'code': 'LAUNCH_OK' if proc.returncode == 0 else 'LAUNCH_FAIL',
        'app': app_id,
        'mode': mode,
        'compatibility': compat,
        'system_policy': system_policy if system_policy else None,
        'qm_ecc_decision': qm_ecc_decision,
        'shell_cache': cache_entry,
        'cache_state': cache_state,
        'projection': pinned_projection,
        'projection_session': projection_session,
        'projection_session_close': projection_session_close,
        'firewall_guard_session': firewall_guard_session,
        'firewall_guard_inspection': firewall_guard_inspection,
        'firewall_packet_source': packet_source,
        'network_sandbox_share': network_share.get('share_receipt'),
        'runtime_image': runtime_image,
        'exit': proc.returncode,
        'process_pid': int(proc.pid),
        'stdout': (stdout or '').strip()[:2000],
        'stderr': (stderr or '').strip()[:1200]
    }
    if bool((firewall_guard_inspection or {}).get("quarantined", 0)):
        out['code'] = 'LAUNCH_FIREWALL_QUARANTINED'
    audit({'corr': corr, 'event': 'app.launch', **{k: v for k, v in out.items() if k not in ('stdout', 'stderr', 'shell_cache')}})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--app', required=True)
    ap.add_argument('--corr', default='corr_launch_001')
    ap.add_argument('--family', default=None)
    ap.add_argument('--profile', default=None)
    ap.add_argument('--installer', default=None)
    ap.add_argument('--installer-app-id', default=None)
    ap.add_argument('--execute-installer', action='store_true')
    ap.add_argument('--allow-live-installer', action='store_true')
    ap.add_argument('--installer-timeout-sec', type=int, default=120)
    ap.add_argument('--expected-flow-profile', default=None)
    ap.add_argument('--ingress-adapter', default=None)
    ap.add_argument('--traffic-sample-json', default=None)
    ap.add_argument('--traffic-source-json', default=None)
    ap.add_argument('--installer-provenance-json', default=None)
    args = ap.parse_args()
    traffic_sample = None
    installer_provenance = None
    if args.traffic_sample_json:
        sample_path = Path(str(args.traffic_sample_json))
        if sample_path.exists():
            try:
                traffic_sample = json.loads(sample_path.read_text(encoding='utf-8-sig'))
            except Exception:
                traffic_sample = None
    if args.traffic_source_json:
        source_path = Path(str(args.traffic_source_json))
        if source_path.exists():
            os.environ["AXION_FIREWALL_PACKET_SOURCE"] = str(source_path)
    if args.installer_provenance_json:
        provenance_path = Path(str(args.installer_provenance_json))
        if provenance_path.exists():
            try:
                installer_provenance = json.loads(provenance_path.read_text(encoding='utf-8-sig'))
            except Exception:
                installer_provenance = None
    print(
        json.dumps(
            launch(
                args.app,
                args.corr,
                family=args.family,
                profile=args.profile,
                installer=args.installer,
                installer_app_id=args.installer_app_id,
                execute_installer=bool(args.execute_installer),
                allow_live_installer=bool(args.allow_live_installer),
                installer_timeout_sec=int(args.installer_timeout_sec),
                installer_provenance=installer_provenance,
                expected_flow_profile=args.expected_flow_profile,
                ingress_adapter=args.ingress_adapter,
                traffic_sample=traffic_sample,
            ),
            indent=2,
        )
    )


if __name__ == '__main__':
    main()
