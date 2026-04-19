#include "axion/subsys/syscall.h"
#include "axion/subsys/security.h"
#include "axion/bootinfo.h"
#include "axion/telemetry.h"
#include "scheduler_internal.h"

typedef struct {
    uint64_t writer_token;
    uint64_t kernel_caps0;
    ax_syscall_policy_stats_t stats;
} ax_syscall_state_t;

static ax_syscall_state_t g_sys;

static uint64_t derive_token(uint64_t caps0) {
    uint64_t seed = 0xA58C4D3F11E27B90ull;
    uint64_t mix = seed ^ (caps0 << 1) ^ (caps0 >> 1) ^ (caps0 * 0x9E3779B97F4A7C15ull);
    return mix == 0 ? 1 : mix;
}

void ax_syscall_init(uint64_t kernel_caps0) {
    g_sys.writer_token = derive_token(kernel_caps0);
    g_sys.kernel_caps0 = kernel_caps0;
    g_sys.stats.total = 0;
    g_sys.stats.allowed = 0;
    g_sys.stats.denied_security = 0;
    g_sys.stats.denied_sched_gate = 0;
    g_sys.stats.denied_bad_input = 0;
    g_sys.stats.last_status = AX_SYSCALL_POLICY_OK;
    g_sys.stats.last_actor_level = 0;
    g_sys.stats.last_policy_epoch = 0;
    g_sys.stats.net_total = 0;
    g_sys.stats.net_allowed = 0;
    g_sys.stats.net_denied_security = 0;
    g_sys.stats.net_denied_policy = 0;
    g_sys.stats.net_denied_bad_input = 0;
    g_sys.stats.net_last_status = AX_SYSCALL_NET_GUARD_OK;

    ax_sched_internal_enable_syscall_gate(g_sys.writer_token);
    ax_trace(AX_EVT_SYSCALL_INIT, kernel_caps0, g_sys.writer_token, 0);
}

int ax_syscall_sched_policy_write(const char *action, ax_sched_policy_t policy, uint64_t actor_level, uint64_t caller_caps0) {
    g_sys.stats.total++;
    g_sys.stats.last_actor_level = actor_level;

    if (!action || action[0] == 0) {
        g_sys.stats.denied_bad_input++;
        g_sys.stats.last_status = AX_SYSCALL_POLICY_BAD_INPUT;
        ax_trace(AX_EVT_SYSCALL_SCHED_POLICY, AX_SYSCALL_POLICY_BAD_INPUT, actor_level, 0);
        return 0;
    }

    uint64_t prior_caps0 = ax_security_caps0();
    uint64_t effective_caps0 = g_sys.kernel_caps0 | caller_caps0;
    ax_security_set_caps0(effective_caps0);
    int allowed = ax_security_check(action, AX_CAP0_PREBOOT_AUTH, actor_level);
    ax_security_set_caps0(prior_caps0);

    if (!allowed) {
        g_sys.stats.denied_security++;
        g_sys.stats.last_status = AX_SYSCALL_POLICY_DENY_SECURITY;
        ax_trace(AX_EVT_SYSCALL_SCHED_POLICY, AX_SYSCALL_POLICY_DENY_SECURITY, actor_level, ax_security_last_decision().reason);
        return 0;
    }

    if (!ax_sched_internal_apply_policy_syscall(policy, actor_level, g_sys.writer_token)) {
        g_sys.stats.denied_sched_gate++;
        g_sys.stats.last_status = AX_SYSCALL_POLICY_DENY_SCHED_GATE;
        ax_trace(AX_EVT_SYSCALL_SCHED_POLICY, AX_SYSCALL_POLICY_DENY_SCHED_GATE, actor_level, 0);
        return 0;
    }

    g_sys.stats.allowed++;
    g_sys.stats.last_status = AX_SYSCALL_POLICY_OK;
    g_sys.stats.last_policy_epoch = ax_sched_policy_epoch();
    ax_trace(AX_EVT_SYSCALL_SCHED_POLICY, AX_SYSCALL_POLICY_OK, actor_level, g_sys.stats.last_policy_epoch);
    return 1;
}

int ax_syscall_network_egress_open(
    uint64_t app_tag,
    uint64_t protocol,
    uint64_t remote_port,
    uint64_t remote_tag,
    uint64_t actor_level,
    uint64_t caller_caps0
) {
    g_sys.stats.net_total++;
    g_sys.stats.last_actor_level = actor_level;

    if (app_tag == 0 || protocol == 0 || remote_port == 0) {
        g_sys.stats.net_denied_bad_input++;
        g_sys.stats.net_last_status = AX_SYSCALL_NET_GUARD_BAD_INPUT;
        ax_trace(AX_EVT_SYSCALL_NET_GUARD, AX_SYSCALL_NET_GUARD_BAD_INPUT, app_tag, remote_port);
        return 0;
    }

    uint64_t prior_caps0 = ax_security_caps0();
    uint64_t effective_caps0 = g_sys.kernel_caps0 | caller_caps0;
    ax_security_set_caps0(effective_caps0);
    int allowed_by_security = ax_security_check("network_egress_open", 0, actor_level);
    ax_security_set_caps0(prior_caps0);
    if (!allowed_by_security) {
        g_sys.stats.net_denied_security++;
        g_sys.stats.net_last_status = AX_SYSCALL_NET_GUARD_DENY_SECURITY;
        ax_trace(AX_EVT_SYSCALL_NET_GUARD, AX_SYSCALL_NET_GUARD_DENY_SECURITY, actor_level, ax_security_last_decision().reason);
        return 0;
    }

    if (!ax_security_net_guard_check(app_tag, protocol, remote_port, remote_tag)) {
        g_sys.stats.net_denied_policy++;
        g_sys.stats.net_last_status = AX_SYSCALL_NET_GUARD_DENY_POLICY;
        ax_trace(AX_EVT_SYSCALL_NET_GUARD, AX_SYSCALL_NET_GUARD_DENY_POLICY, app_tag, remote_port);
        return 0;
    }

    g_sys.stats.net_allowed++;
    g_sys.stats.net_last_status = AX_SYSCALL_NET_GUARD_OK;
    ax_trace(AX_EVT_SYSCALL_NET_GUARD, AX_SYSCALL_NET_GUARD_OK, app_tag, remote_port);
    return 1;
}

ax_syscall_policy_stats_t ax_syscall_policy_stats(void) {
    return g_sys.stats;
}
