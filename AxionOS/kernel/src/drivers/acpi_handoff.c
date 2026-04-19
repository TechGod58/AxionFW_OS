#include <stdint.h>
#include "axion/drivers.h"

static inline void com1_out(char c){ __asm__ volatile("outb %0, %1" : : "a"((uint8_t)c), "Nd"((uint16_t)0x3F8)); }
static void com1_puts(const char *s){ while(*s) com1_out(*s++); }
static void com1_hex8(uint8_t v){ const char* h="0123456789ABCDEF"; com1_out(h[(v>>4)&0xF]); com1_out(h[v&0xF]); }
static void com1_hex32(uint32_t v){ com1_hex8((uint8_t)(v>>24)); com1_hex8((uint8_t)(v>>16)); com1_hex8((uint8_t)(v>>8)); com1_hex8((uint8_t)v); }
static void com1_hex64(uint64_t v){ com1_hex32((uint32_t)(v>>32)); com1_hex32((uint32_t)v); }

struct ax_rsdp {
    char signature[8];
    uint8_t checksum;
    char oem_id[6];
    uint8_t revision;
    uint32_t rsdt_address;
    uint32_t length;
    uint64_t xsdt_address;
    uint8_t extended_checksum;
    uint8_t reserved[3];
} __attribute__((packed));

struct ax_sdt_header {
    char signature[4];
    uint32_t length;
    uint8_t revision;
    uint8_t checksum;
    char oem_id[6];
    char oem_table_id[8];
    uint32_t oem_revision;
    uint32_t creator_id;
    uint32_t creator_revision;
} __attribute__((packed));

static int memeq(const char *a, const char *b, uint32_t n){
    for(uint32_t i=0;i<n;i++) if(a[i] != b[i]) return 0;
    return 1;
}

static int checksum_ok(const uint8_t *p, uint32_t len){
    uint8_t sum = 0;
    for(uint32_t i=0;i<len;i++) sum = (uint8_t)(sum + p[i]);
    return sum == 0;
}

static uint64_t scan_for_rsdp(void){
    for(uint64_t p = 0x000E0000ull; p < 0x00100000ull; p += 16ull){
        const struct ax_rsdp *cand = (const struct ax_rsdp *)(uintptr_t)p;
        if(memeq(cand->signature, "RSD PTR ", 8) && checksum_ok((const uint8_t *)cand, cand->revision >= 2 ? cand->length : 20u)) return p;
    }
    return 0;
}

void ax_drv_acpi_handoff_probe(const ax_bootinfo_t *bootinfo, ax_reference_bsp_status_t *status){
    status->rsdp_ptr = bootinfo->rsdp;
    if(!bootinfo->rsdp){
        com1_puts("DRV_ACPI_RSDP_FAIL\n");
        return;
    }

    const struct ax_rsdp *rsdp = (const struct ax_rsdp *)(uintptr_t)bootinfo->rsdp;
    if(!memeq(rsdp->signature, "RSD PTR ", 8) || !checksum_ok((const uint8_t *)rsdp, rsdp->revision >= 2 ? rsdp->length : 20u)) {
        uint64_t fallback = scan_for_rsdp();
        if(!fallback){
            com1_puts("DRV_ACPI_SIG_FAIL\n");
            return;
        }
        status->rsdp_ptr = fallback;
        rsdp = (const struct ax_rsdp *)(uintptr_t)fallback;
        com1_puts("DRV_ACPI_RSDP_FALLBACK\n");
    }

    uint64_t root_ptr = rsdp->revision >= 2 && rsdp->xsdt_address ? rsdp->xsdt_address : (uint64_t)rsdp->rsdt_address;
    int xsdt = (rsdp->revision >= 2 && rsdp->xsdt_address) ? 1 : 0;
    status->root_sdt_ptr = root_ptr;
    status->acpi_ready = root_ptr != 0;
    com1_puts("DRV_ACPI_RSDP_OK ptr=0x"); com1_hex64(status->rsdp_ptr); com1_puts("\n");
    if(root_ptr){
        com1_puts(xsdt ? "DRV_ACPI_XSDT_OK ptr=0x" : "DRV_ACPI_RSDT_OK ptr=0x");
        com1_hex64(root_ptr);
        com1_puts("\n");
    }
}
