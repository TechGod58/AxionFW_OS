#include "axion/subsys/security.h"
#include "axion/bootinfo.h"
#include "axion/telemetry.h"

#define AX_SEC_RULE_CAP 64
#define AX_NET_GUARD_RULE_CAP 64

typedef struct {
    const char *action;
    uint64_t required_caps0_mask;
    uint64_t min_level;
    uint64_t max_level;
    ax_security_rule_effect_t effect;
    ax_security_match_t match;
    uint64_t used;
} ax_security_rule_t;

typedef struct {
    uint64_t app_tag;
    uint64_t protocol;
    uint64_t remote_port;
    uint64_t remote_tag;
    ax_net_guard_rule_effect_t effect;
    uint64_t used;
} ax_net_guard_rule_t;

typedef struct {
    uint64_t caps0;
    uint64_t decisions_total;
    uint64_t decisions_denied;
    uint64_t reason_counts[AX_SEC_REASON_COUNT];
    uint64_t policy_epoch;
    uint64_t policy_mutations;
    uint64_t policy_mutations_denied;
    uint64_t rule_mutations;
    ax_security_stress_state_t stress;
    ax_security_policy_t policy;
    ax_security_decision_t last;
    ax_security_rule_t rules[AX_SEC_RULE_CAP];
    uint64_t rule_count;
    ax_net_guard_rule_t net_rules[AX_NET_GUARD_RULE_CAP];
    uint64_t net_rule_count;
    ax_net_guard_decision_t net_last;
    ax_net_guard_stats_t net_stats;
} ax_security_state_t;

static ax_security_state_t g_sec;

static int str_eq(const char *a, const char *b) {
    if (!a || !b) return 0;
    while (*a && *b) {
        if (*a != *b) return 0;
        a++;
        b++;
    }
    return (*a == 0 && *b == 0) ? 1 : 0;
}

static uint64_t str_len(const char *s) {
    uint64_t n = 0;
    if (!s) return 0;
    while (*s) {
        n++;
        s++;
    }
    return n;
}

static int str_starts_with(const char *s, const char *prefix) {
    if (!s || !prefix) return 0;
    while (*prefix) {
        if (*s != *prefix) return 0;
        s++;
        prefix++;
    }
    return 1;
}

static int find_rule_exact(const char *action) {
    if (!action) return -1;
    for (uint64_t i = 0; i < g_sec.rule_count; i++) {
        if (g_sec.rules[i].used && str_eq(g_sec.rules[i].action, action)) return (int)i;
    }
    return -1;
}

static int find_best_rule(const char *action) {
    int best = -1;
    uint64_t best_score = 0;
    if (!action) return -1;
    for (uint64_t i = 0; i < g_sec.rule_count; i++) {
        if (!g_sec.rules[i].used) continue;
        uint64_t score = 0;
        if (g_sec.rules[i].match == AX_SEC_MATCH_EXACT && str_eq(g_sec.rules[i].action, action)) {
            score = 2000 + str_len(g_sec.rules[i].action);
        } else if (g_sec.rules[i].match == AX_SEC_MATCH_PREFIX && str_starts_with(action, g_sec.rules[i].action)) {
            score = 1000 + str_len(g_sec.rules[i].action);
        }
        if (score > best_score) {
            best = (int)i;
            best_score = score;
        }
    }
    return best;
}

static uint64_t net_guard_rule_score(const ax_net_guard_rule_t *r, uint64_t app_tag, uint64_t protocol, uint64_t remote_port, uint64_t remote_tag) {
    uint64_t score = 0;
    if (!r || !r->used) return 0;
    if (r->app_tag != 0) {
        if (r->app_tag != app_tag) return 0;
        score += 1000;
    }
    if (r->protocol != 0) {
        if (r->protocol != protocol) return 0;
        score += 100;
    }
    if (r->remote_port != 0) {
        if (r->remote_port != remote_port) return 0;
        score += 40;
    }
    if (r->remote_tag != 0) {
        if (r->remote_tag != remote_tag) return 0;
        score += 20;
    }
    return score;
}

