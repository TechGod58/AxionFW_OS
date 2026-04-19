#include "axion/subsys/bus.h"
#include "axion/subsys/parallel_guard.h"
#include "axion/telemetry.h"

static ax_bus_state_t g_bus;

void ax_bus_init(uint64_t rsdp) {
    g_bus.initialized = 1;
    g_bus.acpi_present = rsdp != 0 ? 1 : 0;
    g_bus.segment_count = 1;
    g_bus.scan_rounds = 1;
    g_bus.devices_seen = 0;
    g_bus.bridges_seen = 0;
    g_bus.endpoints_seen = 0;
    g_bus.guard_allowed = 0;
    g_bus.guard_denied = 0;
    ax_trace(AX_EVT_BUS_INIT, g_bus.acpi_present, g_bus.segment_count, rsdp);
}

void ax_bus_note_device(uint64_t class_code, uint64_t subclass) {
    if (!g_bus.initialized) return;
    if (!ax_parallel_guard_check_bus_device(class_code, subclass)) {
        g_bus.guard_denied++;
        return;
    }
    g_bus.guard_allowed++;
    g_bus.devices_seen++;
    if (class_code == 0x06u) g_bus.bridges_seen++;
    else g_bus.endpoints_seen++;
    ax_trace(AX_EVT_BUS_DEVICE, class_code, subclass, g_bus.devices_seen);
}

ax_bus_state_t ax_bus_state(void) {
    return g_bus;
}
