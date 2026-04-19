#include <axion/runtime/qecc.h>
#include "axion/telemetry.h"

static axion_qecc_state_t g_qecc;

static uint64_t hash64(const char *s) {
    uint64_t h = 1469598103934665603ull;
    if (!s) return h;
    while (*s) {
        h ^= (uint8_t)(*s);
        h *= 1099511628211ull;
        s++;
    }
    return h;
}

void axion_qecc_attach(const char *event) {
    uint64_t h = hash64(event);
    g_qecc.attached_total++;
    g_qecc.last_event_hash = h;
    ax_trace(AX_EVT_RUNTIME_QECC_ATTACH, g_qecc.attached_total, h, 0);
}

axion_qecc_state_t axion_qecc_state(void) {
    return g_qecc;
}