static int find_best_net_rule(uint64_t app_tag, uint64_t protocol, uint64_t remote_port, uint64_t remote_tag) {
    int best = -1;
    uint64_t best_score = 0;
    uint64_t best_deny = 0;
    for (uint64_t i = 0; i < g_sec.net_rule_count; i++) {
        ax_net_guard_rule_t *r = &g_sec.net_rules[i];
        uint64_t score = net_guard_rule_score(r, app_tag, protocol, remote_port, remote_tag);
        if (score == 0) continue;
        uint64_t deny_rank = (r->effect == AX_NET_GUARD_RULE_DENY) ? 1 : 0;
        if (best < 0 || score > best_score || (score == best_score && deny_rank > best_deny)) {
            best = (int)i;
            best_score = score;
            best_deny = deny_rank;
        }
    }
    return best;
}

static ax_security_policy_t normalize_policy(ax_security_policy_t policy) {
    if (policy.max_rules == 0 || policy.max_rules > AX_SEC_RULE_CAP) policy.max_rules = AX_SEC_RULE_CAP;
    if (policy.default_allow != 0) policy.default_allow = 1;
    if (policy.strict_action_allowlist != 0) policy.strict_action_allowlist = 1;
    if (policy.require_preboot_auth_level2_plus != 0) policy.require_preboot_auth_level2_plus = 1;
    if (policy.deny_repair_mode_level3_plus != 0) policy.deny_repair_mode_level3_plus = 1;
    if (policy.deny_debug_without_preboot_auth != 0) policy.deny_debug_without_preboot_auth = 1;
    if (policy.min_policy_write_level > 3) policy.min_policy_write_level = 3;
    return policy;
}

int ax_security_set_policy_checked(ax_security_policy_t policy, uint64_t actor_level) {
    ax_security_policy_t normalized = normalize_policy(policy);
    if (g_sec.policy_epoch > 0 && actor_level < g_sec.policy.min_policy_write_level) {
        g_sec.policy_mutations_denied++;
        ax_trace(AX_EVT_SECURITY_POLICY_DENY, actor_level, g_sec.policy.min_policy_write_level, g_sec.policy_epoch);
        return 0;
    }
    g_sec.policy = normalized;
    g_sec.policy_epoch++;
    g_sec.policy_mutations++;
    ax_trace(AX_EVT_SECURITY_POLICY_UPDATE, actor_level, g_sec.policy.min_policy_write_level, g_sec.policy_epoch);
    return 1;
}

void ax_security_set_policy(ax_security_policy_t policy) {
    (void)ax_security_set_policy_checked(policy, (uint64_t)-1);
}

ax_security_policy_t ax_security_get_policy(void) {
    return g_sec.policy;
}

void ax_security_set_caps0(uint64_t caps0) {
    g_sec.caps0 = caps0;
    ax_trace(AX_EVT_SECURITY_POLICY_UPDATE, caps0, g_sec.policy_epoch, 0);
}

uint64_t ax_security_caps0(void) {
    return g_sec.caps0;
}

int ax_security_register_rule_ex(
    const char *action,
    uint64_t required_caps0_mask,
    uint64_t min_level,
    uint64_t max_level,
    ax_security_rule_effect_t effect,
    ax_security_match_t match,
    uint64_t actor_level
) {
    if (!action) return 0;
    if (min_level > max_level) return 0;
    if (effect != AX_SEC_RULE_ALLOW && effect != AX_SEC_RULE_DENY) return 0;
    if (match != AX_SEC_MATCH_EXACT && match != AX_SEC_MATCH_PREFIX) return 0;
    if (g_sec.policy_epoch > 0 && actor_level < g_sec.policy.min_policy_write_level) return 0;

    int idx = find_rule_exact(action);
    if (idx >= 0) {
        g_sec.rules[idx].required_caps0_mask = required_caps0_mask;
        g_sec.rules[idx].min_level = min_level;
        g_sec.rules[idx].max_level = max_level;
        g_sec.rules[idx].effect = effect;
        g_sec.rules[idx].match = match;
        g_sec.rules[idx].used = 1;
        g_sec.rule_mutations++;
        ax_trace(AX_EVT_SECURITY_RULE_UPDATE, (uint64_t)idx, required_caps0_mask, effect);
        return 1;
    }

    if (g_sec.rule_count >= g_sec.policy.max_rules) return 0;
    ax_security_rule_t *r = &g_sec.rules[g_sec.rule_count++];
    r->action = action;
    r->required_caps0_mask = required_caps0_mask;
    r->min_level = min_level;
    r->max_level = max_level;
    r->effect = effect;
    r->match = match;
    r->used = 1;
    g_sec.rule_mutations++;
    ax_trace(AX_EVT_SECURITY_RULE_UPDATE, g_sec.rule_count - 1, required_caps0_mask, effect);
    return 1;
}

