import provenance_guard
from provenance_guard import issue_provenance_envelope, verify_provenance_envelope, load_policy


def test_installer_provenance_issue_and_verify():
    issued = issue_provenance_envelope(
        subject_type="installer",
        artifact_path="qa_setup.msi",
        family="windows",
        profile="win11",
        metadata={"installer_app_id": "qa_setup"},
        source_commit_sha="1111111111111111111111111111111111111111",
        build_pipeline_id="axion-ci-main",
    )
    assert issued["ok"] is True
    check = verify_provenance_envelope(
        subject_type="installer",
        artifact_path="qa_setup.msi",
        envelope=issued["envelope"],
        family="windows",
        profile="win11",
        metadata={"installer_app_id": "qa_setup"},
    )
    assert check["ok"] is True
    assert check["code"] == "PROVENANCE_VERIFIED"
    assert check["subject_hash"]


def test_module_provenance_missing_fails_closed():
    check = verify_provenance_envelope(
        subject_type="module",
        artifact_path="module.json",
        envelope=None,
        metadata={"app_id": "builder_demo", "name": "Builder Demo", "version": "0.1.0", "runtime_mode": "capsule"},
    )
    assert check["ok"] is False
    assert check["code"] == "PROVENANCE_ENVELOPE_MISSING"


def test_provenance_signature_tamper_rejected():
    issued = issue_provenance_envelope(
        subject_type="installer",
        artifact_path="qa_tamper.deb",
        family="linux",
        profile="linux_current",
        metadata={"installer_app_id": "qa_tamper"},
        source_commit_sha="2222222222222222222222222222222222222222",
        build_pipeline_id="axion-ci-main",
    )
    assert issued["ok"] is True
    envelope = dict(issued["envelope"])
    envelope["signature"] = "deadbeef" + str(envelope["signature"])[8:]
    check = verify_provenance_envelope(
        subject_type="installer",
        artifact_path="qa_tamper.deb",
        envelope=envelope,
        family="linux",
        profile="linux_current",
        metadata={"installer_app_id": "qa_tamper"},
    )
    assert check["ok"] is False
    assert check["code"] == "PROVENANCE_SIGNATURE_INVALID"


def test_issue_fails_when_external_key_source_missing(monkeypatch):
    monkeypatch.delenv("AXION_KMS_RELEASE_SIGNING_KEY_01", raising=False)
    monkeypatch.delenv("AXION_HSM_RELEASE_SIGNING_KEY_02", raising=False)
    issued = issue_provenance_envelope(
        subject_type="installer",
        artifact_path="qa_missing_key_source.msi",
        family="windows",
        profile="win11",
        metadata={"installer_app_id": "qa_missing_key_source"},
        source_commit_sha="3333333333333333333333333333333333333333",
        build_pipeline_id="axion-ci-main",
    )
    assert issued["ok"] is False
    assert issued["code"] == "PROVENANCE_KEY_SOURCE_UNAVAILABLE"


def test_issue_fails_when_rotation_policy_lock_broken(monkeypatch):
    broken = load_policy()
    broken_keys = dict(broken.get("trusted_keys", {}))
    key1 = dict(broken_keys.get("axion-release-key-01", {}))
    key1.pop("next_key_id", None)
    broken_keys["axion-release-key-01"] = key1
    broken["trusted_keys"] = broken_keys
    monkeypatch.setattr(provenance_guard, "load_policy", lambda: broken)
    issued = issue_provenance_envelope(
        subject_type="installer",
        artifact_path="qa_rotation_lock.msi",
        family="windows",
        profile="win11",
        metadata={"installer_app_id": "qa_rotation_lock"},
        source_commit_sha="4444444444444444444444444444444444444444",
        build_pipeline_id="axion-ci-main",
    )
    assert issued["ok"] is False
    assert issued["code"] == "PROVENANCE_KEY_ROTATION_POLICY_VIOLATION"
