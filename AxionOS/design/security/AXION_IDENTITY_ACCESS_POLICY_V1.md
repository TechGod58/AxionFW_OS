# AXION Identity & Access Policy v1

## 1) Policy Defaults

- `password_min_length`: 12
- `password_complexity`: enabled
- `max_failed_attempts`: 5
- `lockout_minutes`: 15
- `idle_lock_minutes`: 10
- `elevation_ttl_minutes`: 10
- `require_reauth_for_privileged`: true

## 2) Role Permissions (starter)

Operator:
- run standard apps
- view non-sensitive telemetry
- no policy edits

Admin:
- all Operator permissions
- security policy updates
- service/runtime control
- quarantine override (audited)

Service:
- non-interactive service execution only
- no desktop/session login

## 3) Privileged Action Categories

- security policy change
- service start/stop/restart
- storage placement override
- quarantine release
- shell elevated execution

## 4) Reason Codes

Auth:
- `AUTH_OK`
- `AUTH_FAIL_BAD_SECRET`
- `AUTH_FAIL_LOCKED`
- `AUTH_FAIL_POLICY`

Elevation:
- `ELEV_OK`
- `ELEV_DENY_ROLE`
- `ELEV_DENY_REAUTH`
- `ELEV_EXPIRED`

## 5) Audit Retention

- auth/elevation events retained 90 days local (v1 default)
- exportable from TraceView
