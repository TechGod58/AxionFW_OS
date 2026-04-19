# AXION Installer Packaging Plan v1

## Why size hasn't jumped much yet
Current work is mostly architecture/spec/runtime scaffolding (text + small scripts), not heavy binaries/assets.
So file count rises faster than total MB.

## Packaging objectives
- One primary installer for end users
- Deterministic, signed, auditable release artifacts
- Support clean install + upgrade + rollback metadata

## Installer contents (v1)
- Axion runtime services (promotion, allocator, auth, access broker stubs)
- Core apps (Control Surface shell, Utilities, Calculator, Notes, Prompt stubs)
- Policy/config defaults
- Wallpaper/assets bundle
- Initial data directories + audit paths

## Install flow
1. Preflight checks (OS version, disk, permissions)
2. Install core runtime
3. Install apps/tools
4. Apply default policies
5. Register services/startup entries
6. Healthcheck + first-run bootstrap

## Upgrade flow
- Preserve user data and policy deltas
- Migrate schema/versioned configs
- Rollback pointer retained

## Output artifacts
- `AxionOS-Setup-<version>.exe`
- `manifest.json`
- `sha256sums.txt`
- `release_notes.md`
- `sbom.spdx.json`

## Non-goals (v1)
- In-place kernel replacement on unknown hosts
- Autonomous firmware flashing
