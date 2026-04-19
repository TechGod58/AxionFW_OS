# AXION Preboot-Key Network Binding v1

Purpose: use outside-OS logon trust (preboot keys) to strengthen network authorization decisions inside OS.

## 1) Trust Chain

1. Preboot auth succeeds (password/PIN/security key)
2. Hardware-bound key unseals device trust token
3. OS session starts with `preboot_verified=true`
4. Network Access Broker consumes trust token claims
5. Higher-risk read/write actions require valid trust state

## 2) Why this matters

- Network auth is not based on user password alone.
- Device trust and user trust both required for sensitive actions.
- Stolen credentials from untrusted host are less useful.

## 3) Token Claim Model (example)

```json
{
  "device_id": "axion-host-001",
  "preboot_verified": true,
  "assurance_level": "A2",
  "boot_policy_hash": "sha256:...",
  "expires_at": "2026-03-01T18:00:00Z"
}
```

## 4) Access Tree Integration

Policy can require:
- `preboot_verified=true` for write/admin actions on restricted resources
- downgrade to `READ_ONLY` if only SSO is present without preboot trust
- deny if trust claim expired or boot policy hash mismatched

## 5) VM/Capsule Binding

- Capsules inherit constrained trust context from host session.
- Capsule cannot elevate trust level above host preboot claim.
- Sensitive write paths from capsule require both:
  - host preboot trust
  - explicit capsule policy grant

## 6) Failure Handling

- Missing/invalid trust token -> `NET_DENY_POSTURE`
- Expired claim -> force reauth path
- Boot policy drift -> restricted mode + security alert

## 7) Definition of Done (v1)

- Network broker evaluates preboot trust claim in decisions.
- Restricted write operations are blocked without valid preboot-bound trust.
- Decision/audit trail includes trust claim state.
