#include "axion/subsys/scheduler.h"
#include "axion/telemetry.h"
#include "scheduler_internal.h"

#define AX_SCHED_Q_CAP 64

typedef struct {
    uint64_t tid;
    uint64_t priority;
    ax_sched_class_t class_id;
    uint64_t quantum;
    uint64_t inserted_tick;
} ax_sched_node_t;

static ax_sched_node_t g_q[AX_SCHED_Q_CAP];
static uint64_t g_count = 0;
static uint64_t g_tick = 0;
static ax_sched_stats_t g_stats;
static ax_sched_stress_state_t g_stress;
static ax_sched_policy_t g_policy;
static uint64_t g_policy_epoch = 0;
static uint64_t g_rr_credit[AX_SCHED_CLASS_COUNT];
static uint64_t g_rr_cursor = 0;
static uint64_t g_syscall_gate_token = 0;
static uint64_t g_syscall_gate_ready = 0;

static uint64_t class_bonus(ax_sched_class_t class_id) {
    switch (class_id) {
        case AX_SCHED_CLASS_REALTIME: return 3;
        case AX_SCHED_CLASS_SYSTEM: return 2;
        case AX_SCHED_CLASS_USER: return 1;
        default: return 0;
    }
}

static uint64_t class_idx(ax_sched_class_t class_id) {
    uint64_t idx = (uint64_t)class_id;
    if (idx >= AX_SCHED_CLASS_COUNT) return (uint64_t)AX_SCHED_CLASS_BACKGROUND;
    return idx;
}

static ax_sched_class_t norm_class(uint64_t class_id) {
    if (class_id >= AX_SCHED_CLASS_COUNT) return AX_SCHED_CLASS_BACKGROUND;
    return (ax_sched_class_t)class_id;
}

static uint64_t clamp_u64(uint64_t v, uint64_t lo, uint64_t hi) {
    if (v < lo) return lo;
    if (v > hi) return hi;
    return v;
}

static uint64_t max_depth(void) {
    uint64_t cap = g_policy.queue_capacity;
    if (cap == 0) cap = 1;
    if (cap > AX_SCHED_Q_CAP) cap = AX_SCHED_Q_CAP;
    return cap;
}

static uint64_t effective_score(const ax_sched_node_t *n) {
    uint64_t age = 0;
    if (g_policy.aging_interval_ticks > 0 && g_tick >= n->inserted_tick) {
        age = (g_tick - n->inserted_tick) / g_policy.aging_interval_ticks;
    }
    uint64_t age_boost = age * g_policy.aging_step;
    uint64_t base = clamp_u64(n->priority, g_policy.min_priority, g_policy.max_priority);
    uint64_t boosted = clamp_u64(base + age_boost, g_policy.min_priority, g_policy.max_priority);
    return boosted + class_bonus(n->class_id);
}

static ax_sched_policy_t normalize_policy(ax_sched_policy_t policy) {
    if (policy.mode != AX_SCHED_POLICY_PRIORITY_AGING && policy.mode != AX_SCHED_POLICY_WEIGHTED_RR) {
        policy.mode = AX_SCHED_POLICY_PRIORITY_AGING;
    }
    if (policy.queue_capacity == 0) policy.queue_capacity = 32;
    if (policy.min_priority > policy.max_priority) {
        uint64_t t = policy.min_priority;
        policy.min_priority = policy.max_priority;
        policy.max_priority = t;
    }
    if (policy.default_quantum == 0) policy.default_quantum = 1;
    if (policy.aging_interval_ticks == 0) policy.aging_interval_ticks = 1;
    for (uint64_t i = 0; i < AX_SCHED_CLASS_COUNT; i++) {
        if (policy.class_weights[i] == 0) policy.class_weights[i] = i + 1;
    }
    if (policy.min_policy_write_level > 3) policy.min_policy_write_level = 3;
    return policy;
}

static int find_tid(uint64_t tid) {
    for (uint64_t i = 0; i < g_count; i++) {
        if (g_q[i].tid == tid) return (int)i;
    }
    return -1;
}

