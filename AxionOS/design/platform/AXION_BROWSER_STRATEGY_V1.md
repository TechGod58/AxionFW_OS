# AXION Browser Strategy v1

Goal: ship a secure, OS-integrated browser quickly without building a new rendering engine from scratch (yet).

## 1) Strategy

Phase 1 (practical):
- Build **Axion Browser** shell/UI on top of a proven open engine runtime.
- Add Axion security integration (capsule launch profile, promotion-aware downloads, corr-trace events).

Phase 2 (advanced):
- Harden process isolation model + Axion policy hooks.
- Build Axion-specific performance/privacy controls.

Phase 3 (long-term, optional):
- Explore custom engine components only where justified (not full engine rewrite unless strategic mandate).

## 2) Why this path

- Faster time-to-market
- Lower risk
- Keeps focus on Axion differentiators (containment, orchestration, auditability)

## 3) Axion Browser requirements (v1)

- Tab sandboxing aligned with capsule model
- Download path forced through `safe://imports/...`
- Optional "Open in isolated capsule" action per download
- Built-in security status chip (site perms/network risk)
- Corr-tagged events for critical actions

## 4) Non-goals (v1)

- New web rendering engine
- New JS engine
- Full extension ecosystem parity on day one