int ax_security_register_rule(const char *action, uint64_t required_caps0_mask, uint64_t min_level, uint64_t max_level) {
    return ax_security_register_rule_ex(
        action,
        required_caps0_mask,
        min_level,
        max_level,
        AX_SEC_RULE_ALLOW,
        AX_SEC_MATCH_EXACT,
        (uint64_t)-1
    );
}

void ax_security_init(uint64_t caps0) {
    g_sec.caps0 = caps0;
    g_sec.decisions_total = 0;
    g_sec.decisions_denied = 0;
    for (int i = 0; i < AX_SEC_REASON_COUNT; i++) g_sec.reason_counts[i] = 0;
    g_sec.policy_epoch = 0;
    g_sec.policy_mutations = 0;
    g_sec.policy_mutations_denied = 0;
    g_sec.rule_mutations = 0;
    ax_security_stress_reset();
    g_sec.rule_count = 0;
    for (uint64_t i = 0; i < AX_SEC_RULE_CAP; i++) g_sec.rules[i].used = 0;
    g_sec.net_rule_count = 0;
    for (uint64_t i = 0; i < AX_NET_GUARD_RULE_CAP; i++) g_sec.net_rules[i].used = 0;
    g_sec.net_last = (ax_net_guard_decision_t){
        .allow = 0,
        .reason = AX_NET_GUARD_DENY_DEFAULT,
        .app_tag = 0,
        .protocol = 0,
        .remote_port = 0,
        .remote_tag = 0,
        .matched_rule_index = -1,
        .matched_rule_effect = AX_NET_GUARD_RULE_DENY,
        .policy_epoch = 0,
    };
    g_sec.net_stats = (ax_net_guard_stats_t){
        .total = 0,
        .allowed = 0,
        .denied = 0,
        .updates = 0,
        .update_denied = 0,
        .policy_epoch = 0,
    };
    g_sec.last = (ax_security_decision_t){
        .allow = 1,
        .reason = AX_SEC_ALLOW,
        .action = "init",
        .required_caps0_mask = 0,
        .requested_level = 0,
        .matched_rule_index = -1,
        .matched_rule_effect = AX_SEC_RULE_ALLOW,
        .policy_epoch = 0,
    };

    ax_security_set_policy((ax_security_policy_t){
        .default_allow = 0,
        .strict_action_allowlist = 1,
        .require_preboot_auth_level2_plus = 1,
        .deny_repair_mode_level3_plus = 1,
        .deny_debug_without_preboot_auth = 1,
        .max_rules = AX_SEC_RULE_CAP,
        .min_policy_write_level = 2,
    });

    // Baseline decision model rules; expanded by higher layers as needed.
    ax_security_register_rule_ex("vm_launch", 0, 0, 2, AX_SEC_RULE_ALLOW, AX_SEC_MATCH_EXACT, (uint64_t)-1);
    ax_security_register_rule_ex("enable_kernel_debug", AX_CAP0_PREBOOT_AUTH, 3, 3, AX_SEC_RULE_ALLOW, AX_SEC_MATCH_EXACT, (uint64_t)-1);
    ax_security_register_rule_ex("firmware_update", AX_CAP0_PREBOOT_AUTH, 2, 3, AX_SEC_RULE_ALLOW, AX_SEC_MATCH_EXACT, (uint64_t)-1);
    ax_security_register_rule_ex("device_attach", 0, 1, 2, AX_SEC_RULE_ALLOW, AX_SEC_MATCH_EXACT, (uint64_t)-1);
    ax_security_register_rule_ex("network_egress_open", 0, 1, 3, AX_SEC_RULE_ALLOW, AX_SEC_MATCH_EXACT, (uint64_t)-1);
    ax_security_register_rule_ex("kernel_mem_write", AX_CAP0_PREBOOT_AUTH, 3, 3, AX_SEC_RULE_DENY, AX_SEC_MATCH_PREFIX, (uint64_t)-1);

    ax_trace(AX_EVT_SECURITY_INIT, caps0, g_sec.policy.strict_action_allowlist, g_sec.rule_count);
}

