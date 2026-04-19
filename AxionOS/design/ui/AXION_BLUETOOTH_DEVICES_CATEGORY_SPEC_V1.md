# AXION Bluetooth & Devices Category Spec v1

Purpose: close out Bluetooth & Devices with practical device management and policy-aware controls.

## Sections
- Bluetooth state + pairing controls
- Connected devices list
- USB devices + sandbox/restricted status
- Driver status/rebind shortcuts
- Reader devices (NFC/prox/smart-card) status

## Actions
- Toggle bluetooth
- Pair/unpair device
- Set device trust (trusted/restricted/blocked)
- Trigger driver rebind
- Open device quarantine review

## Done criteria
- Runtime host persists device state
- Corr-traced events for all actions
- Integrates with Device Adaptation Fabric audit flow
