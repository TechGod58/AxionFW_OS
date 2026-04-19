# AXION VPN Connector Model v1

Purpose: standardized adapter contract for VPN providers/protocols.

## 1) Connector Interface

Each connector must implement:

- `probeCapabilities()`
- `validateProfile(profile)`
- `connect(profile, credsRef, policyCtx)`
- `disconnect(sessionId)`
- `status(sessionId)`
- `collectTelemetry(sessionId)`

## 2) Connector Metadata

```json
{
  "connector_id": "wg_native",
  "provider": "wireguard",
  "version": "1.0.0",
  "modes": ["full_tunnel", "split_tunnel"],
  "auth": ["key", "cert"],
  "requires_elevation": true
}
```

## 3) Profile Contract

```json
{
  "profile_id": "vpn_office_001",
  "connector_id": "ikev2_native",
  "server": "vpn.example.com",
  "mode": "split_tunnel",
  "routes": ["10.0.0.0/8"],
  "dns": ["10.0.0.53"],
  "auth_ref": "vault://net/vpn_office_001"
}
```

## 4) Policy Context Inputs

- user role
- device posture
- time-based policy windows
- geo/network trust state

## 5) Deterministic Result Codes

- `VPN_OK`
- `VPN_DENY_POLICY`
- `VPN_DENY_POSTURE`
- `VPN_FAIL_AUTH`
- `VPN_FAIL_CONNECTOR`
- `VPN_FAIL_NETWORK`

## 6) Isolation Rules

- Connector modules run in restricted service context
- No direct secret storage in connector code
- No unmanaged update path for connectors

## 7) v1 Implementation Order

1. WireGuard native connector
2. OpenVPN native connector
3. IKEv2/IPsec native connector
4. Enterprise adapter scaffold (Cisco-like integration path)
