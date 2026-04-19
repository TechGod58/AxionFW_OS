#pragma once
#include <stdint.h>

typedef struct {
    uint64_t initialized;
    uint64_t launch_budget;
    uint64_t queued;
    uint64_t launched;
    uint64_t denied;
    uint64_t ready_services;
    uint64_t last_level;
} ax_userland_state_t;

void ax_userland_init(uint64_t launch_budget);
int ax_userland_queue_service(const char *service_name, uint64_t requested_level, uint64_t caps0);
int ax_userland_launch_next(void);
ax_userland_state_t ax_userland_state(void);

