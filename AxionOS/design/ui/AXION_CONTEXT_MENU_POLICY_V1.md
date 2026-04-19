# AXION Context Menu Policy v1 (No "Show more options")

## Decision
AxionOS will display the full context menu by default.
No secondary legacy submenu like "Show more options".

## Rules
- Single unified right-click menu.
- All permitted app/system actions visible in one surface.
- Frequent actions pinned to top, advanced actions grouped (but still visible).
- Search/filter inside context menu for long action lists.
- Disabled actions shown with reason tooltip (policy/permission/state).

## Safety
- Destructive actions require confirmation where appropriate.
- Elevation-required actions show shield marker and reason.
- All context action invocations are auditable by corr id.

## Accessibility
- Full keyboard navigation in context menu.
- Screen-reader role/label coverage.
- High-contrast compliant.

## v1 done
- No "show more" pattern present.
- User can access all actions directly from first menu open.
