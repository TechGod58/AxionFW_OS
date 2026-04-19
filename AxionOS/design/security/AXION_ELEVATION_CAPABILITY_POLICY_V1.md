# AXION Elevation Capability Policy v1

Decision update:
- Backwards-compatibility clutter is de-prioritized.
- Every app must support **Run as Administrator** capability.
- Properties dialog must include persistent toggle: **Always run as Administrator**.

## 1) Required UX

- Right-click app/file -> `Run as Administrator`
- Properties -> Compatibility/Security section:
  - [ ] Always run as Administrator
  - [ ] Require confirmation before elevated launch

## 2) Enforcement rules

- Elevation still prompts and is audited.
- Admin token is time-bounded.
- Elevated launch cannot bypass sandbox/promotion policies.
- Elevated state is clearly visible (badge/titlebar marker).

## 3) Data model

Per app entry:
- `allow_run_as_admin` (bool, required true)
- `always_run_as_admin` (bool, user-controlled)
- `last_elevation_by`
- `last_elevation_ts`

## 4) Audit events

- `elevation.requested`
- `elevation.granted`
- `elevation.denied`
- `elevation.always_toggle.changed`

## 5) v1 done

- All first-party launchers expose Run as Administrator.
- Properties toggle persists and applies reliably.
