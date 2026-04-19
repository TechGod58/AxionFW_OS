#include "axion/subsys/userland.h"
#include "axion/bootinfo.h"
#include "axion/telemetry.h"

#define AX_USERLAND_Q_CAP 16

typedef struct {
    const char *name;
    uint64_t level;
    uint64_t used;
} ax_userland_item_t;

static ax_userland_state_t g_ul;
static ax_userland_item_t g_q[AX_USERLAND_Q_CAP];
static uint64_t g_head;
static uint64_t g_tail;

static int starts_with(const char *s, const char *prefix) {
    if (!s || !prefix) return 0;
    while (*prefix) {
        if (*s != *prefix) return 0;
        s++;
        prefix++;
    }
    return 1;
}

void ax_userland_init(uint64_t launch_budget) {
    g_ul.initialized = 1;
    g_ul.launch_budget = launch_budget == 0 ? 1 : launch_budget;
    g_ul.queued = 0;
    g_ul.launched = 0;
    g_ul.denied = 0;
    g_ul.ready_services = 0;
    g_ul.last_level = 0;
    g_head = 0;
    g_tail = 0;
    for (uint64_t i = 0; i < AX_USERLAND_Q_CAP; i++) g_q[i].used = 0;
    ax_trace(AX_EVT_USERLAND_INIT, g_ul.launch_budget, 0, 0);
}

int ax_userland_queue_service(const char *service_name, uint64_t requested_level, uint64_t caps0) {
    if (!g_ul.initialized || !service_name || service_name[0] == 0) return 0;
    if (g_ul.queued >= AX_USERLAND_Q_CAP) {
        g_ul.denied++;
        return 0;
    }

    uint64_t needs_preboot = starts_with(service_name, "secure/") ? 1 : 0;
    if (requested_level >= 2 && needs_preboot && ((caps0 & AX_CAP0_PREBOOT_AUTH) == 0)) {
        g_ul.denied++;
        ax_trace(AX_EVT_USERLAND_QUEUE, requested_level, 0, g_ul.denied);
        return 0;
    }

    g_q[g_tail] = (ax_userland_item_t){ .name = service_name, .level = requested_level, .used = 1 };
    g_tail = (g_tail + 1) % AX_USERLAND_Q_CAP;
    g_ul.queued++;
    g_ul.last_level = requested_level;
    ax_trace(AX_EVT_USERLAND_QUEUE, requested_level, 1, g_ul.queued);
    return 1;
}

int ax_userland_launch_next(void) {
    if (!g_ul.initialized) return 0;
    if (g_ul.queued == 0) return 0;
    if (g_ul.launched >= g_ul.launch_budget) {
        g_ul.denied++;
        return 0;
    }

    ax_userland_item_t item = g_q[g_head];
    if (!item.used) return 0;
    g_q[g_head].used = 0;
    g_head = (g_head + 1) % AX_USERLAND_Q_CAP;
    g_ul.queued--;
    g_ul.launched++;
    g_ul.ready_services++;
    g_ul.last_level = item.level;
    ax_trace(AX_EVT_USERLAND_LAUNCH, item.level, g_ul.launched, g_ul.queued);
    return 1;
}

ax_userland_state_t ax_userland_state(void) {
    return g_ul;
}