static void rr_refill(void) {
    for (uint64_t i = 0; i < AX_SCHED_CLASS_COUNT; i++) {
        g_rr_credit[i] = g_policy.class_weights[i];
    }
}

static int rr_all_zero(void) {
    for (uint64_t i = 0; i < AX_SCHED_CLASS_COUNT; i++) {
        if (g_rr_credit[i] != 0) return 0;
    }
    return 1;
}

static uint64_t pick_best_idx_for_class(ax_sched_class_t class_id) {
    uint64_t best = (uint64_t)-1;
    uint64_t best_score = 0;
    for (uint64_t i = 0; i < g_count; i++) {
        if (g_q[i].class_id != class_id) continue;
        uint64_t score = effective_score(&g_q[i]);
        if (best == (uint64_t)-1 || score > best_score) {
            best = i;
            best_score = score;
        } else if (score == best_score && g_q[i].inserted_tick < g_q[best].inserted_tick) {
            best = i;
        }
    }
    return best;
}

static uint64_t pick_best_idx_priority(void) {
    uint64_t best_idx = 0;
    uint64_t best_score = effective_score(&g_q[0]);
    for (uint64_t i = 1; i < g_count; i++) {
        uint64_t s = effective_score(&g_q[i]);
        if (s > best_score) {
            best_score = s;
            best_idx = i;
        } else if (s == best_score && g_q[i].inserted_tick < g_q[best_idx].inserted_tick) {
            best_idx = i;
        }
    }
    return best_idx;
}

static uint64_t pick_best_idx_weighted_rr(void) {
    if (rr_all_zero()) rr_refill();
    for (uint64_t pass = 0; pass < AX_SCHED_CLASS_COUNT; pass++) {
        uint64_t cls_idx = (g_rr_cursor + pass) % AX_SCHED_CLASS_COUNT;
        if (g_rr_credit[cls_idx] == 0) continue;
        uint64_t idx = pick_best_idx_for_class((ax_sched_class_t)cls_idx);
        if (idx != (uint64_t)-1) {
            g_rr_credit[cls_idx]--;
            g_rr_cursor = (cls_idx + 1) % AX_SCHED_CLASS_COUNT;
            return idx;
        }
        g_rr_credit[cls_idx] = 0;
    }
    rr_refill();
    return pick_best_idx_priority();
}

static int apply_policy_internal(ax_sched_policy_t policy, uint64_t actor_level) {
    ax_sched_policy_t normalized = normalize_policy(policy);
    if (g_policy_epoch > 0 && actor_level < g_policy.min_policy_write_level) {
        g_stats.policy_update_denied++;
        ax_trace(AX_EVT_SCHED_POLICY_DENY, actor_level, g_policy.min_policy_write_level, g_policy_epoch);
        return 0;
    }
    g_policy = normalized;
    g_policy_epoch++;
    g_stats.policy_updates++;
    g_stats.policy_epoch = g_policy_epoch;
    rr_refill();
    ax_trace(AX_EVT_SCHED_POLICY_UPDATE, g_policy.mode, g_policy.queue_capacity, g_policy_epoch);
    return 1;
}

void ax_sched_internal_enable_syscall_gate(uint64_t token) {
    g_syscall_gate_token = token == 0 ? 1 : token;
    g_syscall_gate_ready = 1;
}

int ax_sched_internal_apply_policy_syscall(ax_sched_policy_t policy, uint64_t actor_level, uint64_t token) {
    if (!g_syscall_gate_ready || token != g_syscall_gate_token) {
        g_stats.policy_update_denied++;
        ax_trace(AX_EVT_SCHED_POLICY_DENY, token, g_syscall_gate_token, g_policy_epoch);
        return 0;
    }
    return apply_policy_internal(policy, actor_level);
}

int ax_sched_set_policy_checked(ax_sched_policy_t policy, uint64_t actor_level) {
    (void)policy;
    g_stats.policy_update_denied++;
    ax_trace(AX_EVT_SCHED_POLICY_DENY, actor_level, g_policy.min_policy_write_level, g_policy_epoch);
    return 0;
}

