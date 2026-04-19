#include "axion/subsys/time.h"
#include "axion/bootinfo.h"
#include "axion/telemetry.h"

static ax_time_state_t g_time;

void ax_time_init(uint64_t caps1) {
    (void)caps1;
    g_time.initialized = 1;
    g_time.source = AX_TIME_SRC_TSC;
    g_time.tick_hz = 1000;
    g_time.ticks = 0;
    g_time.monotonic_ms = 0;
    g_time.drift_ppm_limit = 120;
    ax_trace(AX_EVT_TIME_INIT, (uint64_t)g_time.source, g_time.tick_hz, g_time.drift_ppm_limit);
}

void ax_time_tick(uint64_t delta_ticks) {
    if (!g_time.initialized) return;
    g_time.ticks += delta_ticks;
    if (g_time.tick_hz == 0) g_time.tick_hz = 1;
    g_time.monotonic_ms = (g_time.ticks * 1000ull) / g_time.tick_hz;
    ax_trace(AX_EVT_TIME_TICK, delta_ticks, g_time.ticks, g_time.monotonic_ms);
}

uint64_t ax_time_now_ms(void) {
    return g_time.monotonic_ms;
}

ax_time_state_t ax_time_state(void) {
    return g_time;
}
