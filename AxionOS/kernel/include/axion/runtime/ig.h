#pragma once
#include <stdint.h>

typedef struct {
    uint64_t total;
    uint64_t allowed;
    uint64_t denied;
    uint64_t last_hash;
} axion_ig_state_t;

int axion_ig_validate(const char *event);
axion_ig_state_t axion_ig_state(void);

