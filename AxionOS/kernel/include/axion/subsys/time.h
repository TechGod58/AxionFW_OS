#pragma once
#include <stdint.h>

typedef enum {
    AX_TIME_SRC_PIT = 0,
    AX_TIME_SRC_TSC = 1,
} ax_time_source_t;

typedef struct {
    uint64_t initialized;
    ax_time_source_t source;
    uint64_t tick_hz;
    uint64_t ticks;
    uint64_t monotonic_ms;
    uint64_t drift_ppm_limit;
} ax_time_state_t;

void ax_time_init(uint64_t caps1);
void ax_time_tick(uint64_t delta_ticks);
uint64_t ax_time_now_ms(void);
ax_time_state_t ax_time_state(void);
