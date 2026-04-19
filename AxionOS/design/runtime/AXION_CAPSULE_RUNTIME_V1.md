# AXION Capsule Runtime v1 (ACR)

Purpose: launch app-specific ephemeral VMs from prebuilt framework layers fast enough to beat traditional desktop app startup.

## 1) Core Objectives

- Near-instant app start via clone/snapshot boot path
- Deterministic runtime envelopes per app
- Board-agnostic behavior via capability negotiation
- Strict isolation + controlled save-down

## 2) Runtime Pipeline

1. Resolve app `Capsule Blueprint`
2. Select compatible `Framework Layer` (cached immutable base)
3. Create `Ephemeral Overlay` (writable session layer)
4. Allocate CPU/RAM/GPU via allocator policy
5. Boot capsule VM
6. Stream health/telemetry to Control Surface
7. Persist outputs only through promotion pipeline
8. Destroy overlay and transient contexts on close

## 3) Components

- **Blueprint Resolver**
  - validates manifest + policy + host capability match
- **Layer Catalog Manager**
  - tracks immutable base layers and version pins
- **Clone Engine**
  - fast copy-on-write/snapshot clone from base layer
- **Resource Binder**
  - applies allocator decision and guardrails
- **Execution Broker**
  - starts/stops VMs and exposes corr-linked lifecycle events
- **Save-Down Broker**
  - routes all persist requests to promotion daemon

## 4) Performance Targets (v1)

- Warm start (cached layer): <= 1.5s to interactive window
- Cold start (uncached layer): <= 5s
- Capsule teardown: <= 600ms (excluding artifact promotion)
- Startup variance p95 within 2x median

## 5) Isolation Rules

- No direct host OS/storage write from capsule
- No unrestricted host IPC by default
- Device access policy explicit per blueprint
- GPU access profile constrained by policy
- Clipboard/file transfer mediated via controlled channels

## 6) GPU/Memory Profiles

GPU:
- `none`
- `shared`
- `dedicated-lite`
- `dedicated-full`

Memory classes:
- `small`, `medium`, `large`

Allocator enforces host pressure thresholds and returns ALLOCATE/QUEUE/DENY.

## 7) Compatibility Strategy

- Runtime capability negotiation at launch
- Framework layers abstract board-specific differences
- App blueprints target capabilities, not specific hardware IDs

## 8) Corr-Trace Requirements

Each capsule run emits a shared `corr` timeline:
- allocation decision
- layer selected/version
- boot start/ready
- promotion decisions
- shutdown reason

## 9) Failure Modes

- Capability mismatch -> DENY with deterministic code
- Host pressure -> QUEUE with retry hint
- Policy violation -> QUARANTINE / REJECT_* as applicable
- VM crash -> restart policy (bounded), then isolate

## 10) v1 Non-Goals

- live migration
- cross-host capsule relocation
- multi-tenant cloud orchestration

## 11) Definition of Done

- One blueprint can launch a capsule from cached layer under 1.5s target path
- Save-down path always mediated by promotion gate
- Corr trace shows full allocation->execution->promotion chain
- Queue/deny behavior visible in control surface
