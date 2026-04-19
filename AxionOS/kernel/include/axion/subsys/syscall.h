#pragma once
#include <stdint.h>
#include "axion/subsys/scheduler.h"

typedef enum {
    AX_SYSCALL_POLICY_OK = 0,
    AX_SYSCALL_POLICY_BAD_INPUT = 1,
    AX_SYSCALL_POLICY_DENY_SECURITY = 2,
    AX_SYSCALL_POLICY_DENY_SCHED_GATE = 3,
    AX_SYSCALL_NET_GUARD_OK = 10,
    AX_SYSCALL_NET_GUARD_BAD_INPUT = 11,
    AX_SYSCALL_NET_GUARD_DENY_SECURITY = 12,
    AX_SYSCALL_NET_GUARD_DENY_POLICY = 13,
} ax_syscall_policy_status_t;

typedef struct {
    uint64_t total;
    uint64_t allowed;
    uint64_t denied_security;
    uint64_t denied_sched_gate;
    uint64_t denied_bad_input;
    ax_syscall_policy_status_t last_status;
    uint64_t last_actor_level;
    uint64_t last_policy_epoch;
    uint64_t net_total;
    uint64_t net_allowed;
    uint64_t net_denied_security;
    uint64_t net_denied_policy;
    uint64_t net_denied_bad_input;
    ax_syscall_policy_status_t net_last_status;
} ax_syscall_policy_stats_t;

void ax_syscall_init(uint64_t kernel_caps0);
int ax_syscall_sched_policy_write(const char *action, ax_sched_policy_t policy, uint64_t actor_level, uint64_t caller_caps0);
int ax_syscall_network_egress_open(uint64_t app_tag, uint64_t protocol, uint64_t remote_port, uint64_t remote_tag, uint64_t actor_level, uint64_t caller_caps0);
ax_syscall_policy_stats_t ax_syscall_policy_stats(void);
