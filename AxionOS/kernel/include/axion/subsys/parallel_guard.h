#pragma once
#include <stdint.h>

typedef enum {
    AX_PCGUARD_ALLOW = 0,
    AX_PCGUARD_DENY_NOT_INITIALIZED = 1,
    AX_PCGUARD_DENY_INVENTORY_REQUIRED = 2,
    AX_PCGUARD_DENY_HANDOFF_REQUIRED = 3,
    AX_PCGUARD_DENY_CLASS_NOT_ALLOWED = 4,
    AX_PCGUARD_DENY_CLASS_EXPLICIT = 5,
} ax_parallel_guard_reason_t;

typedef struct {
    uint64_t initialized;
    uint64_t enabled;
    uint64_t strict_mode;
    uint64_t inventory_required;
    uint64_t inventory_ready;
    uint64_t handoff_ready;
    uint64_t allow_mask;
    uint64_t deny_mask;
    uint64_t decisions_total;
    uint64_t decisions_allowed;
    uint64_t decisions_denied;
    uint64_t last_class_code;
    uint64_t last_subclass;
    uint64_t last_reason;
} ax_parallel_guard_state_t;

void ax_parallel_guard_init(uint64_t enabled, uint64_t strict_mode, uint64_t inventory_required, uint64_t inventory_ready, uint64_t handoff_ready);
void ax_parallel_guard_set_policy_masks(uint64_t allow_mask, uint64_t deny_mask);
uint64_t ax_parallel_guard_check_bus_device(uint64_t class_code, uint64_t subclass);
ax_parallel_guard_state_t ax_parallel_guard_state(void);
