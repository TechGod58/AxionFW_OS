# AXION Connectivity & Access Hardware Baseline v1

Purpose: define first-class support for core connectivity and identity hardware.

## Included hardware domains (v1 baseline)

1. Bluetooth
2. Ethernet
3. Wi-Fi
4. NFC (Near Field)
5. Proximity card readers
6. Smart card readers

## 1) Bluetooth

Capabilities:
- device discovery/pairing
- audio/input/peripheral profiles
- per-device permission model
- quick connect panel in tray

Security:
- pairing confirmation required
- trust levels (temporary/trusted/blocked)
- background discoverability off by default

## 2) Ethernet

Capabilities:
- DHCP/static config
- VLAN profile support (enterprise)
- link diagnostics
- profile switching (home/work/lab)

Security:
- network zone auto-tagging
- policy hooks into firewall/access tree

## 3) Wi-Fi

Capabilities:
- SSID management
- WPA2/WPA3 profile support
- captive portal handling
- known-network priority ordering

Security:
- random MAC option
- auto-join policy controls
- untrusted network guard profile

## 4) NFC (Near Field)

Capabilities:
- read tag IDs/data (policy-restricted)
- auth token tap workflows
- secure device pairing handoff

Security:
- user confirmation for write actions
- block unknown tag writes by default

## 5) Prox Card Readers

Capabilities:
- card-present events for local login/unlock
- role-based access mapping
- optional MFA factor in enterprise mode

Security:
- anti-replay checks
- failed read lockout policy
- event audit trail required

## 6) Smart Card Readers

Capabilities:
- certificate-based auth
- login/elevation/VPN usage integration
- cert lifecycle + revocation checks

Security:
- PIN retry limits
- lockout on repeated failures
- secure key handling via OS crypto services

## Cross-domain policy rules

- All device additions follow detect -> sandbox validate -> promote path where applicable.
- Permission grants are explicit, revocable, and auditable.
- Device classes can be globally disabled by policy.
- Unknown/high-risk devices default to restricted mode.

## Integration points

- Axion Access Center (network + remote)
- Axion Identity/Auth (logon, MFA)
- Axion Device Adaptation Fabric (driver/runtime rebind)
- Network Access Tree (read/write policy enforcement)

## Decision codes (starter)

- `HW_OK`
- `HW_RESTRICTED_MODE`
- `HW_DENY_POLICY`
- `HW_DENY_AUTH`
- `HW_QUARANTINE`

## v1 definition of done

- User can manage Bluetooth/Ethernet/Wi-Fi from unified connectivity panel.
- NFC/prox/smart-card readers can be enabled and policy-governed.
- Auth/network/security components consume device trust events consistently.
