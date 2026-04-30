<!-- WIP-BANNER:START -->
> [!IMPORTANT]
> **Status: Work in Progress**
>
> This repository is under active development. Content, structure, and implementation details may change frequently.
<!-- WIP-BANNER:END -->

# AxionFW_OS

## Legal Notice (Read First)

This repository is published publicly for visibility and archival purposes only.

No license is granted for any use of this code or related materials.

DO NOT USE, COPY, MODIFY, DISTRIBUTE, DEPLOY, OR CREATE DERIVATIVE WORKS FROM THIS REPOSITORY.

See [LICENSE](LICENSE) and [LEGAL_NOTICE_DO_NOT_USE.md](LEGAL_NOTICE_DO_NOT_USE.md) for the controlling terms.

Combined workspace for AxionFW and AxionOS.

## Layout
- `AxionFW/`
- `AxionOS/`

## Quick Start
Run the combined build wrapper from the repo root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File C:\AxionFW_OS\build_axion_stack.ps1 -SkipFirmwareBuild -QemuTimeoutSeconds 20
```

Build and runtime scripts resolve from the repo root (`C:\AxionFW_OS`) directly.
Compatibility junctions (`C:\AxionFW`, `C:\AxionOS`) are now optional and can be created on demand with:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File C:\AxionFW_OS\tools\ensure_workspace_aliases.ps1 -RepoRoot C:\AxionFW_OS -CreateLegacyAliases
```
