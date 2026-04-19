from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

AXION_ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = AXION_ROOT / "config" / "FIREWALL_GUARD_POLICY_V1.json"
CAPTURE_ADAPTER_PATH = AXION_ROOT / "config" / "FIREWALL_CAPTURE_ADAPTERS_V1.json"


def _to_int_or_none(value: Any) -> int | None:
    try:
        if value is None:
            return None
        return int(value)
    except Exception:
        return None


def _name_token(value: str | None) -> str | None:
    if not value:
        return None
    text = str(value).strip().lower()
    if not text:
        return None
    return Path(text).name.lower()


def _capture_pids(capture_context: dict[str, Any] | None) -> set[int]:
    if not isinstance(capture_context, dict):
        return set()
    out: set[int] = set()
    direct = _to_int_or_none(capture_context.get("process_pid"))
    if direct is not None and direct > 0:
        out.add(direct)
    for item in (capture_context.get("process_pids") or []):
        pid = _to_int_or_none(item)
        if pid is not None and pid > 0:
            out.add(pid)
    return out


def _capture_process_names(capture_context: dict[str, Any] | None) -> set[str]:
    if not isinstance(capture_context, dict):
        return set()
    out: set[str] = set()
    direct = _name_token(str(capture_context.get("process_name") or ""))
    if direct:
        out.add(direct)
    for item in (capture_context.get("process_names") or []):
        token = _name_token(str(item or ""))
        if token:
            out.add(token)
    return out


def _apply_capture_context(packet: dict[str, Any], capture_context: dict[str, Any] | None) -> dict[str, Any]:
    pkt = dict(packet)
    if not isinstance(capture_context, dict):
        return pkt
    app_id = str(capture_context.get("app_id") or "").strip()
    if app_id and not pkt.get("app_id"):
        pkt["app_id"] = app_id
    guard_sid = str(capture_context.get("guard_session_id") or "").strip()
    if guard_sid and not pkt.get("guard_session_id"):
        pkt["guard_session_id"] = guard_sid
    capture_sid = str(capture_context.get("capture_session_id") or "").strip()
    if capture_sid and not pkt.get("capture_session_id"):
        pkt["capture_session_id"] = capture_sid
    hub_sid = str(capture_context.get("network_hub_session_id") or "").strip()
    if hub_sid and not pkt.get("network_hub_session_id"):
        pkt["network_hub_session_id"] = hub_sid
    sandbox_id = str(capture_context.get("network_sandbox_id") or "").strip()
    if sandbox_id and not pkt.get("network_sandbox_id"):
        pkt["network_sandbox_id"] = sandbox_id
    ingress_adapter = str(capture_context.get("ingress_adapter") or "").strip().lower()
    if ingress_adapter and not pkt.get("ingress_adapter"):
        pkt["ingress_adapter"] = ingress_adapter
    return pkt


