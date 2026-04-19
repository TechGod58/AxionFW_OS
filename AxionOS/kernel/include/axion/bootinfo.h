#pragma once
#include <stdint.h>

typedef struct {
    uint64_t fb_base;
    uint32_t fb_width;
    uint32_t fb_height;
    uint32_t fb_pixels_per_scanline;
    uint32_t fb_bpp;

    uint64_t rsdp;

    uint64_t mmap;
    uint64_t mmap_size;
    uint64_t mmap_desc_size;
    uint32_t mmap_desc_ver;

    uint64_t caps0;
    uint64_t caps1;
} ax_bootinfo_t;

#define AX_CAP0_PREBOOT_AUTH (1ull << 0)
#define AX_CAP0_REPAIR_MODE  (1ull << 1)
#define AX_CAP0_MEMTEST64    (1ull << 2)
#define AX_CAP0_DISKTEST     (1ull << 3)
