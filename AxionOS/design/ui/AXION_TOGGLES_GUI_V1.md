# AXION Toggles GUI Spec v1

## Product
- Name: **Toggles**
- ID: `axion-toggles`

## Goal
Single fast GUI for enabling/disabling system features without digging through deep settings menus.

## Core UX
- Grid of large toggle cards
- Search bar at top
- Favorites row (pin most-used toggles)
- Category tabs: Connectivity, Privacy, Security, Performance, Accessibility, Developer

## Default Toggles (v1)
- Wi-Fi
- Bluetooth
- VPN
- Airplane Mode
- Location/GPS
- Camera access
- Microphone access
- Notifications
- Night Light
- Reduced Motion
- High Contrast
- Background App Execution
- Auto-start Permission
- Clipboard History
- Developer Mode

## Behavior
- Toggle changes apply immediately when safe
- High-impact toggles show confirmation
- Every toggle write emits corr-traced audit event
- Failed toggle shows reason code and rollback option

## Integration
- Tray quick settings links into Toggles
- Settings deep-links to same toggle IDs
- Control Panel advanced pages can override policy limits

## Definition of Done (v1)
- User can find and toggle common controls in one place
- State syncs with Settings/Tray without drift
- Permission-sensitive toggles enforce policy and show clear feedback