void ax_sched_set_policy(ax_sched_policy_t policy) {
    (void)ax_sched_set_policy_checked(policy, (uint64_t)-1);
}

uint64_t ax_sched_policy_epoch(void) {
    return g_policy_epoch;
}

ax_sched_policy_t ax_sched_get_policy(void) {
    return g_policy;
}

void ax_sched_init(void) {
    g_count = 0;
    g_tick = 0;
    g_policy_epoch = 0;
    g_rr_cursor = 0;
    g_syscall_gate_token = 0;
    g_syscall_gate_ready = 0;
    for (uint64_t i = 0; i < AX_SCHED_CLASS_COUNT; i++) g_rr_credit[i] = 0;

    g_stats.enqueued_total = 0;
    g_stats.dispatched_total = 0;
    g_stats.dropped_total = 0;
    g_stats.tick_count = 0;
    g_stats.depth = 0;
    g_stats.policy_updates = 0;
    g_stats.policy_update_denied = 0;
    g_stats.policy_epoch = 0;
    g_stats.last_class_dispatched = (uint64_t)AX_SCHED_CLASS_BACKGROUND;
    for (uint64_t i = 0; i < AX_SCHED_CLASS_COUNT; i++) {
        g_stats.class_depth[i] = 0;
        g_stats.class_dispatched[i] = 0;
    }
    g_stress.cycles_requested = 0;
    g_stress.cycles_completed = 0;
    g_stress.burst_requested = 0;
    g_stress.enqueues_attempted = 0;
    g_stress.enqueues_accepted = 0;
    g_stress.dispatches = 0;
    g_stress.policy_flips = 0;
    g_stress.drop_events = 0;
    g_stress.last_ok = 0;

    (void)apply_policy_internal((ax_sched_policy_t){
        .mode = AX_SCHED_POLICY_PRIORITY_AGING,
        .queue_capacity = 32,
        .min_priority = 0,
        .max_priority = 15,
        .default_quantum = 1,
        .aging_step = 1,
        .aging_interval_ticks = 4,
        .class_weights = { 1, 2, 3, 4 },
        .min_policy_write_level = 2,
    }, 3);
    ax_trace(AX_EVT_SCHED_INIT, g_policy.queue_capacity, g_policy.min_priority, g_policy.max_priority);
}

int ax_sched_enqueue_ex(uint64_t tid, uint64_t priority, ax_sched_class_t class_id, uint64_t quantum) {
    ax_sched_class_t normalized_class = norm_class((uint64_t)class_id);
    uint64_t cap = max_depth();
    int idx = find_tid(tid);
    if (idx < 0 && g_count >= cap) {
        g_stats.dropped_total++;
        return 0;
    }

    ax_sched_node_t n = (ax_sched_node_t){
        .tid = tid,
        .priority = clamp_u64(priority, g_policy.min_priority, g_policy.max_priority),
        .class_id = normalized_class,
        .quantum = (quantum == 0 ? g_policy.default_quantum : quantum),
        .inserted_tick = g_tick,
    };

    if (idx >= 0) {
        uint64_t old_class = class_idx(g_q[idx].class_id);
        uint64_t new_class = class_idx(n.class_id);
        g_q[idx] = n;
        if (old_class != new_class) {
            if (g_stats.class_depth[old_class] > 0) g_stats.class_depth[old_class]--;
            g_stats.class_depth[new_class]++;
        }
    } else {
        g_q[g_count++] = n;
        g_stats.class_depth[class_idx(n.class_id)]++;
    }
    g_stats.enqueued_total++;
    g_stats.depth = g_count;
    ax_trace(AX_EVT_SCHED_ENQUEUE, tid, n.priority, (uint64_t)n.class_id);
    return 1;
}

int ax_sched_enqueue(uint64_t tid, uint64_t priority) {
    return ax_sched_enqueue_ex(tid, priority, AX_SCHED_CLASS_USER, 0);
}

void ax_sched_tick(void) {
    g_tick++;
    g_stats.tick_count = g_tick;
}

