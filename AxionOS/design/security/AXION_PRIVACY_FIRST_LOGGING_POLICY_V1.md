# AXION Privacy-First Logging Policy v1

Purpose: prevent snooping while preserving enough telemetry for reliability and security.

## 1) Default Logging Scope

Allowed by default:
- errors/failures
- config/policy changes
- security decisions (allow/deny/quarantine codes)
- service lifecycle events (start/stop/crash)

Not allowed by default:
- full command content capture
- document/content payload logging
- keystroke-level logging
- clipboard content logging
- full-screen/user activity recording

## 2) Log Levels

- `ERROR` (default)
- `CHANGE` (default)
- `WARN` (optional)
- `DEBUG` (off by default, time-limited)

## 3) Redaction Rules

- secrets/tokens/passwords always redacted
- PII minimization in event fields
- hash/IDs preferred over raw values where possible

## 4) Retention

- error/change logs: 30 days default
- debug logs: max 24h unless manually pinned
- security audit logs: policy-defined retention

## 5) User Controls

- view logging policy in Control Panel
- one-click export for support bundle (explicit consent)
- one-click purge of non-required logs

## 6) Compliance Guard

- attempts to enable invasive logs require admin + explicit warning
- any policy override emits `log.policy.override` audit event
