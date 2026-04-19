#pragma once
#include <stdint.h>

typedef struct {
    uint64_t initialized;
    uint64_t vector_base;
    uint64_t vector_count;
    uint64_t enabled_lines_mask_lo;
    uint64_t dispatch_total;
    uint64_t spurious_total;
} ax_irq_state_t;

void ax_irq_init(uint64_t firmware_tables_present);
int ax_irq_enable_line(uint64_t line);
void ax_irq_dispatch(uint64_t vector);
ax_irq_state_t ax_irq_state(void);

