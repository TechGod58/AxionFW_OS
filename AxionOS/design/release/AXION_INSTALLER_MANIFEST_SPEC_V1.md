# AXION Installer File Manifest Spec v1

## Manifest shape

```json
{
  "product": "AxionOS",
  "version": "0.1.0",
  "build_id": "2026-03-01T15:30:00Z",
  "channels": ["stable"],
  "artifacts": [
    {"path":"runtime/promotion/promoted.py","sha256":"...","size":12345},
    {"path":"runtime/allocator/allocator.py","sha256":"...","size":4567}
  ],
  "configs": [
    "config/SAFE_URI_POLICY_V1.json",
    "config/PROMOTION_POLICY_V1.json"
  ],
  "post_install": [
    "create_data_dirs",
    "register_services",
    "run_healthcheck"
  ]
}
```

## Rules
- Every installed file must have hash + size.
- Manifest must be signed.
- Installer refuses if signature/hash mismatch.
- Post-install steps emit audit events.
