#include <stdint.h>
#include "axion/drivers.h"

static ax_reference_bsp_status_t g_status;

static inline void com1_out(char c){ __asm__ volatile("outb %0, %1" : : "a"((uint8_t)c), "Nd"((uint16_t)0x3F8)); }
static void com1_puts(const char *s){ while(*s) com1_out(*s++); }

const ax_reference_bsp_status_t *ax_reference_bsp_last_status(void){
    return &g_status;
}

void ax_reference_bsp_q35_init(const ax_bootinfo_t *bootinfo){
    g_status = (ax_reference_bsp_status_t){0};
    com1_puts("AXHAL_REF_BSP=q35\n");
    ax_drv_acpi_handoff_probe(bootinfo, &g_status);
    ax_drv_q35_chipset_probe(&g_status);
    ax_drv_e1000_probe(&g_status);
    com1_puts(g_status.acpi_ready ? "AXHAL_ACPI_READY\n" : "AXHAL_ACPI_FAIL\n");
    com1_puts(g_status.q35_ready ? "AXHAL_Q35_READY\n" : "AXHAL_Q35_FAIL\n");
    com1_puts(g_status.net_ready ? "AXHAL_NET_READY\n" : "AXHAL_NET_FAIL\n");
    com1_puts(g_status.storage_ready ? "AXHAL_STORAGE_READY\n" : "AXHAL_STORAGE_FAIL\n");
}
