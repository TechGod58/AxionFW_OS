# AXION App Suite Matrix v1

Purpose: track common OS apps/features requested and current design status.

## Status legend
- DONE_SPEC: spec exists
- NEXT_SPEC: queued next
- BUILD_NEXT: spec exists and should be scaffolded next

| Feature | Axion Name | Status | Notes |
|---|---|---|---|
| Command Prompt | Axion Prompt | DONE_SPEC | Windows-compatible profile host defined |
| PowerShell-compatible shell | Axion Shell | DONE_SPEC | Axion-native + compatibility model defined |
| Sticky Notes | Axion Notes | DONE_SPEC | OS-level notes utility specified |
| Calculator (+Mortgage/Cards/Car) | Axion Calculator | DONE_SPEC | Spec + wireframe + test vectors done |
| Alarm Clock | Axion Clock | NEXT_SPEC | Add alarms/timers/world clock |
| Calendar | Axion Calendar | NEXT_SPEC | Local-first calendar/reminders |
| Notepad | Axion Pad | NEXT_SPEC | Lightweight text editor |
| PDF Reader | Axion PDF View | NEXT_SPEC | Open/annotate/basic forms |
| PDF Editor | Axion PDF Studio | NEXT_SPEC | Merge/split/sign/edit basics |
| Word-like app | Axion Write | NEXT_SPEC | Core document editing |
| Excel-like app | Axion Sheets | NEXT_SPEC | Tables/formulas/charts basics |
| Camera app | Axion Camera | NEXT_SPEC | Photo/video + rich controls |
| Browser | Axion Browser | DONE_SPEC | Strategy doc: proven engine + Axion controls |
| Utilities hub | Axion Utilities | DONE_SPEC | Core utilities shell specified |

## Recommended build order (user value first)
1. Axion Clock + Axion Calendar
2. Axion Pad
3. Axion PDF View -> Axion PDF Studio
4. Axion Camera
5. Axion Write + Axion Sheets

## Cross-cutting rule
All app installs/updates follow `AXION_SANDBOXED_UPDATE_INSTALL_FLOW_V1.md`.