int ax_security_check(const char *action, uint64_t required_caps0_mask, uint64_t requested_level) {
    ax_security_reason_t reason = g_sec.policy.default_allow ? AX_SEC_ALLOW : AX_SEC_DENY_DEFAULT;
    uint64_t allow = g_sec.policy.default_allow ? 1 : 0;

    int idx = find_best_rule(action);
    uint64_t rule_required = required_caps0_mask;
    uint64_t rule_min = 0;
    uint64_t rule_max = requested_level;
    ax_security_rule_effect_t rule_effect = AX_SEC_RULE_ALLOW;

    if (idx < 0) {
        if (g_sec.policy.strict_action_allowlist) {
            allow = 0;
            reason = AX_SEC_DENY_RULE_MISSING;
        }
    } else {
        rule_required |= g_sec.rules[idx].required_caps0_mask;
        rule_min = g_sec.rules[idx].min_level;
        rule_max = g_sec.rules[idx].max_level;
        rule_effect = g_sec.rules[idx].effect;
        if (requested_level < rule_min || requested_level > rule_max) {
            allow = 0;
            reason = AX_SEC_DENY_LEVEL_RANGE;
        } else if (rule_effect == AX_SEC_RULE_DENY) {
            allow = 0;
            reason = AX_SEC_DENY_RULE_EFFECT;
        } else {
            allow = 1;
            reason = AX_SEC_ALLOW;
        }
    }

    if (allow && rule_required != 0 && ((g_sec.caps0 & rule_required) != rule_required)) {
        allow = 0;
        reason = AX_SEC_DENY_CAP_MASK;
    }
    if (allow && g_sec.policy.require_preboot_auth_level2_plus && requested_level >= 2
        && ((g_sec.caps0 & AX_CAP0_PREBOOT_AUTH) == 0)) {
        allow = 0;
        reason = AX_SEC_DENY_POLICY_PREBOOT_AUTH;
    }
    if (allow && g_sec.policy.deny_repair_mode_level3_plus && requested_level >= 3
        && ((g_sec.caps0 & AX_CAP0_REPAIR_MODE) != 0)) {
        allow = 0;
        reason = AX_SEC_DENY_POLICY_REPAIR_MODE;
    }
    if (allow && g_sec.policy.deny_debug_without_preboot_auth && str_eq(action, "enable_kernel_debug")
        && ((g_sec.caps0 & AX_CAP0_PREBOOT_AUTH) == 0)) {
        allow = 0;
        reason = AX_SEC_DENY_POLICY_DEBUG;
    }

    g_sec.decisions_total++;
    if (!allow) g_sec.decisions_denied++;
    if ((uint64_t)reason < AX_SEC_REASON_COUNT) g_sec.reason_counts[(uint64_t)reason]++;
    g_sec.last = (ax_security_decision_t){
        .allow = allow,
        .reason = reason,
        .action = action,
        .required_caps0_mask = rule_required,
        .requested_level = requested_level,
        .matched_rule_index = idx,
        .matched_rule_effect = rule_effect,
        .policy_epoch = g_sec.policy_epoch,
    };
    ax_trace(AX_EVT_SECURITY_DECISION, allow, (uint64_t)reason, idx < 0 ? (uint64_t)-1 : (uint64_t)idx);
    return (int)allow;
}

ax_security_decision_t ax_security_last_decision(void) {
    return g_sec.last;
}

uint64_t ax_security_decisions_total(void) {
    return g_sec.decisions_total;
}

uint64_t ax_security_decisions_denied(void) {
    return g_sec.decisions_denied;
}

uint64_t ax_security_reason_count(ax_security_reason_t reason) {
    if ((uint64_t)reason >= AX_SEC_REASON_COUNT) return 0;
    return g_sec.reason_counts[(uint64_t)reason];
}

uint64_t ax_security_policy_mutations(void) {
    return g_sec.policy_mutations;
}

uint64_t ax_security_rule_mutations(void) {
    return g_sec.rule_mutations;
}

void ax_security_stress_reset(void) {
    g_sec.stress.cycles_total = 0;
    g_sec.stress.actions_checked = 0;
    g_sec.stress.actions_unexpected = 0;
    g_sec.stress.network_checked = 0;
    g_sec.stress.network_unexpected = 0;
    g_sec.stress.precedence_total = 0;
    g_sec.stress.precedence_failed = 0;
    g_sec.stress.last_ok = 0;
}

