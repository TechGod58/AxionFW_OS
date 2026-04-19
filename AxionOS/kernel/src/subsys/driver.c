#include "axion/subsys/driver.h"
#include "axion/bootinfo.h"
#include "axion/telemetry.h"
#include "axion/runtime/smart_driver_handoff.h"

static ax_driver_state_t g_drv;
static ax_driver_entry_t g_registry[AX_DRIVER_REG_CAP];

static int str_eq(const char *a, const char *b) {
    if (!a || !b) return 0;
    while (*a && *b) {
        if (*a != *b) return 0;
        a++;
        b++;
    }
    return (*a == 0 && *b == 0) ? 1 : 0;
}

void ax_driver_init(void) {
    g_drv.initialized = 1;
    g_drv.registered_total = 0;
    g_drv.active_total = 0;
    g_drv.blocked_total = 0;
    g_drv.policy_epoch = 1;
    g_drv.handoff_ready = AX_SDF_HANDOFF_READY;
    g_drv.handoff_token_hi = AX_SDF_HANDOFF_LOAD_ONCE_TOKEN_HI;
    g_drv.handoff_token_lo = AX_SDF_HANDOFF_LOAD_ONCE_TOKEN_LO;
    g_drv.handoff_resolved_total = AX_SDF_HANDOFF_RESOLVED_TOTAL;
    g_drv.handoff_synthesized_total = AX_SDF_HANDOFF_SYNTHESIZED_TOTAL;
    g_drv.handoff_signed_artifacts_total = AX_SDF_HANDOFF_SIGNED_ARTIFACTS_TOTAL;
    for (uint64_t i = 0; i < AX_DRIVER_REG_CAP; i++) g_registry[i].used = 0;

    (void)ax_driver_register("q35_chipset", 0x06, 0, 0);
    (void)ax_driver_register("virtio_blk_modern", 0x01, 0, 0);
    (void)ax_driver_register("e1000_probe", 0x02, 0, 0);
    ax_trace(AX_EVT_DRIVER_INIT, g_drv.registered_total, g_drv.handoff_ready, g_drv.handoff_signed_artifacts_total);
}

int ax_driver_register(const char *id, uint64_t class_code, uint64_t required_caps0_mask, uint64_t required_caps1_mask) {
    if (!g_drv.initialized || !id || id[0] == 0) return 0;
    if (g_drv.registered_total >= AX_DRIVER_REG_CAP) return 0;

    ax_driver_entry_t *e = &g_registry[g_drv.registered_total];
    e->id = id;
    e->class_code = class_code;
    e->required_caps0_mask = required_caps0_mask;
    e->required_caps1_mask = required_caps1_mask;
    e->active = 0;
    e->used = 1;
    g_drv.registered_total++;
    ax_trace(AX_EVT_DRIVER_REGISTER, g_drv.registered_total, class_code, required_caps1_mask);
    return 1;
}

int ax_driver_activate(const char *id, uint64_t caps0, uint64_t caps1) {
    if (!g_drv.initialized || !id) return 0;
    for (uint64_t i = 0; i < g_drv.registered_total; i++) {
        ax_driver_entry_t *e = &g_registry[i];
        if (!e->used) continue;
        if (!str_eq(e->id, id)) continue;

        if ((caps0 & e->required_caps0_mask) != e->required_caps0_mask
            || (caps1 & e->required_caps1_mask) != e->required_caps1_mask) {
            g_drv.blocked_total++;
            ax_trace(AX_EVT_DRIVER_ACTIVATE, i, 0, g_drv.blocked_total);
            return 0;
        }
        if (!e->active) {
            e->active = 1;
            g_drv.active_total++;
        }
        ax_trace(AX_EVT_DRIVER_ACTIVATE, i, 1, g_drv.active_total);
        return 1;
    }
    return 0;
}

ax_driver_state_t ax_driver_state(void) {
    return g_drv;
}

const ax_driver_entry_t *ax_driver_entry(uint64_t index) {
    if (index >= g_drv.registered_total) return (const ax_driver_entry_t *)0;
    if (!g_registry[index].used) return (const ax_driver_entry_t *)0;
    return &g_registry[index];
}
