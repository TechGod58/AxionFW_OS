#include <axion/runtime/e_runtime.h>
#include <axion/runtime/ig.h>
#include <axion/runtime/ledger.h>
#include <axion/runtime/qecc.h>
#include "axion/telemetry.h"

static axion_e_policy_t g_policy;
static axion_e_state_t g_state;

static uint64_t str_len(const char *s) {
    uint64_t n = 0;
    if (!s) return 0;
    while (*s) {
        n++;
        s++;
    }
    return n;
}

static axion_e_policy_t normalize_policy(axion_e_policy_t p) {
    if (p.enforce_ig != 0) p.enforce_ig = 1;
    if (p.require_ledger != 0) p.require_ledger = 1;
    if (p.require_qecc != 0) p.require_qecc = 1;
    if (p.sandbox_required_for_external != 0) p.sandbox_required_for_external = 1;
    if (p.min_policy_write_level > 3) p.min_policy_write_level = 3;
    if (p.max_task_name_len == 0) p.max_task_name_len = 96;
    if (p.max_task_name_len > 512) p.max_task_name_len = 512;
    return p;
}

void axion_e_init(void) {
    g_state.initialized = 1;
    g_state.policy_epoch = 0;
    g_state.total_exec = 0;
    g_state.denied_exec = 0;
    g_state.installer_exec = 0;
    g_state.module_attach_exec = 0;
    g_state.external_exec = 0;
    g_state.sandbox_exec = 0;
    g_state.last_reason = AXION_E_REASON_ALLOW;
    g_state.last_policy_epoch = 0;

    g_policy = normalize_policy((axion_e_policy_t){
        .enforce_ig = 1,
        .require_ledger = 1,
        .require_qecc = 1,
        .sandbox_required_for_external = 1,
        .min_policy_write_level = 2,
        .max_task_name_len = 128,
    });
    g_state.policy_epoch = 1;
    g_state.last_policy_epoch = g_state.policy_epoch;
    ax_trace(AX_EVT_RUNTIME_E_INIT, g_state.policy_epoch, g_policy.enforce_ig, g_policy.sandbox_required_for_external);
}

int axion_e_set_policy_checked(axion_e_policy_t policy, uint64_t actor_level) {
    if (!g_state.initialized) axion_e_init();
    if (actor_level < g_policy.min_policy_write_level) {
        g_state.last_reason = AXION_E_REASON_DENY_POLICY_LEVEL;
        ax_trace(AX_EVT_RUNTIME_E_POLICY, 0, actor_level, g_policy.min_policy_write_level);
        return 0;
    }
    g_policy = normalize_policy(policy);
    g_state.policy_epoch++;
    g_state.last_policy_epoch = g_state.policy_epoch;
    g_state.last_reason = AXION_E_REASON_ALLOW;
    ax_trace(AX_EVT_RUNTIME_E_POLICY, 1, g_state.policy_epoch, g_policy.max_task_name_len);
    return 1;
}

axion_e_policy_t axion_e_get_policy(void) {
    return g_policy;
}

int axion_e_execute(const char *task) {
    return axion_e_execute_ex(task, AXION_E_TASK_USER_APP, 1, 0, 1);
}

int axion_e_execute_ex(
    const char *task,
    axion_e_task_class_t task_class,
    uint64_t requested_level,
    uint64_t is_external,
    uint64_t from_sandbox
) {
    if (!g_state.initialized) {
        g_state.last_reason = AXION_E_REASON_DENY_NOT_INITIALIZED;
        return 0;
    }

    g_state.total_exec++;
    if (task_class == AXION_E_TASK_INSTALLER) g_state.installer_exec++;
    if (task_class == AXION_E_TASK_MODULE_ATTACH) g_state.module_attach_exec++;
    if (is_external) g_state.external_exec++;
    if (from_sandbox) g_state.sandbox_exec++;

    if (!task || task[0] == 0 || str_len(task) > g_policy.max_task_name_len) {
        g_state.denied_exec++;
        g_state.last_reason = AXION_E_REASON_DENY_INVALID_TASK;
        ax_trace(AX_EVT_RUNTIME_E_EXEC, 0, AXION_E_REASON_DENY_INVALID_TASK, g_state.total_exec);
        return 0;
    }
    if (is_external && g_policy.sandbox_required_for_external && !from_sandbox) {
        g_state.denied_exec++;
        g_state.last_reason = AXION_E_REASON_DENY_SANDBOX_REQUIRED;
        ax_trace(AX_EVT_RUNTIME_E_EXEC, 0, AXION_E_REASON_DENY_SANDBOX_REQUIRED, g_state.total_exec);
        return 0;
    }
    if (requested_level >= 3 && task_class == AXION_E_TASK_INSTALLER && !from_sandbox) {
        g_state.denied_exec++;
        g_state.last_reason = AXION_E_REASON_DENY_SANDBOX_REQUIRED;
        ax_trace(AX_EVT_RUNTIME_E_EXEC, 0, AXION_E_REASON_DENY_SANDBOX_REQUIRED, requested_level);
        return 0;
    }

    if (g_policy.enforce_ig && !axion_ig_validate(task)) {
        g_state.denied_exec++;
        g_state.last_reason = AXION_E_REASON_DENY_IG;
        ax_trace(AX_EVT_RUNTIME_E_EXEC, 0, AXION_E_REASON_DENY_IG, g_state.total_exec);
        return 0;
    }

    if (g_policy.require_ledger) axion_ledger_commit(task);
    if (g_policy.require_qecc) axion_qecc_attach(task);
    g_state.last_reason = AXION_E_REASON_ALLOW;
    ax_trace(AX_EVT_RUNTIME_E_EXEC, 1, (uint64_t)task_class, requested_level);
    return 1;
}

axion_e_state_t axion_e_state(void) {
    return g_state;
}

