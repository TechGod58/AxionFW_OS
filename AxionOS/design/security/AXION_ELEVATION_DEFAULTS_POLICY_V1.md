# AXION Elevation Defaults Policy v1

Purpose: safe default privilege behavior for broad users, with power-user options.

## 1) Default Recommendation (all users)

- Shells launch as standard user by default.
- Elevate per task when needed (prompt + reason).
- Time-bounded elevation token (e.g., 10 min).

## 2) Power User Option

- Optional profile: "Prefer elevated shell"
- Requires explicit opt-in in Control Panel -> Security
- Shows persistent elevated-session warning badge
- Logs `elevation.profile.enabled`

## 3) Why not admin-by-default for everyone

- larger blast radius for mistakes/malware
- accidental system changes become easier
- breaks least-privilege security posture

## 4) Balanced model

- Keep your personal profile with elevated preference if desired.
- Ship global default as non-elevated.
- Add quick "Run elevated" shortcut (1 click + confirmation).

## 5) v1 done

- Global default is safe.
- Power users can opt into elevated shell behavior.
- All elevation events remain corr-traced and auditable.
