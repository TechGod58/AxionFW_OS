#pragma once
#include <stdint.h>

#define AX_SCHED_CLASS_COUNT 4

typedef enum {
    AX_SCHED_CLASS_BACKGROUND = 0,
    AX_SCHED_CLASS_USER = 1,
    AX_SCHED_CLASS_SYSTEM = 2,
    AX_SCHED_CLASS_REALTIME = 3,
} ax_sched_class_t;

typedef enum {
    AX_SCHED_POLICY_PRIORITY_AGING = 0,
    AX_SCHED_POLICY_WEIGHTED_RR = 1,
} ax_sched_policy_mode_t;

typedef struct {
    ax_sched_policy_mode_t mode;
    uint64_t queue_capacity;
    uint64_t min_priority;
    uint64_t max_priority;
    uint64_t default_quantum;
    uint64_t aging_step;
    uint64_t aging_interval_ticks;
    uint64_t class_weights[AX_SCHED_CLASS_COUNT];
    uint64_t min_policy_write_level;
} ax_sched_policy_t;

typedef struct {
    uint64_t enqueued_total;
    uint64_t dispatched_total;
    uint64_t dropped_total;
    uint64_t tick_count;
    uint64_t depth;
    uint64_t class_depth[AX_SCHED_CLASS_COUNT];
    uint64_t class_dispatched[AX_SCHED_CLASS_COUNT];
    uint64_t policy_updates;
    uint64_t policy_update_denied;
    uint64_t policy_epoch;
    uint64_t last_class_dispatched;
} ax_sched_stats_t;

typedef struct {
    uint64_t cycles_requested;
    uint64_t cycles_completed;
    uint64_t burst_requested;
    uint64_t enqueues_attempted;
    uint64_t enqueues_accepted;
    uint64_t dispatches;
    uint64_t policy_flips;
    uint64_t drop_events;
    uint64_t last_ok;
} ax_sched_stress_state_t;

void ax_sched_init(void);
int ax_sched_enqueue(uint64_t tid, uint64_t priority);
int ax_sched_enqueue_ex(uint64_t tid, uint64_t priority, ax_sched_class_t class_id, uint64_t quantum);
void ax_sched_tick(void);
uint64_t ax_sched_next(void);
uint64_t ax_sched_depth(void);
void ax_sched_set_policy(ax_sched_policy_t policy);
int ax_sched_set_policy_checked(ax_sched_policy_t policy, uint64_t actor_level);
ax_sched_policy_t ax_sched_get_policy(void);
uint64_t ax_sched_policy_epoch(void);
ax_sched_stats_t ax_sched_stats(void);
void ax_sched_run_stress(uint64_t cycles, uint64_t burst);
ax_sched_stress_state_t ax_sched_stress_state(void);