def _normalize_packets(
    raw: Any,
    expected_flow_profile: str | None = None,
    capture_context: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        pkt = _apply_capture_context(dict(item), capture_context)
        if expected_flow_profile and not pkt.get("flow_profile"):
            pkt["flow_profile"] = expected_flow_profile
        out.append(pkt)
    return out


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _load_capture_adapter_policy() -> dict[str, Any]:
    if not CAPTURE_ADAPTER_PATH.exists():
        return {"default_provider_id": "windows_tcp_snapshot_provider_v1", "providers": {}, "mappings": {}}
    try:
        obj = _load_json(CAPTURE_ADAPTER_PATH)
    except Exception:
        return {"default_provider_id": "windows_tcp_snapshot_provider_v1", "providers": {}, "mappings": {}}
    if not isinstance(obj, dict):
        return {"default_provider_id": "windows_tcp_snapshot_provider_v1", "providers": {}, "mappings": {}}
    if not isinstance(obj.get("providers"), dict):
        obj["providers"] = {}
    if not isinstance(obj.get("mappings"), dict):
        obj["mappings"] = {}
    obj.setdefault("default_provider_id", "windows_tcp_snapshot_provider_v1")
    return obj


def _capture_family(capture_context: dict[str, Any] | None) -> str:
    if not isinstance(capture_context, dict):
        return ""
    return str(capture_context.get("runtime_family") or "").strip().lower()


def _capture_profile(capture_context: dict[str, Any] | None) -> str:
    if not isinstance(capture_context, dict):
        return ""
    return str(capture_context.get("runtime_profile") or "").strip().lower()


def _capture_exec_model(capture_context: dict[str, Any] | None) -> str:
    if not isinstance(capture_context, dict):
        return ""
    return str(capture_context.get("runtime_execution_model") or "").strip().lower()


def _capture_provider_id(capture_context: dict[str, Any] | None) -> str:
    if not isinstance(capture_context, dict):
        return ""
    return str(capture_context.get("capture_provider_id") or "").strip()


def _resolve_provider(capture_context: dict[str, Any] | None) -> tuple[str, dict[str, Any]]:
    cfg = _load_capture_adapter_policy()
    providers = dict(cfg.get("providers") or {})
    requested = _capture_provider_id(capture_context)
    if requested and isinstance(providers.get(requested), dict):
        return requested, dict(providers.get(requested) or {})

    family = _capture_family(capture_context)
    profile = _capture_profile(capture_context)
    exec_model = _capture_exec_model(capture_context)
    mappings = dict(cfg.get("mappings") or {})
    keys = [
        f"{family}:{profile}:{exec_model}" if family and profile and exec_model else "",
        f"{family}:{exec_model}" if family and exec_model else "",
        f"{family}:{profile}" if family and profile else "",
        family,
    ]
    for key in keys:
        if not key:
            continue
        provider_id = str(mappings.get(key) or "").strip()
        if provider_id and isinstance(providers.get(provider_id), dict):
            return provider_id, dict(providers.get(provider_id) or {})

    fallback = str(cfg.get("default_provider_id") or "").strip()
    if fallback and isinstance(providers.get(fallback), dict):
        return fallback, dict(providers.get(fallback) or {})
    return "", {}


def _read_packet_file(
    path: Path,
    expected_flow_profile: str | None = None,
    capture_context: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    if path.suffix.lower() in (".ndjson", ".jsonl"):
        rows: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            s = line.strip()
            if not s:
                continue
            try:
                obj = json.loads(s)
            except Exception:
                continue
            if isinstance(obj, dict):
                rows.append(obj)
        return _normalize_packets(
            rows,
            expected_flow_profile=expected_flow_profile,
            capture_context=capture_context,
        )

    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return []

    if isinstance(obj, dict) and isinstance(obj.get("packets"), list):
        return _normalize_packets(
            obj["packets"],
            expected_flow_profile=expected_flow_profile,
            capture_context=capture_context,
        )
    return _normalize_packets(
        obj,
        expected_flow_profile=expected_flow_profile,
        capture_context=capture_context,
    )


def _run_powershell_json(command: str) -> Any:
    try:
        p = subprocess.run(["powershell", "-NoProfile", "-Command", command], capture_output=True, text=True)
    except Exception:
        return None
    if p.returncode != 0:
        return None
    raw = (p.stdout or "").strip()
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None


def _collect_windows_tcp_snapshot(
    limit: int,
    expected_flow_profile: str | None = None,
    capture_context: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    cmd = (
        "Get-NetTCPConnection -State Established | "
        f"Select-Object -First {int(limit)} -Property LocalAddress,LocalPort,RemoteAddress,RemotePort,OwningProcess,State | "
        "ConvertTo-Json -Compress"
    )
    obj = _run_powershell_json(cmd)
    if obj is None:
        return []
    if isinstance(obj, dict):
        entries = [obj]
    elif isinstance(obj, list):
        entries = [x for x in obj if isinstance(x, dict)]
    else:
        entries = []

    pid_filter = _capture_pids(capture_context)
    process_name_filter = _capture_process_names(capture_context)
    process_map: dict[int, str] = {}
    if entries:
        ids = sorted({int(x.get("OwningProcess")) for x in entries if _to_int_or_none(x.get("OwningProcess")) is not None})
        if ids:
            id_csv = ",".join(str(i) for i in ids)
            pobj = _run_powershell_json(
                f"Get-Process -Id {id_csv} -ErrorAction SilentlyContinue | "
                "Select-Object -Property Id,ProcessName | ConvertTo-Json -Compress"
            )
            if isinstance(pobj, dict):
                pobj = [pobj]
            if isinstance(pobj, list):
                for row in pobj:
                    if not isinstance(row, dict):
                        continue
                    pid = _to_int_or_none(row.get("Id"))
                    pname = _name_token(str(row.get("ProcessName") or ""))
                    if pid is None or not pname:
                        continue
                    process_map[int(pid)] = pname

    packets: list[dict[str, Any]] = []
    for row in entries:
        pid = _to_int_or_none(row.get("OwningProcess"))
        if pid is None:
            continue
        if pid_filter and pid not in pid_filter:
            continue
        proc_name = process_map.get(pid)
        if process_name_filter and proc_name and proc_name not in process_name_filter:
            continue
        remote_host = str(row.get("RemoteAddress") or "").strip()
        local_host = str(row.get("LocalAddress") or "").strip()
        local_port = _to_int_or_none(row.get("LocalPort")) or 0
        remote_port_raw = row.get("RemotePort")
        try:
            remote_port = int(remote_port_raw) if remote_port_raw is not None else 0
        except Exception:
            remote_port = 0
        packet = {
            "direction": "egress",
            "protocol": "tcp",
            "local_host": local_host,
            "local_port": local_port,
            "remote_host": remote_host,
            "remote_port": remote_port,
            "flow_profile": expected_flow_profile or "runtime_snapshot",
            "packet_source": "process_bound_live",
            "owning_pid": int(pid),
            "process_name": proc_name,
        }
        packets.append(
            _apply_capture_context(packet, capture_context)
        )
    return packets


def _extract_pid_from_ss_process_field(text: str) -> int | None:
    m = re.search(r"pid=(\d+)", str(text or ""))
    if not m:
        return None
    try:
        return int(m.group(1))
    except Exception:
        return None


def _extract_process_name_from_ss_process_field(text: str) -> str | None:
    m = re.search(r"users:\(\(\"([^\"]+)\"", str(text or ""))
    if not m:
        return None
    return _name_token(m.group(1))


def _split_host_port(value: str) -> tuple[str, int]:
    text = str(value or "").strip()
    if not text:
        return ("", 0)
    if text.startswith("[") and "]:" in text:
        idx = text.rfind("]:")
        host = text[1:idx]
        port_raw = text[idx + 2:]
    else:
        idx = text.rfind(":")
        if idx < 0:
            return (text, 0)
        host = text[:idx]
        port_raw = text[idx + 1 :]
    try:
        port = int(port_raw)
    except Exception:
        port = 0
    return (host, port)


def _collect_linux_ss_snapshot(
    limit: int,
    expected_flow_profile: str | None = None,
    capture_context: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    try:
        p = subprocess.run(["ss", "-tnp"], capture_output=True, text=True)
    except Exception:
        return []
    if p.returncode != 0:
        return []
    lines = (p.stdout or "").splitlines()
    pid_filter = _capture_pids(capture_context)
    name_filter = _capture_process_names(capture_context)
    out: list[dict[str, Any]] = []
    for line in lines:
        row = str(line or "").strip()
        if not row or row.lower().startswith("state") or row.lower().startswith("recv-q"):
            continue
        parts = row.split()
        if len(parts) < 5:
            continue
        state = parts[0].strip().lower()
        if state not in ("estab", "established"):
            continue
        local_raw = parts[3]
        remote_raw = parts[4]
        proc_field = " ".join(parts[5:]) if len(parts) > 5 else ""
        pid = _extract_pid_from_ss_process_field(proc_field)
        proc_name = _extract_process_name_from_ss_process_field(proc_field)
        if pid_filter and (pid is None or pid not in pid_filter):
            continue
        if name_filter and (proc_name is None or proc_name not in name_filter):
            continue
        local_host, local_port = _split_host_port(local_raw)
        remote_host, remote_port = _split_host_port(remote_raw)
        packet = {
            "direction": "egress",
            "protocol": "tcp",
            "local_host": local_host,
            "local_port": local_port,
            "remote_host": remote_host,
            "remote_port": remote_port,
            "flow_profile": expected_flow_profile or "runtime_snapshot",
            "packet_source": "process_bound_live",
            "owning_pid": pid,
            "process_name": proc_name,
        }
        out.append(_apply_capture_context(packet, capture_context))
        if len(out) >= int(limit):
            break
    return out


def resolve_packet_sample(
    *,
    explicit_packets: Any = None,
    expected_flow_profile: str | None = None,
    capture_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    packets = _normalize_packets(
        explicit_packets,
        expected_flow_profile=expected_flow_profile,
        capture_context=capture_context,
    )
    if packets:
        return {"packets": packets, "source": "explicit", "correlated": False}

    source_file = os.environ.get("AXION_FIREWALL_PACKET_SOURCE", "").strip()
    if source_file:
        from_file = _read_packet_file(
            Path(source_file),
            expected_flow_profile=expected_flow_profile,
            capture_context=capture_context,
        )
        if from_file:
            return {
                "packets": from_file,
                "source": "env_file",
                "source_path": source_file,
                "correlated": False,
            }

    if not POLICY_PATH.exists():
        return {"packets": [], "source": "none", "correlated": False}
    try:
        policy = _load_json(POLICY_PATH)
    except Exception:
        return {"packets": [], "source": "none", "correlated": False}

    sniff_cfg = dict(policy.get("packet_sniffing") or {})
    force_source = ""
    if isinstance(capture_context, dict):
        force_source = str(capture_context.get("source") or "").strip().lower()
    sniff_source = force_source or str(sniff_cfg.get("source", "")).strip().lower()
    if sniff_source in ("windows_tcp_snapshot", "process_bound_live"):
        has_pid_filter = bool(_capture_pids(capture_context))
        has_name_filter = bool(_capture_process_names(capture_context))
        provider_id, provider = _resolve_provider(capture_context)
        provider_kind = str((provider or {}).get("kind") or "").strip().lower()
        if not provider_kind:
            provider_kind = "windows_tcp_snapshot"
        if not has_pid_filter and not has_name_filter:
            return {
                "packets": [],
                "source": "process_bound_live",
                "correlated": True,
                "note": "missing_process_filter",
                "provider_id": provider_id or None,
                "provider_kind": provider_kind,
            }
        limit = int(sniff_cfg.get("max_sample", 32) or 32)
        snap: list[dict[str, Any]]
        if provider_kind == "linux_ss_snapshot":
            snap = _collect_linux_ss_snapshot(
                limit,
                expected_flow_profile=expected_flow_profile,
                capture_context=capture_context,
            )
        else:
            snap = _collect_windows_tcp_snapshot(
                limit,
                expected_flow_profile=expected_flow_profile,
                capture_context=capture_context,
            )
        if snap:
            return {
                "packets": snap,
                "source": "process_bound_live",
                "correlated": True,
                "provider_id": provider_id or None,
                "provider_kind": provider_kind,
            }
        return {
            "packets": [],
            "source": "process_bound_live",
            "correlated": True,
            "note": "no_process_bound_connections",
            "pid_filter": sorted(_capture_pids(capture_context)),
            "provider_id": provider_id or None,
            "provider_kind": provider_kind,
        }
    return {"packets": [], "source": "none", "correlated": False}
