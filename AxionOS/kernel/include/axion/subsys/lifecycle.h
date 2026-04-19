#pragma once
#include <stdint.h>

typedef struct {
    uint64_t initialized;
    uint64_t required_stage_mask;
    uint64_t stage_mask;
    uint64_t stage_ok_mask;
    uint64_t ownership_checks;
    uint64_t ownership_failed;
    uint64_t warnings;
    uint64_t health_score;
    uint64_t finalized;
} ax_lifecycle_state_t;

void ax_lifecycle_init(void);
void ax_lifecycle_set_required_mask(uint64_t required_stage_mask);
void ax_lifecycle_mark_stage(uint64_t stage_bit, uint64_t ok);
void ax_lifecycle_finalize(void);
uint64_t ax_lifecycle_is_ready(void);
ax_lifecycle_state_t ax_lifecycle_state(void);
