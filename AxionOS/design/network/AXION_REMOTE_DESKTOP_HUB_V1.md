# AXION Remote Desktop Hub v1

Purpose: single Axion-native app for remote access sessions across common protocols.

## 1) Protocol Scope (v1)

- RDP
- VNC
- SSH terminal

## 2) Session UX

- Saved profiles with tags
- One-click connect/disconnect
- Connection health indicator
- Clipboard/file-transfer policy indicator
- Per-session security badge (trusted/restricted)

## 3) Profile Contract

```json
{
  "session_profile_id": "rdp_lab_001",
  "protocol": "rdp",
  "host": "192.168.1.50",
  "port": 3389,
  "auth_ref": "vault://remote/rdp_lab_001",
  "display": {"resolution": "1920x1080", "scaling": 1.0},
  "policy": {"clipboard": "restricted", "file_transfer": "deny"}
}
```

## 4) Security Controls

- Session launch policy checks before connect
- Optional MFA gate for sensitive targets
- Clipboard/file transfer policy enforcement
- Session recording flag (policy-based)

## 5) Audit Events

- `remote.profile.opened`
- `remote.connect.requested`
- `remote.connect.succeeded`
- `remote.connect.failed`
- `remote.disconnect`

All corr-traced and exportable in TraceView.

## 6) Non-Goals (v1)

- Browser-based remote gateway replacement
- Full enterprise broker parity
- Unrestricted file transfer by default

## 7) Definition of Done (v1)

- User launches RDP/VNC/SSH sessions from one Axion tool
- Policy guardrails are visible and enforced
- Session telemetry and audits are corr-linked
