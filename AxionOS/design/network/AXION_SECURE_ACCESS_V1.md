# AXION Secure Access v1

Purpose: unified OS-level secure access for VPN + remote desktop with centralized Axion policy controls.

## 1) Objectives

- One native access surface for users (no tool sprawl)
- Broad protocol compatibility via standards + connector model
- Security posture enforced by Axion (not fragmented in third-party clients)
- Full corr-traced audit for connect/disconnect/auth/elevation actions

## 2) Product Components

- **Axion Access Center** (UI)
  - VPN profiles, remote sessions, policy status, active tunnels
- **Access Broker Service**
  - orchestrates connectors, enforces policy, emits audit events
- **Credential/Vault Bridge**
  - pulls secrets from protected store only at runtime
- **Policy Engine Hooks**
  - device posture, allow/deny rules, split-tunnel policy, kill-switch

## 3) Compatibility Strategy

Tier 1 (native first):
- WireGuard
- OpenVPN
- IKEv2/IPsec

Tier 2 (connector adapters):
- enterprise ecosystems (Cisco-like and others) via isolated connector modules

Tier 3 (future):
- managed cloud enterprise gateways

## 4) Security Controls

- Default-deny connections not matching policy
- Optional "require trusted device posture" before connect
- DNS leak prevention + kill switch policy
- Split/full tunnel policy per profile
- Session timeout + reauth options
- Cert pinning / trust store controls

## 5) Audit Events

- `access.vpn.connect.requested`
- `access.vpn.connect.succeeded`
- `access.vpn.connect.failed`
- `access.vpn.disconnected`
- `access.remote.session.started`
- `access.remote.session.ended`

All include corr id, profile id, connector id, reason code, timestamps.

## 6) Non-Goals (v1)

- Guarantee parity with every proprietary client feature
- Cloud dependency for core local connectivity
- Hidden auto-elevation for network changes

## 7) Definition of Done (v1)

- User can connect/disconnect through Axion Access Center
- Policy controls applied uniformly across supported connectors
- Session events visible in TraceView + Control Surface
