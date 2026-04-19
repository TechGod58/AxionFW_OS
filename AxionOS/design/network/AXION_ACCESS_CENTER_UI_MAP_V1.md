# AXION Access Center UI Map v1

Purpose: define screen structure and interaction map for VPN + Remote access inside Axion Utilities / Control Surface ecosystem.

Related:
- `AXION_SECURE_ACCESS_V1.md`
- `AXION_VPN_CONNECTOR_MODEL_V1.md`
- `AXION_REMOTE_DESKTOP_HUB_V1.md`

---

## 1) Navigation Structure

```text
Axion Utilities
  └─ Access Center
      ├─ Overview
      ├─ VPN
      │   ├─ Profiles
      │   ├─ Active Tunnels
      │   └─ Connector Health
      ├─ Remote
      │   ├─ Session Profiles
      │   ├─ Active Sessions
      │   └─ Security Policies
      ├─ Policies
      ├─ Certificates & Keys
      └─ Audit & Trace
```

---

## 2) Screen Map

## 2.1 Overview Screen

**ID:** `access.overview`

Widgets:
- Active tunnel count
- Active remote session count
- Current posture status (Trusted / Restricted / Blocked)
- Last 5 security events
- Quick actions: Connect, Disconnect All, Open Trace

Data sources:
- `access.vpn.status`
- `access.remote.status`
- `security.posture.state`
- `access.audit.tail`

---

## 2.2 VPN Profiles Screen

**ID:** `access.vpn.profiles`

Table columns:
- profile name
- connector
- mode (full/split)
- last success
- status chip

Actions:
- Connect
- Disconnect
- Edit profile
- Duplicate profile
- Test profile

Modal: **Create/Edit VPN Profile**
Fields:
- connector id
- server/endpoint
- auth reference (`vault://...`)
- tunnel mode
- routes
- DNS
- policy toggles (kill switch, DNS leak prevention)

---

## 2.3 Active Tunnels Screen

**ID:** `access.vpn.active`

Live cards:
- tunnel id
- corr id
- throughput up/down
- latency
- connected duration
- policy state

Actions:
- reconnect
- terminate
- open corr trace

---

## 2.4 Connector Health Screen

**ID:** `access.vpn.connectors`

Cards per connector:
- connector id + version
- health status
- supported auth modes
- last error code

Actions:
- run diagnostics
- export connector logs

---

## 2.5 Remote Session Profiles Screen

**ID:** `access.remote.profiles`

Table columns:
- profile name
- protocol (RDP/VNC/SSH)
- target
- policy badge (clipboard/file transfer)
- last used

Actions:
- Connect
- Edit
- Clone
- Delete

---

## 2.6 Active Remote Sessions Screen

**ID:** `access.remote.active`

Session rows:
- session id
- protocol
- target
- corr id
- health badge
- duration

Actions:
- disconnect
- lock clipboard
- lock file transfer
- open trace

---

## 2.7 Policy Screen

**ID:** `access.policies`

Sections:
- VPN policy (split/full, kill switch, posture requirement)
- Remote policy (clipboard/file transfer/session recording)
- Reauth policy (sensitive target reconnect)

Actions:
- save policy
- validate policy
- rollback to previous

---

## 2.8 Certificates & Keys Screen

**ID:** `access.keys`

Sections:
- installed certs (metadata only)
- key references (vault refs, never raw secrets)
- expiry alerts

Actions:
- import cert
- rotate key reference
- test trust chain

---

## 2.9 Audit & Trace Screen

**ID:** `access.audit`

Features:
- filter by corr id/profile/event code
- timeline view
- export JSON/NDJSON

Events displayed:
- connect/disconnect attempts
- policy denials
- posture failures
- remote session lifecycle

---

## 3) Core Interaction Flows

### Flow A: Connect VPN
1. User selects profile -> Connect.
2. Preflight checks (policy + posture + creds ref).
3. Access Broker invokes connector.
4. UI shows `connecting` -> `connected` or `failed(code)`.
5. Corr trace link appears.

### Flow B: Start Remote Session
1. User selects RDP/VNC/SSH profile.
2. Policy check passes/fails.
3. Session starts with policy badges visible.
4. Runtime telemetry updates session row.

### Flow C: Policy Denial
1. Connect requested.
2. Policy engine returns deny code.
3. UI shows explicit reason + remediation hint.
4. Action options: retry, edit profile, open policy.

---

## 4) Visual Language (aligned with Control Surface)

- Blue = connected/healthy
- Amber = connecting/degraded
- Red = denied/disconnected/error
- Purple accent (Qh8#) = critical strategic/security event markers

UI chips:
- `CONNECTED`
- `CONNECTING`
- `DENIED`
- `POLICY_BLOCKED`
- `POSTURE_FAIL`

---

## 5) Event Topics (UI)

Subscribe:
- `access.vpn.event`
- `access.remote.event`
- `access.connector.health`
- `security.posture.event`
- `audit.trace.event`

Publish:
- `ui.access.vpn.connect`
- `ui.access.vpn.disconnect`
- `ui.access.remote.connect`
- `ui.access.remote.disconnect`
- `ui.access.policy.update`
- `ui.access.trace.open`

---

## 6) Build Order

1. Overview + VPN Profiles
2. Active Tunnels + Remote Profiles
3. Policy + Keys screens
4. Audit & Trace integration
5. Connector health diagnostics view

---

## 7) Definition of Done (v1)

- User can manage VPN + Remote profiles in one UI.
- Connect/disconnect lifecycle visible with reason codes.
- Policy denials are explicit and actionable.
- Corr trace available for all critical actions.
