# AXION Graphics Consistency Policy v1

Purpose: keep graphics behavior consistent between runtime shell and Settings controls.

## 1) Principle
Single source of truth for graphics preferences:
- Settings writes graphics profile
- Shell components consume same profile live
- No hidden per-component drift

## 2) Graphics profile controls (v1)
- Resolution scaling policy
- Refresh-rate preference hint
- Animation quality (high/balanced/low)
- Transparency/blur toggle
- Reduced-motion override
- Color profile/theme accent linkage

## 3) Sync model
1. User changes setting in Settings app
2. Settings publishes `shell.settings.changed` event with graphics key
3. Taskbar/Start/Desktop hosts apply changes live
4. State persisted to graphics profile JSON

## 4) Fallbacks
- If GPU pressure high, auto-step to balanced/low with user notification
- Respect accessibility settings over cosmetic effects

## 5) Definition of done
- Same graphics values shown in Settings and active shell state
- No restart required for core visual updates
