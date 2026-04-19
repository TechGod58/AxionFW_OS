# AXION Config Registry Cleaner v1

Purpose: safe, high-quality registry/config cleanup utility that matches legacy "Disk Doctor" value without risky destructive behavior.

## Product
- Name: **Axion Registry Doctor**
- ID: `axion-registry-doctor`

## 1) Design Principles

- Safety over aggression
- Deterministic findings with confidence scores
- One-click backup + rollback before any change
- Explain every proposed fix in plain language

## 2) Scan Domains

- Orphaned app keys (uninstalled apps)
- Broken file associations
- Invalid startup entries
- Stale COM/class references
- Dead service references
- Invalid shell/context menu handlers
- Empty/duplicate config branches

## 3) Risk Levels

- Low: dead references with no active dependency
- Medium: likely stale but app-linked
- High: system-critical/hive-sensitive keys (default: do not auto-fix)

## 4) Operation Modes

- Analyze only (default)
- Safe Repair (low risk only)
- Advanced Repair (requires admin + explicit confirmations)

## 5) Safety Guards

- Automatic snapshot before changes (checkpoint + export)
- Transaction log for every edit
- Rollback by corr id and timestamp
- Blocklist of protected system paths/hives
- Dry-run diff preview required before apply

## 6) Performance Targets

- Full scan under 90s on typical user profile (v1 target)
- Incremental scan under 15s

## 7) UX

- Summary score (health index)
- Findings grouped by category/risk
- "Fix selected" + "Fix safe items" actions
- Export report (JSON/TXT)

## 8) Integration

- Launch from Control Panel -> System Tools
- Integrates with Disk Cleanup "Logs & Diagnostics"
- Emits audit events to TraceView

## 9) Decision Codes

- `REG_SCAN_OK`
- `REG_SCAN_PARTIAL`
- `REG_FIX_OK`
- `REG_FIX_SKIPPED_PROTECTED`
- `REG_FIX_ROLLBACK_OK`
- `REG_FIX_FAIL`

## 10) v1 Non-goals

- blind aggressive "delete all" cleaning
- editing protected system roots without override controls

## 11) Definition of Done

- Analyze mode stable and accurate
- Safe Repair produces measurable health improvement
- Rollback works reliably for all applied changes
