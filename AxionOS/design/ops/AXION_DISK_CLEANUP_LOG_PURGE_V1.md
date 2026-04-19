# AXION Disk Cleanup + Log Purge Spec v1

Purpose: include log cleanup in disk cleanup while protecting required audit trails.

## 1) Cleanup Modes

- Quick Cleanup
  - temp files
  - cache files
  - stale installer remnants
  - non-critical logs older than retention

- Advanced Cleanup (admin)
  - debug logs (all)
  - crash dumps older than threshold
  - optional non-required trace archives

## 2) Log Purge Rules

Can purge:
- debug logs
- non-required operational logs
- temporary trace exports

Cannot purge without elevated confirmation/policy:
- mandatory security audit logs still in retention window
- active incident logs under hold

## 3) UI

Disk Cleanup includes a "Logs & Diagnostics" section:
- estimated reclaimable size
- category checkboxes
- retention warning labels

## 4) Automation

- scheduled cleanup task (default weekly)
- dry-run report before deletion in enterprise mode

## 5) Decision codes

- `CLEANUP_OK`
- `CLEANUP_PARTIAL_POLICY_HOLD`
- `CLEANUP_DENY_PRIVILEGE`
- `CLEANUP_FAIL_IO`
