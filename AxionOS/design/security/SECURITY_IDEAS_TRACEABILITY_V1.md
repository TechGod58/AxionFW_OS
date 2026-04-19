# Security Ideas Traceability (Today) v1

Purpose: confirm user-requested security ideas are captured in AxionOS design docs.

## A) Captured Ideas -> Spec Mapping

1. **Sandbox-first install/evaluate/push**
   - `<AXIONOS_ROOT>\design\bus_v1\OS_SANDBOX_PROMOTION_PIPELINE_V1.md`
   - `<AXIONOS_ROOT>\design\bus_v1\PROMOTION_DAEMON_INTERFACE_V1.md`

2. **Scan before reaching OS/storage**
   - `<AXIONOS_ROOT>\design\security\AXION_THREAT_SCREENING_PIPELINE_V1.md`
   - `<AXIONOS_ROOT>\design\bus_v1\OS_SANDBOX_PROMOTION_PIPELINE_V1.md`

3. **No-email handoff; internal staging/promotion path**
   - `<AXIONOS_ROOT>\design\bus_v1\OS_SANDBOX_PROMOTION_PIPELINE_V1.md`

4. **Security inside + outside sandboxes**
   - `<AXIONOS_ROOT>\design\security\AXION_THREAT_SCREENING_PIPELINE_V1.md`
   - `<AXIONOS_ROOT>\design\platform\AXION_DEVICE_ADAPTATION_FABRIC_V1.md`

5. **Outside-OS/pre-boot auth direction and optional lock tiers**
   - `<AXIONOS_ROOT>\design\security\AXION_LOGON_SECURITY_ARCH_V1.md`
   - `<AXIONOS_ROOT>\design\security\AXION_IDENTITY_ACCESS_POLICY_V1.md`
   - (next planned) outside-OS auth boundary + lock tiers formalization

6. **No forced full-disk encryption by default; optional stronger locks**
   - `<AXIONOS_ROOT>\design\security\AXION_IDENTITY_ACCESS_POLICY_V1.md`
   - `<AXIONOS_ROOT>\design\security\AXION_THREAT_SCREENING_PIPELINE_V1.md`

7. **ActiveX-class risk denied/isolated**
   - currently captured in chat direction; to formalize in security baseline next patch

8. **USB sandbox + shadow reattach profile**
   - `<AXIONOS_ROOT>\design\platform\AXION_DEVICE_ADAPTATION_FABRIC_V1.md`

9. **Built-in VPN/Remote access under Axion control**
   - `<AXIONOS_ROOT>\design\network\AXION_SECURE_ACCESS_V1.md`
   - `<AXIONOS_ROOT>\design\network\AXION_VPN_CONNECTOR_MODEL_V1.md`
   - `<AXIONOS_ROOT>\design\network\AXION_REMOTE_DESKTOP_HUB_V1.md`

## B) Immediate Gaps to close next

- Add explicit `LEGACY_ACTIVEX_POLICY_V1` (deny by default, isolate-only fallback).
- Add `OUTSIDE_OS_AUTH_BOUNDARY_V1` and `SECURITY_LOCK_TIERS_V1` docs.

## C) Current status

Most security ideas from today are now represented in written design artifacts.

