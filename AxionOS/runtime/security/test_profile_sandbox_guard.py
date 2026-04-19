import json
from pathlib import Path

from profile_sandbox_guard import ensure_profile_sandbox_storage, evaluate_web_download_target


def _write_policy(path: Path, root_base: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "version": 2,
                "policyId": "AXION_PROFILE_SHELL_FOLDERS_V1",
                "profileRootBase": str(root_base),
                "savePolicy": {
                    "mode": "persistent_profile_sandboxes",
                    "allowedTargets": ["Documents", "Downloads", "Photos", "Music"],
                },
                "folders": {
                    "archives": {"pathSegment": "Archives", "legacyAlias": "Documents"},
                    "downloads": {"pathSegment": "Downloads", "legacyAlias": "Downloads"},
                    "photos": {"pathSegment": "Photos", "legacyAlias": "Pictures"},
                    "music": {"pathSegment": "Music", "legacyAlias": "Music"},
                    "connections": {
                        "pathSegment": "Connections",
                        "legacyAlias": "Links",
                        "displayAliases": ["Connectios"],
                        "pathSegmentAliases": ["Connectios"],
                        "aliases": ["connectios"],
                    },
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _write_vault_policy(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "policyId": "AXION_PROFILE_FOLDER_VAULT_DOMAINS_V1",
                "folders": {
                    "archives": {"domainId": "profile.vault.archives"},
                    "downloads": {"domainId": "profile.vault.downloads"},
                    "photos": {"domainId": "profile.vault.photos"},
                    "music": {"domainId": "profile.vault.music"},
                    "connections": {
                        "domainId": "profile.vault.connections",
                        "domainAliases": ["profile.vault.connectios"],
                        "aliases": ["connectios"],
                    },
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def test_profile_sandbox_storage_created(monkeypatch, tmp_path):
    policy_path = tmp_path / "PROFILE_SHELL_FOLDERS_V1.json"
    vault_path = tmp_path / "PROFILE_FOLDER_VAULT_DOMAINS_V1.json"
    root_base = tmp_path / "profiles"
    _write_policy(policy_path, root_base)
    _write_vault_policy(vault_path)
    monkeypatch.setattr("profile_sandbox_guard.PROFILE_POLICY_PATH", policy_path)
    monkeypatch.setattr("profile_sandbox_guard.FOLDER_VAULT_POLICY_PATH", vault_path)

    out = ensure_profile_sandbox_storage(profile_id="u1", corr="corr_profile_sbx_001")
    assert out["ok"] is True
    assert (root_base / "u1" / "Archives").exists()
    assert (root_base / "u1" / "Downloads").exists()
    assert (root_base / "u1" / "Photos").exists()
    assert (root_base / "u1" / "Music").exists()
    downloads_manifest = root_base / "u1" / "Downloads" / ".axion_folder_vault_domain.json"
    assert downloads_manifest.exists()
    assert json.loads(downloads_manifest.read_text(encoding="utf-8-sig"))["domainId"] == "profile.vault.downloads"


def test_web_download_target_allowed_in_profile_sandbox(monkeypatch, tmp_path):
    policy_path = tmp_path / "PROFILE_SHELL_FOLDERS_V1.json"
    vault_path = tmp_path / "PROFILE_FOLDER_VAULT_DOMAINS_V1.json"
    root_base = tmp_path / "profiles"
    _write_policy(policy_path, root_base)
    _write_vault_policy(vault_path)
    monkeypatch.setattr("profile_sandbox_guard.PROFILE_POLICY_PATH", policy_path)
    monkeypatch.setattr("profile_sandbox_guard.FOLDER_VAULT_POLICY_PATH", vault_path)

    ensure_profile_sandbox_storage(profile_id="u1", corr="corr_profile_sbx_002")
    save_path = str(root_base / "u1" / "Downloads" / "installer.msi")
    out = evaluate_web_download_target(
        save_path=save_path,
        profile_id="u1",
        allowed_folders=["Documents", "Downloads", "Photos", "Music"],
        required_vault_domains=["profile.vault.downloads"],
        app_id="external_installer",
        corr="corr_profile_sbx_003",
    )
    assert out["ok"] is True
    assert out["code"] == "PROFILE_SANDBOX_WEB_DOWNLOAD_ALLOWED"
    assert out["target_vault_domain"] == "profile.vault.downloads"


def test_web_download_target_blocks_c_root(monkeypatch, tmp_path):
    policy_path = tmp_path / "PROFILE_SHELL_FOLDERS_V1.json"
    vault_path = tmp_path / "PROFILE_FOLDER_VAULT_DOMAINS_V1.json"
    root_base = tmp_path / "profiles"
    _write_policy(policy_path, root_base)
    _write_vault_policy(vault_path)
    monkeypatch.setattr("profile_sandbox_guard.PROFILE_POLICY_PATH", policy_path)
    monkeypatch.setattr("profile_sandbox_guard.FOLDER_VAULT_POLICY_PATH", vault_path)

    out = evaluate_web_download_target(
        save_path=r"C:\malware.exe",
        profile_id="u1",
        allowed_folders=["Documents", "Downloads", "Photos", "Music"],
        app_id="external_installer",
        corr="corr_profile_sbx_004",
    )
    assert out["ok"] is False
    assert out["code"] == "PROFILE_SANDBOX_C_ROOT_BLOCKED"


def test_web_download_target_blocks_non_allowed_folder_domain(monkeypatch, tmp_path):
    policy_path = tmp_path / "PROFILE_SHELL_FOLDERS_V1.json"
    vault_path = tmp_path / "PROFILE_FOLDER_VAULT_DOMAINS_V1.json"
    root_base = tmp_path / "profiles"
    _write_policy(policy_path, root_base)
    _write_vault_policy(vault_path)
    monkeypatch.setattr("profile_sandbox_guard.PROFILE_POLICY_PATH", policy_path)
    monkeypatch.setattr("profile_sandbox_guard.FOLDER_VAULT_POLICY_PATH", vault_path)

    ensure_profile_sandbox_storage(profile_id="u1", corr="corr_profile_sbx_005")
    save_path = str(root_base / "u1" / "Downloads" / "installer.msi")
    out = evaluate_web_download_target(
        save_path=save_path,
        profile_id="u1",
        allowed_folders=["Documents", "Downloads", "Photos", "Music"],
        required_vault_domains=["profile.vault.photos"],
        app_id="external_installer",
        corr="corr_profile_sbx_006",
    )
    assert out["ok"] is False
    assert out["code"] == "PROFILE_SANDBOX_FOLDER_DOMAIN_BLOCKED"


def test_web_download_target_accepts_legacy_connections_alias(monkeypatch, tmp_path):
    policy_path = tmp_path / "PROFILE_SHELL_FOLDERS_V1.json"
    vault_path = tmp_path / "PROFILE_FOLDER_VAULT_DOMAINS_V1.json"
    root_base = tmp_path / "profiles"
    _write_policy(policy_path, root_base)
    _write_vault_policy(vault_path)
    monkeypatch.setattr("profile_sandbox_guard.PROFILE_POLICY_PATH", policy_path)
    monkeypatch.setattr("profile_sandbox_guard.FOLDER_VAULT_POLICY_PATH", vault_path)

    ensure_profile_sandbox_storage(profile_id="u1", corr="corr_profile_sbx_legacy_001")
    legacy_dir = root_base / "u1" / "Connectios"
    legacy_dir.mkdir(parents=True, exist_ok=True)
    (legacy_dir / ".axion_folder_vault_domain.json").write_text(
        json.dumps(
            {
                "domainId": "profile.vault.connectios",
                "folderKey": "connectios",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    out = evaluate_web_download_target(
        save_path=str(legacy_dir / "legacy_link.url"),
        profile_id="u1",
        allowed_folders=["Connections"],
        required_vault_domains=["profile.vault.connections"],
        app_id="external_installer",
        corr="corr_profile_sbx_legacy_002",
    )
    assert out["ok"] is True
    assert out["target_vault_domain"] == "profile.vault.connections"
