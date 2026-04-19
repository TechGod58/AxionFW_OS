# AXION Network Access Tree v1

Purpose: deterministic read/write access model for network resources across host + capsules (VMs).

## 1) Core Model

Every access request is evaluated against a tree:

```text
ROOT
 ├─ Subject
 │   ├─ user_role (Operator/Admin/Service)
 │   ├─ session_trust (preboot_verified, sso_verified)
 │   └─ runtime_origin (host | capsule)
 ├─ Resource
 │   ├─ class (share, api, db, remote_session, device)
 │   ├─ sensitivity (public, internal, restricted)
 │   └─ location (local_lan, vpn, internet)
 ├─ Action
 │   ├─ read
 │   ├─ write
 │   ├─ execute
 │   └─ admin
 └─ Context
     ├─ corr
     ├─ device_posture
     ├─ network_zone
     └─ time_policy
```

Decision = `ALLOW` | `READ_ONLY` | `DENY` | `QUARANTINE_PATH`

## 2) VM/Capsule Rules

- Capsule default = `READ_ONLY` to approved network resources.
- `WRITE` requires explicit policy grant by app blueprint + role.
- No direct capsule access to restricted admin shares.
- Unknown protocol/device traffic from capsule -> deny + alert.

## 3) Read/Write Tree Profiles (starter)

### Profile: `office_user`
- Internal docs shares: read/write
- Restricted ops shares: read-only
- Admin services: deny

### Profile: `builder_service`
- Artifact endpoints: read/write
- Secrets endpoints: deny direct (vault broker only)
- Internet egress: allowlist only

### Profile: `remote_session_restricted`
- Clipboard/file channels: policy-gated
- Host admin channels: deny

## 4) Enforcement Points

- Access Broker (pre-request policy eval)
- VPN/Remote connector policy hooks
- Capsule egress filter
- Promotion gate for file persistence

## 5) Decision Codes

- `NET_ALLOW`
- `NET_READ_ONLY`
- `NET_DENY_ROLE`
- `NET_DENY_POSTURE`
- `NET_DENY_ZONE`
- `NET_QUARANTINE`

## 6) Auditing

All decisions must log:
- subject id
- resource id
- requested action
- final decision code
- corr id
- timestamp

## 7) Definition of Done (v1)

- Host and capsule traffic both evaluated by same access tree model.
- Read/write downgrades (READ_ONLY) supported, not just allow/deny.
- Corr-traced logs visible in TraceView.
