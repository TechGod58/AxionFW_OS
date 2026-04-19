# Axion Shell (PowerShell-Compatible) Spec v1

## Goal
Create Axion-native shell that supports modern automation while preserving Windows command compatibility.

## Name
- Product: **Axion Shell**
- ID: `axion-shell`

## Positioning
- Not a clone.
- A compatibility-first shell host with Axion-native command model.

## Execution profiles
1. Axion Native (future command model)
2. Windows PowerShell compatibility
3. CMD compatibility
4. WSL passthrough (optional)

## v1 compatibility requirements
- Execute PowerShell commands/scripts reliably
- Execute CMD commands/scripts reliably
- Preserve stdout/stderr/exit codes
- Profile switch per tab/session
- Script execution policy controls

## Axion-native additions
- Corr-aware command context (`corr` tagging)
- Structured JSON output mode
- Built-in links to allocator/promotion/security status
- Policy-aware privileged command gating

## Safety model
- Explicit elevation boundary
- Execution transcript toggle
- Redaction mode for secrets in logs

## v1 acceptance
- Admin/dev workflows run with parity in compatibility profiles
- JSON mode available for automation
- Corr trace integration works with Control Surface
