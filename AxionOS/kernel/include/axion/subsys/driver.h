#pragma once
#include <stdint.h>

#define AX_DRIVER_REG_CAP 16

typedef struct {
    const char *id;
    uint64_t class_code;
    uint64_t required_caps0_mask;
    uint64_t required_caps1_mask;
    uint64_t active;
    uint64_t used;
} ax_driver_entry_t;

typedef struct {
    uint64_t initialized;
    uint64_t registered_total;
    uint64_t active_total;
    uint64_t blocked_total;
    uint64_t policy_epoch;
    uint64_t handoff_ready;
    uint64_t handoff_token_hi;
    uint64_t handoff_token_lo;
    uint64_t handoff_resolved_total;
    uint64_t handoff_synthesized_total;
    uint64_t handoff_signed_artifacts_total;
} ax_driver_state_t;

void ax_driver_init(void);
int ax_driver_register(const char *id, uint64_t class_code, uint64_t required_caps0_mask, uint64_t required_caps1_mask);
int ax_driver_activate(const char *id, uint64_t caps0, uint64_t caps1);
ax_driver_state_t ax_driver_state(void);
const ax_driver_entry_t *ax_driver_entry(uint64_t index);
