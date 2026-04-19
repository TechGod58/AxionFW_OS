# Axion Compatibility Sandbox Runtime v1

Goal: every app launch prepares a sandbox environment first, and after first run AxionOS keeps a reusable warm shell to reduce startup time on later launches.

## Families
- `native_axion`
- `windows`
- `linux`

## Warm Shell Rule
- first run creates the sandbox shell and records it in `SANDBOX_SHELL_CACHE_V1.json`
- later launches reuse the prepared shell when policy allows
- closing the app still terminates the live session; only the reusable shell definition remains

## Compatibility Direction
- Windows compatibility profiles span `win95` through `win11`
- Linux compatibility profiles span early Linux userland through `linux_current`
- all compatibility targets remain sandbox-only
