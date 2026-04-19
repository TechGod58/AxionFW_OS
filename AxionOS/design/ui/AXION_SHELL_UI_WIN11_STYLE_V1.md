# AXION Shell UI Spec v1 (Windows-11-style, Axion-native)

Goal: deliver familiar modern desktop feel (taskbar + start menu behavior/effects) with original Axion implementation.

## Clean-room rule
- Match UX patterns users love.
- Do NOT copy proprietary code/assets.
- Axion branding, components, and animations are original.

## 1) Taskbar (Axion Bar)

Features to implement:
- Centered icon layout with optional left align toggle
- Pinned + running app indicators
- Live hover previews (window thumbnails)
- Smooth icon animations (open/minimize/attention pulse)
- Blur/translucency backdrop (performance adaptive)
- System tray region (network, sound, battery, clock/calendar)
- Quick settings flyout
- Notification center flyout

## 2) Start Menu (Axion Launch)

Features:
- Centered launcher panel with rounded container
- Search-first top input
- Pinned apps grid
- Recent/recommended list
- Power menu
- Profile/session controls
- Keyboard workflow: Win key open, arrows/tab nav, Enter launch

## 3) Motion + Effects

- 120/60fps adaptive animation targets
- spring-based open/close transitions
- reduced-motion accessibility mode
- blur fallback for low-end hardware
- dynamic accent color from theme/wallpaper (optional)

## 4) Performance budgets

- Start menu open latency target: <120ms warm
- Taskbar interaction response: <16ms input budget
- Shell idle CPU target: <1.5% average

## 5) Integration hooks

- Axion Clock/Calendar in tray
- Axion Access Center quick toggles in quick settings
- Corr-aware app launch telemetry for traceability

## 6) v1 build order

1. Taskbar shell frame + pin/run states
2. Start menu shell + search + pinned grid
3. Tray + quick settings + notifications
4. Motion/effects polish and accessibility pass

## 7) Definition of done

- User gets modern Windows-like comfort immediately.
- UI feels premium/smooth without heavy overhead.
- Entire implementation is Axion-original and extensible.
