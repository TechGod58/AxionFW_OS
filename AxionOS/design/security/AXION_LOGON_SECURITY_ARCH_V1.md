# AXION Logon Security Architecture v1

Purpose: define OS-level authentication/authorization early to avoid late retrofit risk.

## 1) Security Principles

- Default-deny before user session is established.
- Strong local auth first (offline-capable).
- Session tokens are short-lived and revocable.
- Privilege escalation is explicit, time-bounded, auditable.
- No hidden bypass paths around logon gate.

## 2) Boot -> Logon -> Session Chain

1. Boot integrity checks (platform + OS policy profile)
2. Pre-logon secure desktop (isolated input path)
3. Credential verification (primary + optional factor)
4. Session key issuance
5. User shell unlock
6. Continuous session guard (lock/re-auth triggers)

## 3) Auth Methods (v1)

Required:
- Password/passphrase (local account)

Optional (configurable):
- PIN (device-bound)
- Security key (FIDO2/WebAuthn-style target)
- Recovery key flow (offline recovery package)

## 4) Account Model

- Local user accounts (v1)
- Roles:
  - `Operator`
  - `Admin`
  - `Service`
- Least-privilege default role assignment

## 5) Session Security

- Idle lock timer policy
- Re-auth required for privileged actions
- Session anomaly triggers: force lock + security event
- Corr-tagged privileged actions for traceability

## 6) Elevation Model

- Standard user context by default
- Elevation prompt for admin actions
- Elevation token TTL (e.g., 5-15 min)
- Elevation can be revoked centrally from Control Surface

## 7) Credential & Secret Handling

- Credentials stored as salted strong hashes
- Secrets never logged in plaintext
- Secure input channel for password/PIN
- Anti-bruteforce controls:
  - exponential backoff
  - temporary lockout threshold

## 8) Audit Events (required)

- `auth.logon.success`
- `auth.logon.fail`
- `auth.lockout.triggered`
- `auth.session.locked`
- `auth.session.unlocked`
- `auth.elevation.granted`
- `auth.elevation.revoked`

All include: user_id, device_id, corr (when present), timestamp, reason code.

## 9) UX Requirements (Windows-familiar)

- Lock screen + sign-in screen model users recognize
- Clear error messages without leaking sensitive auth internals
- Fast account switch
- Ctrl+Alt+Del equivalent secure attention sequence (future target)

## 10) v1 Non-goals

- Enterprise domain join
- Cloud identity dependency
- Full SSO federation

## 11) Definition of Done (v1)

- User cannot access shell without successful logon.
- Failed auth attempts throttle and lock out per policy.
- Privileged operations always require elevation path.
- Auth and elevation events visible in TraceView with reason codes.
