#include "axion/telemetry.h"
#include "axion/console.h"

static uint64_t g_evt_idx = 0;

// Minimal telemetry: print + implicit ring index.
// Later: per-core buffers, timestamping (TSC), export protocol for IG.
void ax_telemetry_init(void) {
    g_evt_idx = 0;
}

void ax_trace(ax_evt_type_t t, uint64_t a, uint64_t b, uint64_t c) {
    g_evt_idx++;
    // Keep output small; serial/stdout is not available unless you add it.
    // Framebuffer console only (for now).
    (void)b; (void)c;
    ax_printf("[trace] #%lu type=%lu a=0x%lx\n", g_evt_idx, (uint64_t)t, a);
}
