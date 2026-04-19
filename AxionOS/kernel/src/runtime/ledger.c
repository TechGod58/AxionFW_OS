#include <axion/runtime/ledger.h>
#include "axion/telemetry.h"

static axion_ledger_state_t g_ledger;

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

void axion_ledger_init(void) {
    g_ledger.initialized = 1;
    g_ledger.commits = 0;
    g_ledger.rolling_hash = 0;
    g_ledger.last_event_hash = 0;
}

void axion_ledger_commit(const char *event) {
    if (!g_ledger.initialized) axion_ledger_init();
    uint64_t h = hash64(event);
    g_ledger.commits++;
    g_ledger.last_event_hash = h;
    g_ledger.rolling_hash = (g_ledger.rolling_hash * 1315423911ull) ^ h ^ g_ledger.commits;
    ax_trace(AX_EVT_RUNTIME_LEDGER_COMMIT, g_ledger.commits, g_ledger.rolling_hash, h);
}

axion_ledger_state_t axion_ledger_state(void) {
    return g_ledger;
}

