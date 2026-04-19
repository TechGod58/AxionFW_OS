#include "axion/subsys/irq.h"
#include "axion/telemetry.h"

static ax_irq_state_t g_irq;

void ax_irq_init(uint64_t firmware_tables_present) {
    g_irq.initialized = 1;
    g_irq.vector_base = firmware_tables_present ? 0x20u : 0x30u;
    g_irq.vector_count = 224;
    g_irq.enabled_lines_mask_lo = 0;
    g_irq.dispatch_total = 0;
    g_irq.spurious_total = 0;
    ax_trace(AX_EVT_IRQ_INIT, g_irq.vector_base, g_irq.vector_count, firmware_tables_present);
}

int ax_irq_enable_line(uint64_t line) {
    if (!g_irq.initialized) return 0;
    if (line >= 64) return 0;
    g_irq.enabled_lines_mask_lo |= (1ull << line);
    return 1;
}

void ax_irq_dispatch(uint64_t vector) {
    if (!g_irq.initialized) return;
    if (vector < g_irq.vector_base || vector >= (g_irq.vector_base + g_irq.vector_count)) {
        g_irq.spurious_total++;
        ax_trace(AX_EVT_IRQ_DISPATCH, vector, 0, 1);
        return;
    }
    g_irq.dispatch_total++;
    ax_trace(AX_EVT_IRQ_DISPATCH, vector, 1, 0);
}

ax_irq_state_t ax_irq_state(void) {
    return g_irq;
}

