#include "axion/subsys/parallel_guard.h"
#include "axion/telemetry.h"

static ax_parallel_guard_state_t g_guard;

void ax_parallel_guard_init(uint64_t enabled, uint64_t strict_mode, uint64_t inventory_required, uint64_t inventory_ready, uint64_t handoff_ready) {
    g_guard.initialized = 1;
    g_guard.enabled = enabled ? 1 : 0;
    g_guard.strict_mode = strict_mode ? 1 : 0;
    g_guard.inventory_required = inventory_required ? 1 : 0;
    g_guard.inventory_ready = inventory_ready ? 1 : 0;
    g_guard.handoff_ready = handoff_ready ? 1 : 0;
    g_guard.allow_mask = 0;
    g_guard.deny_mask = 0;
    g_guard.decisions_total = 0;
    g_guard.decisions_allowed = 0;
    g_guard.decisions_denied = 0;
    g_guard.last_class_code = 0;
    g_guard.last_subclass = 0;
    g_guard.last_reason = AX_PCGUARD_ALLOW;
    ax_trace(AX_EVT_BUS_GUARD_INIT, enabled ? 1 : 0, strict_mode ? 1 : 0, inventory_ready ? 1 : 0);
}

void ax_parallel_guard_set_policy_masks(uint64_t allow_mask, uint64_t deny_mask) {
    g_guard.allow_mask = allow_mask;
    g_guard.deny_mask = deny_mask;
}

static uint64_t class_bit(uint64_t class_code) {
    if (class_code > 63u) return 0;
    return (uint64_t)1u << class_code;
}

uint64_t ax_parallel_guard_check_bus_device(uint64_t class_code, uint64_t subclass) {
    uint64_t reason = AX_PCGUARD_ALLOW;
    uint64_t allowed = 1;
    uint64_t bit = class_bit(class_code);

    if (!g_guard.initialized) {
        reason = AX_PCGUARD_DENY_NOT_INITIALIZED;
        allowed = 0;
    } else if (!g_guard.enabled) {
        allowed = 1;
    } else if (g_guard.strict_mode && g_guard.inventory_required && !g_guard.inventory_ready) {
        reason = AX_PCGUARD_DENY_INVENTORY_REQUIRED;
        allowed = 0;
    } else if (g_guard.strict_mode && !g_guard.handoff_ready) {
        reason = AX_PCGUARD_DENY_HANDOFF_REQUIRED;
        allowed = 0;
    } else if (bit != 0 && (g_guard.deny_mask & bit) != 0) {
        reason = AX_PCGUARD_DENY_CLASS_EXPLICIT;
        allowed = 0;
    } else if (g_guard.strict_mode && g_guard.allow_mask != 0 && (bit == 0 || (g_guard.allow_mask & bit) == 0)) {
        reason = AX_PCGUARD_DENY_CLASS_NOT_ALLOWED;
        allowed = 0;
    }

    g_guard.decisions_total++;
    if (allowed) g_guard.decisions_allowed++;
    else g_guard.decisions_denied++;
    g_guard.last_class_code = class_code;
    g_guard.last_subclass = subclass;
    g_guard.last_reason = reason;

    ax_trace(AX_EVT_BUS_GUARD_DECISION, allowed, reason, class_code);
    return allowed;
}

ax_parallel_guard_state_t ax_parallel_guard_state(void) {
    return g_guard;
}
