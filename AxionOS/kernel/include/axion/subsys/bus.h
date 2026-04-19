#pragma once
#include <stdint.h>

typedef struct {
    uint64_t initialized;
    uint64_t acpi_present;
    uint64_t segment_count;
    uint64_t scan_rounds;
    uint64_t devices_seen;
    uint64_t bridges_seen;
    uint64_t endpoints_seen;
    uint64_t guard_allowed;
    uint64_t guard_denied;
} ax_bus_state_t;

void ax_bus_init(uint64_t rsdp);
void ax_bus_note_device(uint64_t class_code, uint64_t subclass);
ax_bus_state_t ax_bus_state(void);
