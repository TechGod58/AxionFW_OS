from safe_uri import resolve_safe_uri


def test_safe_uri_pass(tmp_path):
    zone_root = tmp_path / "projects"
    zone_root.mkdir(parents=True)
    policy = {
        "zones": {
            "projects": {
                "enabled": True,
                "root": str(zone_root),
                "maxBytes": 1024,
                "allowedMimePrefixes": ["application/", "text/"],
                "blockedExtensions": [".exe", ".dll"],
            }
        },
        "disallowedZones": [],
    }
    meta = {"mimeType": "application/json", "sizeBytes": 12}
    ok, code, resolved = resolve_safe_uri("safe://projects/demo/file.json", policy, meta)
    assert ok
    assert code == "MAP_OK"
    assert resolved is not None


def test_safe_uri_reject_blocked_extension(tmp_path):
    zone_root = tmp_path / "projects"
    zone_root.mkdir(parents=True)
    policy = {
        "zones": {
            "projects": {
                "enabled": True,
                "root": str(zone_root),
                "maxBytes": 1024,
                "allowedMimePrefixes": ["application/"],
                "blockedExtensions": [".exe"],
            }
        },
        "disallowedZones": [],
    }
    meta = {"mimeType": "application/octet-stream", "sizeBytes": 44}
    ok, code, _ = resolve_safe_uri("safe://projects/demo/file.exe", policy, meta)
    assert not ok
    assert code == "MAP_FAIL_POLICY_TYPE"


def test_safe_uri_reject_size_policy(tmp_path):
    zone_root = tmp_path / "projects"
    zone_root.mkdir(parents=True)
    policy = {
        "zones": {
            "projects": {
                "enabled": True,
                "root": str(zone_root),
                "maxBytes": 32,
                "allowedMimePrefixes": ["application/"],
                "blockedExtensions": [],
            }
        },
        "disallowedZones": [],
    }
    meta = {"mimeType": "application/json", "sizeBytes": 64}
    ok, code, _ = resolve_safe_uri("safe://projects/demo/file.json", policy, meta)
    assert not ok
    assert code == "MAP_FAIL_POLICY_SIZE"


def test_safe_uri_reject_mime_policy(tmp_path):
    zone_root = tmp_path / "projects"
    zone_root.mkdir(parents=True)
    policy = {
        "zones": {
            "projects": {
                "enabled": True,
                "root": str(zone_root),
                "maxBytes": 512,
                "allowedMimePrefixes": ["application/json"],
                "blockedExtensions": [],
            }
        },
        "disallowedZones": [],
    }
    meta = {"mimeType": "text/plain", "sizeBytes": 12}
    ok, code, _ = resolve_safe_uri("safe://projects/demo/file.txt", policy, meta)
    assert not ok
    assert code == "MAP_FAIL_POLICY_TYPE"

