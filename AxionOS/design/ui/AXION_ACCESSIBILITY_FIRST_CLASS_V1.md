# AXION Accessibility First-Class Spec v1

Purpose: deliver accessibility as a core quality bar, not a compliance checkbox.

## Principle
Accessibility is a product requirement for every system app and shell component.

## 1) Vision & Inclusion Targets

- Motor, visual, hearing, cognitive, and speech accessibility support by default.
- Equal-path UX: accessible flows must not be second-class or hidden.
- Performance parity: accessibility features must remain responsive.

## 2) Core Accessibility Suite (OS-level)

1. **Screen Reader** (Axion Narrator)
2. **Magnifier** with docked/lens/full-screen modes
3. **High Contrast + Theme Controls**
4. **Text Size & UI Scale Controls** (global + per-app hints)
5. **Live Captions** for media/system audio (where available)
6. **Voice Access/Control** (phase rollout)
7. **On-screen Keyboard** + switch access
8. **Sticky/Filter/Toggle keys**
9. **Pointer/Focus visibility enhancements**
10. **Color filter modes** (color blindness support)

## 3) Input Accessibility

- Full keyboard navigability for shell and all first-party apps.
- Clear focus order + visible focus rings.
- Optional dwell-click and click-lock.
- Remappable shortcuts and global shortcut conflict manager.

## 4) Visual Accessibility

- WCAG-targeted contrast baselines for core UI.
- Reduced-motion mode enforced globally.
- Animation disable option for sensitive users.
- User-selectable font families and readability modes.

## 5) Hearing Accessibility

- System-wide captions toggle in tray quick settings.
- Visual alerts replacement for sound notifications.
- Independent left/right and frequency enhancement controls (where supported).

## 6) Cognitive Accessibility

- Simplified UI mode (reduced clutter)
- Consistent icon/label language
- Optional confirmation prompts for destructive actions
- Reading mode for long settings/help content

## 7) Accessibility in App VM Model

- Accessibility APIs/events pass safely into capsule apps.
- App capsule launch policy requires accessibility capability declaration.
- Accessibility overlays work across host shell + capsule windows.

## 8) Developer Requirements (first-party baseline)

Each app must provide:
- semantic labels/roles for controls
- keyboard shortcuts + discoverability
- screen reader announcements for state changes
- no color-only state meaning
- caption/subtitle support where media is involved

## 9) QA Gates (non-negotiable)

- Accessibility regression suite in CI for first-party apps.
- Manual assistive-tech passes before release.
- Keyboard-only end-to-end pass for critical workflows.
- Contrast and focus audits on every shell/theme update.

## 10) Definition of Done (v1)

- Core shell (taskbar/start/settings/control panel/utilities) fully keyboard + screen-reader usable.
- High-contrast and reduced-motion modes work system-wide.
- Accessibility settings are easy to find and persist correctly.
- First-party app suite meets baseline accessibility checklist before ship.