int ax_security_run_stress_cycle(uint64_t actor_level, uint64_t caller_caps0) {
    int ok = 1;
    uint64_t prior_caps0 = g_sec.caps0;
    uint64_t effective_caps0 = prior_caps0 | caller_caps0;
    ax_security_selftest_result_t selftest;

    g_sec.stress.cycles_total++;
    ax_security_set_caps0(effective_caps0);

    if (!ax_security_register_rule_ex("scheduler_policy_write", AX_CAP0_PREBOOT_AUTH, 3, 3, AX_SEC_RULE_ALLOW, AX_SEC_MATCH_EXACT, actor_level)) ok = 0;
    if (!ax_security_register_rule_ex("scheduler_tune", AX_CAP0_PREBOOT_AUTH, 2, 3, AX_SEC_RULE_ALLOW, AX_SEC_MATCH_PREFIX, actor_level)) ok = 0;
    if (!ax_security_register_rule_ex("scheduler_tune/unsafe_overclock", AX_CAP0_PREBOOT_AUTH, 2, 3, AX_SEC_RULE_DENY, AX_SEC_MATCH_EXACT, actor_level)) ok = 0;
    if (!ax_security_net_guard_register_rule(0x1001, 6, 443, 0xA100, AX_NET_GUARD_RULE_ALLOW, actor_level)) ok = 0;
    if (!ax_security_net_guard_register_rule(0x1001, 6, 443, 0xDEAD, AX_NET_GUARD_RULE_DENY, actor_level)) ok = 0;

    g_sec.stress.actions_checked++;
    if (!ax_security_check("scheduler_policy_write", AX_CAP0_PREBOOT_AUTH, 3)) {
        g_sec.stress.actions_unexpected++;
        ok = 0;
    }

    g_sec.stress.actions_checked++;
    if (!ax_security_check("scheduler_tune/foreground_boost", AX_CAP0_PREBOOT_AUTH, 2)) {
        g_sec.stress.actions_unexpected++;
        ok = 0;
    }

    g_sec.stress.actions_checked++;
    if (ax_security_check("scheduler_tune/unsafe_overclock", AX_CAP0_PREBOOT_AUTH, 2)) {
        g_sec.stress.actions_unexpected++;
        ok = 0;
    }

    g_sec.stress.actions_checked++;
    if (ax_security_check("stress/unknown_action", 0, 1)) {
        g_sec.stress.actions_unexpected++;
        ok = 0;
    }

    g_sec.stress.network_checked++;
    if (!ax_security_net_guard_check(0x1001, 6, 443, 0xA100)) {
        g_sec.stress.network_unexpected++;
        ok = 0;
    }

    g_sec.stress.network_checked++;
    if (ax_security_net_guard_check(0x1001, 6, 443, 0xDEAD)) {
        g_sec.stress.network_unexpected++;
        ok = 0;
    }

    selftest = ax_security_selftest_rule_precedence();
    g_sec.stress.precedence_total += selftest.total;
    g_sec.stress.precedence_failed += selftest.failed;
    if (selftest.failed != 0) ok = 0;

    ax_security_set_caps0(prior_caps0);
    g_sec.stress.last_ok = ok ? 1 : 0;
    ax_trace(AX_EVT_SECURITY_STRESS, g_sec.stress.actions_checked, g_sec.stress.network_checked, g_sec.stress.precedence_failed);
    return ok;
}

ax_security_stress_state_t ax_security_stress_state(void) {
    return g_sec.stress;
}

void ax_security_net_guard_reset(void) {
    g_sec.net_rule_count = 0;
    for (uint64_t i = 0; i < AX_NET_GUARD_RULE_CAP; i++) g_sec.net_rules[i].used = 0;
    g_sec.net_stats.policy_epoch++;
    g_sec.net_stats.updates++;
    g_sec.net_last = (ax_net_guard_decision_t){
        .allow = 0,
        .reason = AX_NET_GUARD_DENY_DEFAULT,
        .app_tag = 0,
        .protocol = 0,
        .remote_port = 0,
        .remote_tag = 0,
        .matched_rule_index = -1,
        .matched_rule_effect = AX_NET_GUARD_RULE_DENY,
        .policy_epoch = g_sec.net_stats.policy_epoch,
    };
    ax_trace(AX_EVT_SECURITY_NET_GUARD_POLICY_UPDATE, g_sec.net_stats.policy_epoch, g_sec.net_rule_count, 0);
}

