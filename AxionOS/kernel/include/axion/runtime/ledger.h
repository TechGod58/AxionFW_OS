#pragma once
#include <stdint.h>

typedef struct {
    uint64_t initialized;
    uint64_t commits;
    uint64_t rolling_hash;
    uint64_t last_event_hash;
} axion_ledger_state_t;

void axion_ledger_init(void);
void axion_ledger_commit(const char *event);
axion_ledger_state_t axion_ledger_state(void);

