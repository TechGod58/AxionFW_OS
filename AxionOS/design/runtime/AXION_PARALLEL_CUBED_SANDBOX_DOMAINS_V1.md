# Axion Parallel Cubed Sandbox Domains v1

Goal: make Parallel Cubed a real AxionOS execution boundary. Every install, launch, and persistence action stays inside an explicit sandbox rail, and only a small host control plane may broker cross-boundary work.

## 1) Core Model

Parallel Cubed uses three sandbox regions:
- **logic**: reasoning, shell, browser control, guarded admin tasks
- **memory**: documents, notes, structured work, durable user context
- **emotion**: media capture, creative tools, expressive surfaces

Every region binds to the same three rails:
- **install**: programs install into a capsule image, never directly onto the live host
- **execute**: programs run inside capsules by default
- **persist**: writes exit the capsule only through the promotion pipeline

## 2) Non-Negotiable Invariants

- Default launch mode remains `capsule`.
- All user apps install into sandbox storage first.
- All user apps execute in sandbox domains.
- No app may write directly to live OS storage.
- Persistence must traverse `safe://` promotion.
- Host-required services are limited to control-plane brokers.

## 3) Region Mapping

- `logic` owns: `browser_manager`, `prompt`, `registry_editor`, `shell`, `utilities`, `access_center`
- `memory` owns: `calendar`, `pad`, `pdf_view`, `pdf_studio`, `write`, `sheets`, `gallery`, `notes`
- `emotion` owns: `clock`, `camera`, `creative_studio`, `video_studio`, `arcade`

## 4) Rail Semantics

- **install rail**
  - sandbox image required
  - host mounts denied
  - receipt/provenance required
  - brokered by `allocator`

- **execute rail**
  - capsule launch required
  - host process escape denied
  - network capability only through `network_broker`
  - capsule closes on app close

- **persist rail**
  - promotion required
  - direct OS write denied
  - target scheme is `safe://`
  - brokered by `promotion_daemon`

## 5) Region Flow

The regions keep the original Parallel Cubed directionality:
- `logic -> memory`: policy-approved persistence and document context handoff
- `memory -> emotion`: render and media context handoff inside sandbox execution
- `emotion -> logic`: focus/intent feedback without privilege escalation

Only declared rails may carry those synapses.

## 6) Enforcement Surface

Versioned source of truth: `<AXIONOS_ROOT>\config\PARALLEL_CUBED_SANDBOX_DOMAINS_V1.json`
Validator/emitter: `<AXIONOS_ROOT>	oolsuntime\parallel_cubed_sandbox_domain_integrity_flow.py`
Launcher resolver: `<AXIONOS_ROOT>untime\capsule\launcherspp_launcher_policy.py`
Release gate id: `parallel_cubed_sandbox_domain_integrity`

