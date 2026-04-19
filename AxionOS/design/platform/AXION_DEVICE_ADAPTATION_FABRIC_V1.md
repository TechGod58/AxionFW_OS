# AXION Device Adaptation Fabric (DAF) v1

Goal: automatically adapt OS runtime when new hardware appears (cards/devices/USB), with safe install/update flow and fast reattach via shadow profiles.

## 1) Core Concept

When a device is added:
1. Detect device and capabilities
2. Resolve/install driver package in staging
3. Validate in device sandbox
4. Promote to active driver set
5. Rebuild/update dependent runtime bindings
6. Emit corr-traced success/fail events

When a known USB device returns:
- restore prior validated profile from shadow copy (no full reinstall path unless version mismatch)

## 2) Components

- **Device Watcher**
  - listens for PCIe/USB/hotplug events
- **Driver Builder/Resolver**
  - maps hardware IDs -> driver package/profile
- **Driver Sandbox Runner**
  - test-loads driver with policy/invariant checks
- **Promotion Gate**
  - approves/rejects driver activation
- **Runtime Rebind Service**
  - updates OS runtime graph for new hardware
- **Shadow Profile Store**
  - caches validated USB/device state for rapid reattach

## 3) Driver install/update flow

1. `device.detected`
2. `driver.resolve.requested`
3. `driver.staging.ready`
4. `driver.sandbox.test`
5. `driver.promote` or `driver.quarantine`
6. `runtime.rebind`
7. `device.ready`

All with deterministic reason codes.

## 4) USB shadow copy model

On detach:
- save profile snapshot:
  - device id / vendor-product id
  - validated driver version
  - policy profile
  - permission grants
  - known-good runtime config hash

On reattach:
- if snapshot still valid -> quick restore
- else -> resolve/update flow

## 5) USB sandboxing rules

- New USB devices start in restricted sandbox mode
- No raw host write by default
- Explicit grant required for elevated classes (storage/raw HID/debug interfaces)
- File payloads from USB pass promotion/security scanning before placement

## 6) Board update linkage

When a new card/device is promoted:
- trigger controlled board/runtime update plan:
  - capability graph refresh
  - scheduler/allocator profile refresh
  - service dependency re-evaluation
- no blind auto-flash; human approval gate for firmware-level writes

## 7) Data Contracts (starter)

### device.detected
```json
{
  "corr": "corr_dev_001",
  "bus": "usb",
  "device_id": "usb:vid_1234_pid_5678",
  "class": "storage",
  "ts": "2026-03-01T16:45:00Z"
}
```

### driver.decision
```json
{
  "corr": "corr_dev_001",
  "decision": "PROMOTE",
  "code": "DRV_OK",
  "driver_version": "2.1.4",
  "ts": "2026-03-01T16:45:03Z"
}
```

## 8) Deterministic decision codes

- `DRV_OK`
- `DRV_QUEUE_HOST_PRESSURE`
- `DRV_REJECT_SIGNATURE`
- `DRV_REJECT_POLICY`
- `DRV_REJECT_IG`
- `DRV_QUARANTINED`
- `DRV_SHADOW_RESTORE_OK`
- `DRV_SHADOW_RESTORE_STALE`

## 9) v1 Non-goals

- universal driver compiler for all vendors
- autonomous firmware flashing
- cloud-only driver dependency

## 10) Definition of Done (v1)

- New USB device follows detect->sandbox->promote/quarantine flow
- Reattached known USB device restores from shadow profile when valid
- Driver decisions visible in control surface with corr trace
- Runtime rebind event emitted after successful promotion
