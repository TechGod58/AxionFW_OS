from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


def extension_chain(path: str) -> list[str]:
    name = Path(path).name.lower()
    parts = name.split(".")
    if len(parts) <= 1:
        return []
    chain: list[str] = []
    for i in range(1, len(parts)):
        chain.append("." + ".".join(parts[i:]))
    return chain


def _pick_extension(path: str) -> str | None:
    chain = extension_chain(path)
    return chain[0] if chain else None


def _tokenize(template: list[str], installer_path: str, tokens: dict[str, str] | None = None) -> list[str]:
    replacements = {"installer": str(installer_path)}
    for k, v in (tokens or {}).items():
        replacements[str(k)] = str(v)

    out: list[str] = []
    for token in template:
        value = str(token)
        for key, replacement in replacements.items():
            value = value.replace("{" + key + "}", replacement)
        out.append(value)
    return out


class InstallerAdapter:
    family = "unknown"

    def __init__(self, profile: str, execution_model: str, sandbox_enforced: bool):
        self.profile = str(profile)
        self.execution_model = str(execution_model)
        self.sandbox_enforced = bool(sandbox_enforced)

    def supports_extension(self, ext: str) -> bool:
        return ext.lower() in self._routing_map()

    def _routing_map(self) -> dict[str, dict[str, Any]]:
        raise NotImplementedError

    def capture_provider_id(self) -> str | None:
        return None

    def plan(self, installer_path: str, install_context: dict[str, Any] | None = None) -> dict[str, Any]:
        ext = _pick_extension(installer_path)
        if not ext:
            return {"ok": False, "code": "INSTALLER_EXTENSION_MISSING"}
        route = self._routing_map().get(ext.lower())
        if not route:
            return {"ok": False, "code": "INSTALLER_EXTENSION_UNSUPPORTED_BY_ADAPTER", "extension": ext}
        cmd_template = [str(token) for token in route.get("command", [])]
        token_ctx = {
            "installer_artifact": str(Path(installer_path).name),
            "install_root": str((install_context or {}).get("install_root") or ""),
            "install_path": str((install_context or {}).get("install_path") or ""),
            "environment_root": str((install_context or {}).get("environment_root") or ""),
            "projection_root": str((install_context or {}).get("projection_root") or ""),
        }
        return {
            "ok": True,
            "code": "INSTALLER_EXEC_PLAN_READY",
            "family": self.family,
            "profile": self.profile,
            "execution_model": self.execution_model,
            "sandbox_enforced": self.sandbox_enforced,
            "installer_path": installer_path,
            "installer_artifact": Path(installer_path).name,
            "installer_extension": ext.lower(),
            "adapter_id": str(route.get("adapter_id", "")),
            "executor": str(route.get("executor", "")),
            "capture_provider_id": str(route.get("capture_provider_id", "") or self.capture_provider_id() or ""),
            "install_root": token_ctx["install_root"] or None,
            "install_path": token_ctx["install_path"] or None,
            "environment_root": token_ctx["environment_root"] or None,
            "projection_root": token_ctx["projection_root"] or None,
            "command": _tokenize(cmd_template, installer_path, token_ctx),
        }

    def execute(self, plan: dict[str, Any], live_execution: bool, timeout_sec: int = 120) -> dict[str, Any]:
        if not bool(plan.get("ok")):
            return {"ok": False, "code": "INSTALLER_EXEC_PLAN_INVALID", "plan": plan}

        if not live_execution:
            cmd_preview = [str(token) for token in plan.get("command", [])]
            process_name = Path(cmd_preview[0]).name.lower() if cmd_preview else None
            return {
                "ok": True,
                "code": "INSTALLER_EXECUTION_SIMULATED",
                "live_execution": False,
                "exit": 0,
                "pid": None,
                "process_name": process_name,
                "plan": plan,
                "stdout": "",
                "stderr": "",
            }

        cmd = [str(token) for token in plan.get("command", [])]
        if not cmd:
            return {"ok": False, "code": "INSTALLER_EXEC_COMMAND_EMPTY", "plan": plan}
        if shutil.which(cmd[0]) is None:
            return {
                "ok": False,
                "code": "INSTALLER_EXECUTOR_MISSING",
                "plan": plan,
                "pid": None,
                "process_name": Path(cmd[0]).name.lower(),
                "missing_binary": cmd[0],
            }
        proc = None
        try:
            install_cwd = str(plan.get("install_path") or "").strip() or None
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=install_cwd,
            )
            pid = int(proc.pid)
            stdout, stderr = proc.communicate(timeout=max(1, int(timeout_sec)))
        except subprocess.TimeoutExpired as ex:
            if proc is not None:
                proc.kill()
                killed_stdout, killed_stderr = proc.communicate()
            else:
                killed_stdout, killed_stderr = ex.stdout, ex.stderr
            return {
                "ok": False,
                "code": "INSTALLER_EXECUTION_TIMEOUT",
                "plan": plan,
                "pid": int(proc.pid) if proc is not None else None,
                "process_name": Path(cmd[0]).name.lower(),
                "stdout": (killed_stdout or "")[:400],
                "stderr": (killed_stderr or "")[:400],
            }
        return {
            "ok": proc.returncode == 0,
            "code": "INSTALLER_EXECUTION_OK" if proc.returncode == 0 else "INSTALLER_EXECUTION_FAIL",
            "live_execution": True,
            "exit": proc.returncode,
            "pid": pid,
            "process_name": Path(cmd[0]).name.lower(),
            "plan": plan,
            "stdout": (stdout or "")[:800],
            "stderr": (stderr or "")[:800],
        }


