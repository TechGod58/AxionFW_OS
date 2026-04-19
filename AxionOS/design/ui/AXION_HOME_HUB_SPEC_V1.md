# AXION Home Hub Spec v1

Purpose: first screen in Settings with high-value system summary and quick actions.

## Sections
- Device Health (CPU/MEM/storage/security status)
- Recent Changes (settings + policy)
- Quick Toggles (wifi/bluetooth/vpn/location/notifications)
- Recovery Shortcuts (checkpoint/restore)
- Update Status

## Rules
- Must be actionable, not decorative.
- Every action links to full category page.
- Show only key signals; avoid clutter.

## Done criteria
- Home route exists in Settings host
- Live summary from shell state + audit tails
- Quick actions emit corr-traced events
