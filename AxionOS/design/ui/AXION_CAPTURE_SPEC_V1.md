# Axion Capture (Snipping Tool) Spec v1

## Goal
Fast screenshot/snipping utility with Windows-like behavior and Axion-native naming.

## Name
- Product: **Axion Capture**
- Binary/service id: `axion-capture`

## Core modes
- Rectangle snip
- Freeform snip (v2)
- Window snip
- Full screen

## Core actions
- Copy to clipboard
- Save to file
- Send to Axion Promotion Pipeline (`safe://userdocs/snips/...`)
- Quick annotate (pen/highlight, v1 minimal)

## Hotkeys (proposal)
- `Win+Shift+S` equivalent mapping in Axion shell
- `PrintScreen` -> full screen capture

## File defaults
- Format: PNG (default), JPG optional
- Save root: `safe://userdocs/snips/`
- Naming: `snip_YYYYMMDD_HHMMSS.png`

## Security behavior
- Captures from sandbox windows are tagged with source corr id when available
- Save-down goes through promotion policy when persisted
- Clipboard-only captures remain ephemeral

## v1 acceptance
- Capture in all core modes
- Clipboard + save both work
- Promotion handoff works with audit trace