class WindowsInstallerAdapter(InstallerAdapter):
    family = "windows"

    def capture_provider_id(self) -> str | None:
        return "windows_tcp_snapshot_provider_v1"

    def _routing_map(self) -> dict[str, dict[str, Any]]:
        return {
            ".msi": {
                "adapter_id": "windows_msi_adapter_v1",
                "executor": "sandbox_windows_compat",
                "command": ["msiexec", "/i", "{installer}", "TARGETDIR={install_path}", "/qn", "/norestart"],
            },
            ".exe": {
                "adapter_id": "windows_exe_adapter_v1",
                "executor": "sandbox_windows_compat",
                "command": ["{installer}", "/S", "/D={install_path}"],
            },
            ".msix": {
                "adapter_id": "windows_msix_adapter_v1",
                "executor": "sandbox_windows_compat",
                "command": [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    "Add-AppxPackage -Path '{installer}';$env:AXION_INSTALL_PATH='{install_path}'",
                ],
            },
            ".appx": {
                "adapter_id": "windows_appx_adapter_v1",
                "executor": "sandbox_windows_compat",
                "command": [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    "Add-AppxPackage -Path '{installer}';$env:AXION_INSTALL_PATH='{install_path}'",
                ],
            },
            ".cmd": {
                "adapter_id": "windows_cmd_adapter_v1",
                "executor": "sandbox_windows_compat",
                "command": ["cmd", "/c", "set AXION_INSTALL_PATH={install_path}&&{installer}"],
            },
            ".bat": {
                "adapter_id": "windows_bat_adapter_v1",
                "executor": "sandbox_windows_compat",
                "command": ["cmd", "/c", "set AXION_INSTALL_PATH={install_path}&&{installer}"],
            },
        }


class LinuxInstallerAdapter(InstallerAdapter):
    family = "linux"

    def capture_provider_id(self) -> str | None:
        return "linux_ss_snapshot_provider_v1"

    def _routing_map(self) -> dict[str, dict[str, Any]]:
        return {
            ".deb": {
                "adapter_id": "linux_deb_adapter_v1",
                "executor": "sandbox_linux_compat",
                "command": ["dpkg", "--root={install_path}", "-i", "{installer}"],
            },
            ".rpm": {
                "adapter_id": "linux_rpm_adapter_v1",
                "executor": "sandbox_linux_compat",
                "command": ["rpm", "--root", "{install_path}", "-i", "{installer}"],
            },
            ".pkg.tar": {
                "adapter_id": "linux_pkg_tar_adapter_v1",
                "executor": "sandbox_linux_compat",
                "command": ["pacman", "--root", "{install_path}", "-U", "{installer}", "--noconfirm"],
            },
            ".pkg.tar.zst": {
                "adapter_id": "linux_pkg_tar_zst_adapter_v1",
                "executor": "sandbox_linux_compat",
                "command": ["pacman", "--root", "{install_path}", "-U", "{installer}", "--noconfirm"],
            },
            ".run": {
                "adapter_id": "linux_run_adapter_v1",
                "executor": "sandbox_linux_compat",
                "command": ["sh", "{installer}", "--prefix", "{install_path}"],
            },
            ".appimage": {
                "adapter_id": "linux_appimage_adapter_v1",
                "executor": "sandbox_linux_compat",
                "command": ["sh", "-c", "cp '{installer}' '{install_path}/' && chmod +x '{install_path}/{installer_artifact}'"],
            },
            ".flatpak": {
                "adapter_id": "linux_flatpak_adapter_v1",
                "executor": "sandbox_linux_compat",
                "command": ["flatpak", "install", "-y", "{installer}"],
            },
            ".snap": {
                "adapter_id": "linux_snap_adapter_v1",
                "executor": "sandbox_linux_compat",
                "command": ["snap", "install", "{installer}"],
            },
            ".tar.gz": {
                "adapter_id": "linux_tar_gz_adapter_v1",
                "executor": "sandbox_linux_compat",
                "command": ["tar", "-xf", "{installer}", "-C", "{install_path}"],
            },
            ".tar.xz": {
                "adapter_id": "linux_tar_xz_adapter_v1",
                "executor": "sandbox_linux_compat",
                "command": ["tar", "-xf", "{installer}", "-C", "{install_path}"],
            },
        }


def build_adapter(family: str, profile: str, execution_model: str, sandbox_enforced: bool) -> InstallerAdapter | None:
    key = str(family).lower()
    if key == "windows":
        return WindowsInstallerAdapter(profile, execution_model, sandbox_enforced)
    if key == "linux":
        return LinuxInstallerAdapter(profile, execution_model, sandbox_enforced)
    return None


def build_replay_signature(plan: dict[str, Any]) -> str:
    canonical = {
        "adapter_id": str(plan.get("adapter_id", "")),
        "family": str(plan.get("family", "")),
        "profile": str(plan.get("profile", "")),
        "installer_artifact": str(plan.get("installer_artifact", "")),
        "installer_extension": str(plan.get("installer_extension", "")),
        "execution_model": str(plan.get("execution_model", "")),
        "sandbox_enforced": bool(plan.get("sandbox_enforced", False)),
        "executor": str(plan.get("executor", "")),
        "capture_provider_id": str(plan.get("capture_provider_id", "")),
        "command": [str(x) for x in plan.get("command", [])],
    }
    digest = hashlib.sha256(json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    return digest
