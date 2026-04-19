#pragma once
#include <stdint.h>

typedef struct {
    uint64_t attached_total;
    uint64_t last_event_hash;
} axion_qecc_state_t;

void axion_qecc_attach(const char *event);
axion_qecc_state_t axion_qecc_state(void);