int ax_security_net_guard_register_rule(
    uint64_t app_tag,
    uint64_t protocol,
    uint64_t remote_port,
    uint64_t remote_tag,
    ax_net_guard_rule_effect_t effect,
    uint64_t actor_level
) {
    if (effect != AX_NET_GUARD_RULE_ALLOW && effect != AX_NET_GUARD_RULE_DENY) return 0;
    if (g_sec.policy_epoch > 0 && actor_level < g_sec.policy.min_policy_write_level) {
        g_sec.net_stats.update_denied++;
        ax_trace(AX_EVT_SECURITY_NET_GUARD_POLICY_DENY, actor_level, g_sec.policy.min_policy_write_level, g_sec.net_stats.policy_epoch);
        return 0;
    }

    for (uint64_t i = 0; i < g_sec.net_rule_count; i++) {
        ax_net_guard_rule_t *r = &g_sec.net_rules[i];
        if (!r->used) continue;
        if (r->app_tag == app_tag && r->protocol == protocol && r->remote_port == remote_port && r->remote_tag == remote_tag) {
            r->effect = effect;
            g_sec.net_stats.updates++;
            g_sec.net_stats.policy_epoch++;
            ax_trace(AX_EVT_SECURITY_NET_GUARD_POLICY_UPDATE, g_sec.net_stats.policy_epoch, i, effect);
            return 1;
        }
    }

    if (g_sec.net_rule_count >= AX_NET_GUARD_RULE_CAP) return 0;
    ax_net_guard_rule_t *r = &g_sec.net_rules[g_sec.net_rule_count++];
    r->app_tag = app_tag;
    r->protocol = protocol;
    r->remote_port = remote_port;
    r->remote_tag = remote_tag;
    r->effect = effect;
    r->used = 1;
    g_sec.net_stats.updates++;
    g_sec.net_stats.policy_epoch++;
    ax_trace(AX_EVT_SECURITY_NET_GUARD_POLICY_UPDATE, g_sec.net_stats.policy_epoch, g_sec.net_rule_count - 1, effect);
    return 1;
}

int ax_security_net_guard_check(uint64_t app_tag, uint64_t protocol, uint64_t remote_port, uint64_t remote_tag) {
    g_sec.net_stats.total++;
    if (app_tag == 0 || protocol == 0 || remote_port == 0) {
        g_sec.net_stats.denied++;
        g_sec.net_last = (ax_net_guard_decision_t){
            .allow = 0,
            .reason = AX_NET_GUARD_DENY_BAD_INPUT,
            .app_tag = app_tag,
            .protocol = protocol,
            .remote_port = remote_port,
            .remote_tag = remote_tag,
            .matched_rule_index = -1,
            .matched_rule_effect = AX_NET_GUARD_RULE_DENY,
            .policy_epoch = g_sec.net_stats.policy_epoch,
        };
        ax_trace(AX_EVT_SECURITY_NET_GUARD_DECISION, 0, AX_NET_GUARD_DENY_BAD_INPUT, 0);
        return 0;
    }

    int idx = find_best_net_rule(app_tag, protocol, remote_port, remote_tag);
    uint64_t allow = 0;
    ax_net_guard_reason_t reason = AX_NET_GUARD_DENY_DEFAULT;
    ax_net_guard_rule_effect_t matched_effect = AX_NET_GUARD_RULE_DENY;
    if (idx >= 0) {
        matched_effect = g_sec.net_rules[idx].effect;
        if (matched_effect == AX_NET_GUARD_RULE_ALLOW) {
            allow = 1;
            reason = AX_NET_GUARD_ALLOW;
        } else {
            allow = 0;
            reason = AX_NET_GUARD_DENY_RULE_EFFECT;
        }
    }

    if (allow) g_sec.net_stats.allowed++; else g_sec.net_stats.denied++;
    g_sec.net_last = (ax_net_guard_decision_t){
        .allow = allow,
        .reason = reason,
        .app_tag = app_tag,
        .protocol = protocol,
        .remote_port = remote_port,
        .remote_tag = remote_tag,
        .matched_rule_index = idx,
        .matched_rule_effect = matched_effect,
        .policy_epoch = g_sec.net_stats.policy_epoch,
    };
    ax_trace(AX_EVT_SECURITY_NET_GUARD_DECISION, allow, reason, idx < 0 ? (uint64_t)-1 : (uint64_t)idx);
    return (int)allow;
}

