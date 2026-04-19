# Axion Prompt (Windows-Compatible Command Prompt) Spec v1

## Goal
Axion-native terminal that can execute Windows workflows reliably.

## Name
- Product: **Axion Prompt**
- ID: `axion-prompt`

## Compatibility requirements
- Run native `cmd.exe` commands
- Run PowerShell commands
- Optional WSL passthrough profile
- Preserve PATH/environment inheritance
- Support scripts: `.bat`, `.cmd`, `.ps1`

## Profiles
1. `Windows CMD`
2. `PowerShell`
3. `WSL` (optional if installed)

## Behavior model
- Axion Prompt is a shell host/orchestrator, not a separate incompatible shell language.
- Explicit profile toggle per tab.
- Command history per profile.

## Safety/ops features
- Corr id tagging for privileged operations (when launched from control surface)
- Optional execution policy guardrails
- Transcript logging toggle

## v1 acceptance
- User can run common Windows admin/dev commands without compatibility surprises.
- Profile switching is one-click.
- Exit codes and stderr handling are accurate.
