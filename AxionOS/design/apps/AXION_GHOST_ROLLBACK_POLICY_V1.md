# AXION Ghost Rollback (Per-File Version Trail) v1

Purpose: lightweight file rollback for office/design apps with auto-snapshots.

## Scope
Applies to:
- Axion Write
- Axion Sheets
- Axion Creative Studio
- Axion Video Studio
- Axion PDF Studio

## 1) Ghost snapshots

- Auto-save creates hidden ghost snapshots.
- Default retention: **6 versions per file**.
- Ring buffer behavior: newest kept, oldest rotated out.

## 2) Class-based retention defaults

- Office docs: 6
- Design images/projects: 8
- Video projects: 10 (metadata snapshots; media blobs referenced)

## 3) User controls

- File -> Version History -> Restore
- File -> Pin Snapshot (protect from rotation)
- App settings can override retention in range 3..20

## 4) Storage model

- Snapshot metadata + diff/chunk strategy where possible
- Path root: `safe://userdocs/.ghost/<app>/<file_id>/`
- Snapshots follow promotion/storage policy

## 5) Safety

- Ghost snapshots are local/private by default
- Snapshot delete is recoverable until cleanup window expires
- All restore actions are corr-traced

## 6) Decision codes

- `GHOST_SAVE_OK`
- `GHOST_ROTATE_OK`
- `GHOST_RESTORE_OK`
- `GHOST_RESTORE_FAIL`
- `GHOST_PIN_OK`

## 7) v1 done

- User can restore prior versions quickly.
- Rotation works deterministically per app class.
