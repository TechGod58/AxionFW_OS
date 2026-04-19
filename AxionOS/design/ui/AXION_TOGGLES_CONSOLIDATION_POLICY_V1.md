# AXION Toggles Consolidation Policy v1

Decision:
All common on/off controls that are split across multiple "managers" in other OSes should live in **Toggles** first.

## Principle
- One place for practical switches
- No bloated manager maze
- Advanced details can live in category pages, but the switch itself is in Toggles

## Consolidated Toggle Domains
- Connectivity: wifi, bluetooth, vpn, airplane_mode, metered_network
- Privacy: location, camera_access, microphone_access, clipboard_history, telemetry_mode (quick mode)
- Security: firewall_strict_mode, lockdown_mode, threat_scan_mode_quick
- System: notifications, background_apps, autostart_permission
- Accessibility: reduced_motion, high_contrast, live_captions, on_screen_keyboard
- Personalization: visual_effects, night_light
- Developer: developer_mode

## UX Rules
- Fast search + favorites pinning
- Safe defaults visible
- Reason shown when toggle blocked by policy
- Corr-traced audit per change

## Done criteria
- Toggles includes cross-category switch set
- Category pages deep-link back to toggle IDs
- No duplicate conflicting switches in separate managers
