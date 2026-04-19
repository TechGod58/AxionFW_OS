#pragma once
#include <stdint.h>

/*
Hook registry: these are the "extension points" you asked for.
Everything is explicit and ordered. Each hook may be a no-op at first.

Design goals:
- deterministic boot sequence
- centralized telemetry of init stages
- ability to swap subsystems without reworking boot flow
*/

typedef enum {
    AX_HOOK_EARLY = 0,
    AX_HOOK_MEM_EARLY,
    AX_HOOK_MM_INIT,
    AX_HOOK_IRQ_INIT,
    AX_HOOK_TIME_INIT,
    AX_HOOK_SCHED_INIT,
    AX_HOOK_IPC_INIT,
    AX_HOOK_SECURITY_INIT,   // IG anchor
    AX_HOOK_BUS_INIT,
    AX_HOOK_DRIVER_INIT,
    AX_HOOK_SYSCALL_INIT,
    AX_HOOK_USERLAND_INIT,
    AX_HOOK_LATE,
    AX_HOOK_COUNT
} ax_hook_stage_t;

typedef struct {
    const char *name;
    void (*fn)(void *ctx);
} ax_hook_t;

void ax_hooks_register(ax_hook_stage_t stage, ax_hook_t hook);
void ax_hooks_run(ax_hook_stage_t stage, void *ctx);
