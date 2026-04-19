# AXION Startup & Background Execution Policy v1

Purpose: prevent silent startup/background bloat while keeping user control simple.

## 1) Default behavior

- Newly installed apps are **not** allowed to auto-start by default.
- Newly installed apps are **not** allowed to run persistent background services unless explicitly approved.
- Installer requests for startup/background permissions are shown to user at install-time and can be denied.

## 2) User-controlled startup

Primary UX:
- Right-click app -> **"Add to Startup"**
- Right-click app (if enabled) -> **"Remove from Startup"**

Secondary UX:
- Control Panel -> Startup Manager
- Batch enable/disable with impact score

## 3) Background execution classes

- `none` (default)
- `on-demand` (allowed only while app is open or called)
- `scheduled` (time/event based, explicit user approval)
- `persistent` (admin-approved only; strong justification)

## 4) Install-time permission prompts

If app requests startup/background rights, show:
- requested mode
- reason from app manifest
- estimated resource impact
- Allow once / Always allow / Deny

## 5) Enforcement

- No hidden startup registration writes.
- No hidden service creation by user-mode apps.
- All startup/background grants are auditable and revocable.

## 6) Startup Manager fields

- App name
- Publisher/signature status
- Startup status (enabled/disabled)
- Last launch impact (low/med/high)
- Background mode
- User who granted permission
- Corr id

## 7) Decision codes

- `STARTUP_ENABLE_OK`
- `STARTUP_DISABLE_OK`
- `STARTUP_DENY_POLICY`
- `BGRND_GRANT_OK`
- `BGRND_DENY_POLICY`
- `BGRND_REVOKE_OK`

## 8) Definition of done (v1)

- Right-click startup toggle works.
- Silent auto-start from third-party installers is blocked.
- Background execution is opt-in and visible.
- User can revoke permissions instantly.
