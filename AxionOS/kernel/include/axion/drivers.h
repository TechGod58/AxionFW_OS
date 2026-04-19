#pragma once

#include <stdint.h>
#include "axion/bootinfo.h"

typedef struct {
    uint8_t acpi_ready;
    uint8_t q35_ready;
    uint8_t net_ready;
    uint8_t storage_ready;
    uint64_t rsdp_ptr;
    uint64_t root_sdt_ptr;
} ax_reference_bsp_status_t;

const ax_reference_bsp_status_t *ax_reference_bsp_last_status(void);
void ax_reference_bsp_q35_init(const ax_bootinfo_t *bootinfo);
void ax_drv_acpi_handoff_probe(const ax_bootinfo_t *bootinfo, ax_reference_bsp_status_t *status);
void ax_drv_q35_chipset_probe(ax_reference_bsp_status_t *status);
void ax_drv_e1000_probe(ax_reference_bsp_status_t *status);

void ax_run_boot_diagnostics(const ax_bootinfo_t *bootinfo);
uint32_t ax_boot_diag_memtest_ok(void);
uint32_t ax_boot_diag_disk_ok(void);
