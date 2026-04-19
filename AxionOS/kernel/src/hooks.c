#include "axion/hooks.h"

#define AX_MAX_HOOKS_PER_STAGE 16

static ax_hook_t g_hooks[AX_HOOK_COUNT][AX_MAX_HOOKS_PER_STAGE];
static uint32_t g_hook_counts[AX_HOOK_COUNT];

void ax_hooks_register(ax_hook_stage_t stage, ax_hook_t hook) {
    if (stage >= AX_HOOK_COUNT) return;
    uint32_t n = g_hook_counts[stage];
    if (n >= AX_MAX_HOOKS_PER_STAGE) return;
    g_hooks[stage][n] = hook;
    g_hook_counts[stage] = n + 1;
}

void ax_hooks_run(ax_hook_stage_t stage, void *ctx) {
    if (stage >= AX_HOOK_COUNT) return;
    uint32_t n = g_hook_counts[stage];
    for (uint32_t i = 0; i < n; i++) {
        if (g_hooks[stage][i].fn) {
            g_hooks[stage][i].fn(ctx);
        }
    }
}
