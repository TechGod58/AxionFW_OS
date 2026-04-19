#pragma once
#include <stdint.h>
#include "axion/bootinfo.h"

typedef struct {
    uint64_t total_bytes;
    uint64_t usable_bytes;
    uint64_t first_usable_base;
    uint64_t desc_count;
} ax_mem_state_t;

typedef struct {
    uint64_t tracked_pages;
    uint64_t active_allocations;
    uint64_t high_watermark;
    uint64_t alloc_attempts;
    uint64_t alloc_success;
    uint64_t release_attempts;
    uint64_t release_success;
    uint64_t stress_cycles;
    uint64_t stress_failures;
    uint64_t pressure_peak_pct;
    uint64_t last_alloc_addr;
} ax_mem_health_t;

void ax_mem_init(const ax_bootinfo_t *bi);
ax_mem_state_t ax_mem_state(void);
uint64_t ax_mem_alloc_page(void);
int ax_mem_release_page(uint64_t page_addr);
void ax_mem_run_stress(uint64_t cycles, uint64_t alloc_burst);
ax_mem_health_t ax_mem_health(void);
