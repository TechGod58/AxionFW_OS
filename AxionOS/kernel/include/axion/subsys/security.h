#pragma once
#include <stdint.h>

typedef enum {
    AX_SEC_ALLOW = 0,
    AX_SEC_DENY_DEFAULT = 1,
    AX_SEC_DENY_RULE_MISSING = 2,
    AX_SEC_DENY_CAP_MASK = 3,
    AX_SEC_DENY_LEVEL_RANGE = 4,
    AX_SEC_DENY_POLICY_PREBOOT_AUTH = 5,
    AX_SEC_DENY_POLICY_REPAIR_MODE = 6,
    AX_SEC_DENY_POLICY_DEBUG = 7,
    AX_SEC_DENY_RULE_EFFECT = 8,
    AX_SEC_DENY_POLICY_WRITE_LEVEL = 9,
    AX_SEC_REASON_COUNT = 10,
} ax_security_reason_t;

typedef enum {
    AX_SEC_RULE_ALLOW = 0,
    AX_SEC_RULE_DENY = 1,
} ax_security_rule_effect_t;

typedef enum {
    AX_SEC_MATCH_EXACT = 0,
    AX_SEC_MATCH_PREFIX = 1,
} ax_security_match_t;

typedef struct {
    uint64_t default_allow;
    uint64_t strict_action_allowlist;
    uint64_t require_preboot_auth_level2_plus;
    uint64_t deny_repair_mode_level3_plus;
    uint64_t deny_debug_without_preboot_auth;
    uint64_t max_rules;
    uint64_t min_policy_write_level;
} ax_security_policy_t;

typedef struct {
    uint64_t allow;
    ax_security_reason_t reason;
    const char *action;
    uint64_t required_caps0_mask;
    uint64_t requested_level;
    int64_t matched_rule_index;
    ax_security_rule_effect_t matched_rule_effect;
    uint64_t policy_epoch;
} ax_security_decision_t;

typedef struct {
    uint64_t total;
    uint64_t passed;
    uint64_t failed;
} ax_security_selftest_result_t;

typedef struct {
    uint64_t cycles_total;
    uint64_t actions_checked;
    uint64_t actions_unexpected;
    uint64_t network_checked;
    uint64_t network_unexpected;
    uint64_t precedence_total;
    uint64_t precedence_failed;
    uint64_t last_ok;
} ax_security_stress_state_t;

typedef enum {
    AX_NET_GUARD_ALLOW = 0,
    AX_NET_GUARD_DENY_DEFAULT = 1,
    AX_NET_GUARD_DENY_RULE_EFFECT = 2,
    AX_NET_GUARD_DENY_BAD_INPUT = 3,
} ax_net_guard_reason_t;

typedef enum {
    AX_NET_GUARD_RULE_ALLOW = 0,
    AX_NET_GUARD_RULE_DENY = 1,
} ax_net_guard_rule_effect_t;

typedef struct {
    uint64_t allow;
    ax_net_guard_reason_t reason;
    uint64_t app_tag;
    uint64_t protocol;
    uint64_t remote_port;
    uint64_t remote_tag;
    int64_t matched_rule_index;
    ax_net_guard_rule_effect_t matched_rule_effect;
    uint64_t policy_epoch;
} ax_net_guard_decision_t;

typedef struct {
    uint64_t total;
    uint64_t allowed;
    uint64_t denied;
    uint64_t updates;
    uint64_t update_denied;
    uint64_t policy_epoch;
} ax_net_guard_stats_t;

void ax_security_init(uint64_t caps0);
void ax_security_set_policy(ax_security_policy_t policy);
int ax_security_set_policy_checked(ax_security_policy_t policy, uint64_t actor_level);
ax_security_policy_t ax_security_get_policy(void);
void ax_security_set_caps0(uint64_t caps0);
uint64_t ax_security_caps0(void);
int ax_security_register_rule(const char *action, uint64_t required_caps0_mask, uint64_t min_level, uint64_t max_level);
int ax_security_register_rule_ex(
    const char *action,
    uint64_t required_caps0_mask,
    uint64_t min_level,
    uint64_t max_level,
    ax_security_rule_effect_t effect,
    ax_security_match_t match,
    uint64_t actor_level
);
int ax_security_check(const char *action, uint64_t required_caps0_mask, uint64_t requested_level);
ax_security_decision_t ax_security_last_decision(void);
uint64_t ax_security_decisions_total(void);
uint64_t ax_security_decisions_denied(void);
uint64_t ax_security_reason_count(ax_security_reason_t reason);
uint64_t ax_security_policy_mutations(void);
uint64_t ax_security_rule_mutations(void);
ax_security_selftest_result_t ax_security_selftest_rule_precedence(void);
void ax_security_stress_reset(void);
int ax_security_run_stress_cycle(uint64_t actor_level, uint64_t caller_caps0);
ax_security_stress_state_t ax_security_stress_state(void);
void ax_security_net_guard_reset(void);
int ax_security_net_guard_register_rule(
    uint64_t app_tag,
    uint64_t protocol,
    uint64_t remote_port,
    uint64_t remote_tag,
    ax_net_guard_rule_effect_t effect,
    uint64_t actor_level
);
int ax_security_net_guard_check(uint64_t app_tag, uint64_t protocol, uint64_t remote_port, uint64_t remote_tag);
ax_net_guard_decision_t ax_security_net_guard_last_decision(void);
ax_net_guard_stats_t ax_security_net_guard_stats(void);