ax_net_guard_decision_t ax_security_net_guard_last_decision(void) {
    return g_sec.net_last;
}

ax_net_guard_stats_t ax_security_net_guard_stats(void) {
    return g_sec.net_stats;
}

ax_security_selftest_result_t ax_security_selftest_rule_precedence(void) {
    ax_security_selftest_result_t r = { .total = 0, .passed = 0, .failed = 0 };
    ax_security_decision_t d;
    int ok;

    (void)ax_security_register_rule_ex(
        "selftest/precedence/prefix_deny",
        0,
        0,
        3,
        AX_SEC_RULE_DENY,
        AX_SEC_MATCH_PREFIX,
        (uint64_t)-1
    );
    (void)ax_security_register_rule_ex(
        "selftest/precedence/prefix_deny/allow_exact",
        0,
        0,
        3,
        AX_SEC_RULE_ALLOW,
        AX_SEC_MATCH_EXACT,
        (uint64_t)-1
    );
    ok = ax_security_check("selftest/precedence/prefix_deny/allow_exact", 0, 1);
    d = ax_security_last_decision();
    r.total++;
    if (ok && d.reason == AX_SEC_ALLOW && d.matched_rule_effect == AX_SEC_RULE_ALLOW) r.passed++; else r.failed++;

    (void)ax_security_register_rule_ex(
        "selftest/precedence/prefix_allow",
        0,
        0,
        3,
        AX_SEC_RULE_ALLOW,
        AX_SEC_MATCH_PREFIX,
        (uint64_t)-1
    );
    (void)ax_security_register_rule_ex(
        "selftest/precedence/prefix_allow/deny_exact",
        0,
        0,
        3,
        AX_SEC_RULE_DENY,
        AX_SEC_MATCH_EXACT,
        (uint64_t)-1
    );
    ok = ax_security_check("selftest/precedence/prefix_allow/deny_exact", 0, 1);
    d = ax_security_last_decision();
    r.total++;
    if (!ok && d.reason == AX_SEC_DENY_RULE_EFFECT && d.matched_rule_effect == AX_SEC_RULE_DENY) r.passed++; else r.failed++;

    (void)ax_security_register_rule_ex(
        "selftest/precedence/path",
        0,
        0,
        3,
        AX_SEC_RULE_DENY,
        AX_SEC_MATCH_PREFIX,
        (uint64_t)-1
    );
    (void)ax_security_register_rule_ex(
        "selftest/precedence/path/allow",
        0,
        0,
        3,
        AX_SEC_RULE_ALLOW,
        AX_SEC_MATCH_PREFIX,
        (uint64_t)-1
    );
    ok = ax_security_check("selftest/precedence/path/allow/item", 0, 1);
    d = ax_security_last_decision();
    r.total++;
    if (ok && d.reason == AX_SEC_ALLOW && d.matched_rule_effect == AX_SEC_RULE_ALLOW) r.passed++; else r.failed++;

    (void)ax_security_register_rule_ex(
        "selftest/precedence/path2",
        0,
        0,
        3,
        AX_SEC_RULE_ALLOW,
        AX_SEC_MATCH_PREFIX,
        (uint64_t)-1
    );
    (void)ax_security_register_rule_ex(
        "selftest/precedence/path2/deny",
        0,
        0,
        3,
        AX_SEC_RULE_DENY,
        AX_SEC_MATCH_PREFIX,
        (uint64_t)-1
    );
    ok = ax_security_check("selftest/precedence/path2/deny/item", 0, 1);
    d = ax_security_last_decision();
    r.total++;
    if (!ok && d.reason == AX_SEC_DENY_RULE_EFFECT && d.matched_rule_effect == AX_SEC_RULE_DENY) r.passed++; else r.failed++;

    ok = ax_security_check("selftest/precedence/unknown", 0, 1);
    d = ax_security_last_decision();
    r.total++;
    if (!ok && d.reason == AX_SEC_DENY_RULE_MISSING) r.passed++; else r.failed++;

    ax_trace(AX_EVT_SECURITY_SELFTEST, r.passed, r.failed, r.total);
    return r;
}
