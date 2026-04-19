#include <axion/runtime/qm.h>
#include "axion/telemetry.h"

static axion_qm_policy_t g_policy;
static axion_qm_state_t g_state;

static int str_eq(const char *a, const char *b) {
    if (!a || !b) return 0;
    while (*a && *b) {
        if (*a != *b) return 0;
        a++;
        b++;
    }
    return (*a == 0 && *b == 0) ? 1 : 0;
}

static axion_qm_policy_t normalize_policy(axion_qm_policy_t p) {
    if (p.strict_forward_only != 0) p.strict_forward_only = 1;
    if (p.allow_recovery_anytime != 0) p.allow_recovery_anytime = 1;
    if (p.min_transition_level > 3) p.min_transition_level = 3;
    if (p.min_policy_write_level > 3) p.min_policy_write_level = 3;
    return p;
}

static int parse_phase(const char *state, axion_qm_phase_t *out) {
    if (!state || !out) return 0;
    if (str_eq(state, "cold_boot")) { *out = AXION_QM_PHASE_COLD_BOOT; return 1; }
    if (str_eq(state, "secure_init")) { *out = AXION_QM_PHASE_SECURE_INIT; return 1; }
    if (str_eq(state, "runtime_ready")) { *out = AXION_QM_PHASE_RUNTIME_READY; return 1; }
    if (str_eq(state, "degraded")) { *out = AXION_QM_PHASE_DEGRADED; return 1; }
    if (str_eq(state, "recovery")) { *out = AXION_QM_PHASE_RECOVERY; return 1; }
    return 0;
}

void axion_qm_init(void) {
    g_policy = normalize_policy((axion_qm_policy_t){
        .strict_forward_only = 1,
        .allow_recovery_anytime = 1,
        .min_transition_level = 1,
        .min_policy_write_level = 2,
    });
    g_state.initialized = 1;
    g_state.phase = AXION_QM_PHASE_COLD_BOOT;
    g_state.policy_epoch = 1;
    g_state.transitions_total = 0;
    g_state.transitions_denied = 0;
    g_state.transitions_recovery = 0;
    g_state.last_reason = AXION_QM_REASON_ALLOW;
    g_state.last_target = AXION_QM_PHASE_COLD_BOOT;
    g_state.last_policy_epoch = g_state.policy_epoch;
    ax_trace(AX_EVT_RUNTIME_QM_INIT, g_state.phase, g_state.policy_epoch, g_policy.strict_forward_only);
}

int axion_qm_set_policy_checked(axion_qm_policy_t policy, uint64_t actor_level) {
    if (!g_state.initialized) axion_qm_init();
    if (actor_level < g_policy.min_policy_write_level) {
        g_state.last_reason = AXION_QM_REASON_DENY_POLICY_LEVEL;
        ax_trace(AX_EVT_RUNTIME_QM_POLICY, 0, actor_level, g_policy.min_policy_write_level);
        return 0;
    }
    g_policy = normalize_policy(policy);
    g_state.policy_epoch++;
    g_state.last_policy_epoch = g_state.policy_epoch;
    g_state.last_reason = AXION_QM_REASON_ALLOW;
    ax_trace(AX_EVT_RUNTIME_QM_POLICY, 1, g_state.policy_epoch, g_policy.strict_forward_only);
    return 1;
}

axion_qm_policy_t axion_qm_get_policy(void) {
    return g_policy;
}

int axion_qm_transition(const char *state) {
    axion_qm_phase_t target = AXION_QM_PHASE_COLD_BOOT;
    if (!parse_phase(state, &target)) {
        if (g_state.initialized) {
            g_state.transitions_denied++;
            g_state.last_reason = AXION_QM_REASON_DENY_BAD_TARGET;
            ax_trace(AX_EVT_RUNTIME_QM_TRANSITION, 0, AXION_QM_REASON_DENY_BAD_TARGET, 0);
        }
        return 0;
    }
    return axion_qm_transition_ex(target, 1);
}

int axion_qm_transition_ex(axion_qm_phase_t target, uint64_t requested_level) {
    if (!g_state.initialized) {
        g_state.last_reason = AXION_QM_REASON_DENY_NOT_INITIALIZED;
        return 0;
    }
    if (requested_level < g_policy.min_transition_level) {
        g_state.transitions_denied++;
        g_state.last_reason = AXION_QM_REASON_DENY_POLICY_LEVEL;
        ax_trace(AX_EVT_RUNTIME_QM_TRANSITION, 0, AXION_QM_REASON_DENY_POLICY_LEVEL, requested_level);
        return 0;
    }

    axion_qm_phase_t from = g_state.phase;
    int allowed = 0;
    if (target == AXION_QM_PHASE_RECOVERY && g_policy.allow_recovery_anytime) {
        allowed = 1;
    } else if (!g_policy.strict_forward_only) {
        allowed = 1;
    } else {
        if (from == AXION_QM_PHASE_COLD_BOOT && target == AXION_QM_PHASE_SECURE_INIT) allowed = 1;
        if (from == AXION_QM_PHASE_SECURE_INIT && target == AXION_QM_PHASE_RUNTIME_READY) allowed = 1;
        if (from == AXION_QM_PHASE_RUNTIME_READY && target == AXION_QM_PHASE_DEGRADED) allowed = 1;
        if (from == AXION_QM_PHASE_DEGRADED && target == AXION_QM_PHASE_RUNTIME_READY) allowed = 1;
    }

    if (!allowed) {
        g_state.transitions_denied++;
        g_state.last_reason = AXION_QM_REASON_DENY_STRICT_PATH;
        g_state.last_target = target;
        ax_trace(AX_EVT_RUNTIME_QM_TRANSITION, 0, AXION_QM_REASON_DENY_STRICT_PATH, ((uint64_t)from << 32) | (uint64_t)target);
        return 0;
    }

    g_state.phase = target;
    g_state.transitions_total++;
    if (target == AXION_QM_PHASE_RECOVERY) g_state.transitions_recovery++;
    g_state.last_reason = AXION_QM_REASON_ALLOW;
    g_state.last_target = target;
    ax_trace(AX_EVT_RUNTIME_QM_TRANSITION, 1, (uint64_t)from, (uint64_t)target);
    return 1;
}

axion_qm_state_t axion_qm_state(void) {
    return g_state;
}

