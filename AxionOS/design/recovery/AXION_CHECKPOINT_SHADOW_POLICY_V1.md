# AXION Checkpoint & Shadow Copy Policy v1

## 1) Retention Policy

- Keep last 20 system checkpoints
- Keep all checkpoints for last 7 days
- Keep daily checkpoint for last 30 days
- Pin manually-tagged checkpoints until unpinned

## 2) Storage Zones

- `<AXIONOS_ROOT>\data\checkpoints\system\`
- `<AXIONOS_ROOT>\data\checkpoints\capsule\`
- `<AXIONOS_ROOT>\data\checkpoints\metadata\`

## 3) Integrity Requirements

- Each checkpoint manifest includes sha256 per artifact
- Manifest signed with local trust key
- Restore refuses unsigned/tampered checkpoints

## 4) Trigger Events

Create checkpoint before:
- app install/update promotion
- policy update
- driver promotion
- shell/runtime package upgrade

## 5) Restore Safety Guards

- Dry-run preview required before apply
- Destructive restore requires two-step confirmation token
- Post-restore health and IG checks mandatory

## 6) Decision Codes

- `CKPT_CREATE_OK`
- `CKPT_CREATE_FAIL`
- `ROLLBACK_OK`
- `ROLLBACK_FAIL_INTEGRITY`
- `ROLLBACK_FAIL_HEALTH`
- `RESTORE_ABORT_CONFIRMATION`

