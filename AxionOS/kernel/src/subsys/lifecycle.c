#include "axion/subsys/lifecycle.h"
#include "axion/telemetry.h"

static ax_lifecycle_state_t g_life;

void ax_lifecycle_init(void) {
    g_life.initialized = 1;
    g_life.required_stage_mask = 0;
    g_life.stage_mask = 0;
    g_life.stage_ok_mask = 0;
    g_life.ownership_checks = 0;
    g_life.ownership_failed = 0;
    g_life.warnings = 0;
    g_life.health_score = 100;
    g_life.finalized = 0;
    ax_trace(AX_EVT_LIFECYCLE_INIT, g_life.health_score, 0, 0);
}

void ax_lifecycle_set_required_mask(uint64_t required_stage_mask) {
    if (!g_life.initialized) return;
    g_life.required_stage_mask = required_stage_mask;
    ax_trace(AX_EVT_LIFECYCLE_STAGE, required_stage_mask, g_life.stage_mask, g_life.stage_ok_mask);
}

void ax_lifecycle_mark_stage(uint64_t stage_bit, uint64_t ok) {
    if (!g_life.initialized || stage_bit >= 64) return;
    g_life.ownership_checks++;
    g_life.stage_mask |= (1ull << stage_bit);
    if (ok) g_life.stage_ok_mask |= (1ull << stage_bit);
    if (!ok) {
        g_life.warnings++;
        g_life.ownership_failed++;
        if (g_life.health_score >= 9) g_life.health_score -= 9;
        else g_life.health_score = 0;
    }
    ax_trace(AX_EVT_LIFECYCLE_STAGE, stage_bit, ok, g_life.stage_ok_mask);
}

void ax_lifecycle_finalize(void) {
    uint64_t missing;
    uint64_t missing_ok;
    if (!g_life.initialized) return;
    missing = g_life.required_stage_mask & ~g_life.stage_mask;
    missing_ok = g_life.required_stage_mask & ~g_life.stage_ok_mask;
    if (missing != 0) {
        g_life.warnings++;
        g_life.ownership_failed++;
        if (g_life.health_score >= 15) g_life.health_score -= 15;
        else g_life.health_score = 0;
    }
    if (missing_ok != 0) {
        g_life.warnings++;
        g_life.ownership_failed++;
        if (g_life.health_score >= 10) g_life.health_score -= 10;
        else g_life.health_score = 0;
    }
    g_life.finalized = 1;
    ax_trace(AX_EVT_LIFECYCLE_FINALIZE, g_life.stage_mask, g_life.stage_ok_mask, g_life.health_score);
    ax_trace(AX_EVT_LIFECYCLE_READY, g_life.required_stage_mask, missing_ok, ax_lifecycle_is_ready());
}

uint64_t ax_lifecycle_is_ready(void) {
    if (!g_life.initialized || !g_life.finalized) return 0;
    if (g_life.required_stage_mask == 0) return 0;
    if ((g_life.stage_ok_mask & g_life.required_stage_mask) != g_life.required_stage_mask) return 0;
    return g_life.ownership_failed == 0 ? 1 : 0;
}

ax_lifecycle_state_t ax_lifecycle_state(void) {
    return g_life;
}