uint64_t ax_sched_next(void) {
    if (g_count == 0) return 0;

    uint64_t best_idx = (g_policy.mode == AX_SCHED_POLICY_WEIGHTED_RR)
        ? pick_best_idx_weighted_rr()
        : pick_best_idx_priority();
    uint64_t best_score = effective_score(&g_q[best_idx]);

    uint64_t tid = g_q[best_idx].tid;
    uint64_t dispatched_class = class_idx(g_q[best_idx].class_id);
    for (uint64_t i = best_idx + 1; i < g_count; i++) {
        g_q[i - 1] = g_q[i];
    }
    g_count--;
    g_stats.dispatched_total++;
    g_stats.class_dispatched[dispatched_class]++;
    if (g_stats.class_depth[dispatched_class] > 0) g_stats.class_depth[dispatched_class]--;
    g_stats.depth = g_count;
    g_stats.last_class_dispatched = dispatched_class;
    ax_trace(AX_EVT_SCHED_DISPATCH, tid, best_score, g_count);
    return tid;
}

uint64_t ax_sched_depth(void) {
    return g_count;
}

ax_sched_stats_t ax_sched_stats(void) {
    g_stats.depth = g_count;
    g_stats.tick_count = g_tick;
    g_stats.policy_epoch = g_policy_epoch;
    return g_stats;
}

void ax_sched_run_stress(uint64_t cycles, uint64_t burst) {
    uint64_t baseline_drops = g_stats.dropped_total;
    uint64_t tid_seed = 0x10000u + (g_tick << 8);
    cycles = clamp_u64(cycles, 1, 64);
    burst = clamp_u64(burst, 1, 32);

    g_stress.cycles_requested = cycles;
    g_stress.cycles_completed = 0;
    g_stress.burst_requested = burst;
    g_stress.enqueues_attempted = 0;
    g_stress.enqueues_accepted = 0;
    g_stress.dispatches = 0;
    g_stress.policy_flips = 0;
    g_stress.drop_events = 0;
    g_stress.last_ok = 0;

    for (uint64_t c = 0; c < cycles; c++) {
        ax_sched_policy_t p = g_policy;
        uint64_t span = (p.max_priority >= p.min_priority) ? (p.max_priority - p.min_priority + 1) : 1;
        p.mode = (c & 1u) ? AX_SCHED_POLICY_WEIGHTED_RR : AX_SCHED_POLICY_PRIORITY_AGING;
        p.queue_capacity = clamp_u64(16 + burst + c, 8, AX_SCHED_Q_CAP);
        p.class_weights[0] = 1;
        p.class_weights[1] = 2 + (c & 1u);
        p.class_weights[2] = 3 + ((c >> 1) & 1u);
        p.class_weights[3] = 4 + ((c >> 2) & 1u);
        if (apply_policy_internal(p, 3)) g_stress.policy_flips++;
        g_stress.cycles_completed++;

        for (uint64_t i = 0; i < burst; i++) {
            uint64_t tid = tid_seed + (c * burst) + i + 1;
            uint64_t prio = p.min_priority + ((i * 3 + c * 5) % span);
            ax_sched_class_t cls = norm_class((i + c) % AX_SCHED_CLASS_COUNT);
            g_stress.enqueues_attempted++;
            if (ax_sched_enqueue_ex(tid, prio, cls, 1 + (i & 1u))) g_stress.enqueues_accepted++;
        }

        for (uint64_t d = 0; d < (burst / 2) + 1; d++) {
            if (ax_sched_next() == 0) break;
            g_stress.dispatches++;
        }
        ax_sched_tick();
    }

    while (g_count > 0) {
        if (ax_sched_next() == 0) break;
        g_stress.dispatches++;
    }
    g_stress.drop_events = g_stats.dropped_total - baseline_drops;
    g_stress.last_ok = (g_stress.cycles_completed == g_stress.cycles_requested)
        && (g_stress.enqueues_accepted > 0)
        && (g_stress.dispatches > 0)
        && (g_count == 0);
    ax_trace(AX_EVT_SCHED_STRESS, g_stress.dispatches, g_stress.drop_events, g_stress.last_ok);
}

ax_sched_stress_state_t ax_sched_stress_state(void) {
    return g_stress;
}
