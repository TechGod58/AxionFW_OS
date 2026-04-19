#include <stdint.h>
#include <stddef.h>
#include "axion/bootinfo.h"

extern void ax_kdisk_modern_probe(void);

static uint32_t g_memtest64_ok = 0;
static uint32_t g_disktest_ok = 0;
__attribute__((aligned(64))) static uint64_t diag_mem_region[131072];

static inline void com1_out(char c){ __asm__ volatile("outb %0, %1" : : "a"((uint8_t)c), "Nd"((uint16_t)0x3F8)); }
static void com1_puts(const char *s){ while(*s) com1_out(*s++); }

static int memtest64_run(void){
    const uint64_t patterns[] = {0x0000000000000000ull, 0xFFFFFFFFFFFFFFFFull, 0xAAAAAAAAAAAAAAAAull, 0x5555555555555555ull};
    for(size_t p=0; p<sizeof(patterns)/sizeof(patterns[0]); p++){
        for(size_t i=0; i<131072; i++) diag_mem_region[i] = patterns[p];
        for(size_t i=0; i<131072; i++) if(diag_mem_region[i] != patterns[p]) return 0;
    }
    return 1;
}

void ax_run_boot_diagnostics(const ax_bootinfo_t *bootinfo){
    uint64_t flags = bootinfo->caps0;
    if(flags & AX_CAP0_REPAIR_MODE) com1_puts("BOOT_DIAG_REPAIR_MODE\n");
    if(flags & AX_CAP0_MEMTEST64){
        com1_puts("BOOT_DIAG_MEMTEST64_START\n");
        g_memtest64_ok = memtest64_run();
        com1_puts(g_memtest64_ok ? "BOOT_DIAG_MEMTEST64_PASS\n" : "BOOT_DIAG_MEMTEST64_FAIL\n");
    }
    if((flags & AX_CAP0_DISKTEST) || (flags & AX_CAP0_REPAIR_MODE)){
        com1_puts("BOOT_DIAG_DISK_START\n");
        ax_kdisk_modern_probe();
        g_disktest_ok = 1;
        com1_puts("BOOT_DIAG_DISK_DONE\n");
    }
}

uint32_t ax_boot_diag_memtest_ok(void){ return g_memtest64_ok; }
uint32_t ax_boot_diag_disk_ok(void){ return g_disktest_ok; }
