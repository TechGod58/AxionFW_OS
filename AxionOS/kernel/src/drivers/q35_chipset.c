#include <stdint.h>
#include "axion/drivers.h"
#include "axion/subsys/bus.h"

#define INTEL_VENDOR 0x8086
#define Q35_HOST_BRIDGE 0x29C0
#define ICH9_LPC 0x2918
#define VIRTIO_VENDOR 0x1AF4
#define VIRTIO_BLK_MODERN 0x1042
#define VIRTIO_BLK_TRANSITIONAL 0x1001

static inline void outl(uint16_t p, uint32_t v){ __asm__ volatile("outl %0,%1"::"a"(v),"Nd"(p)); }
static inline uint32_t inl(uint16_t p){ uint32_t v; __asm__ volatile("inl %1,%0":"=a"(v):"Nd"(p)); return v; }
static inline void com1_out(char c){ __asm__ volatile("outb %0, %1" : : "a"((uint8_t)c), "Nd"((uint16_t)0x3F8)); }
static void com1_puts(const char *s){ while(*s) com1_out(*s++); }

static uint32_t pci_cfg_read32(uint8_t bus, uint8_t slot, uint8_t func, uint8_t off){
    uint32_t a = 0x80000000u | ((uint32_t)bus<<16) | ((uint32_t)slot<<11) | ((uint32_t)func<<8) | (off & 0xFC);
    outl(0xCF8, a); return inl(0xCFC);
}

void ax_drv_q35_chipset_probe(ax_reference_bsp_status_t *status){
    int host = 0, lpc = 0, storage = 0;
    for(uint16_t bus=0; bus<256; bus++) for(uint8_t slot=0; slot<32; slot++) for(uint8_t func=0; func<8; func++){
        uint32_t id = pci_cfg_read32((uint8_t)bus, slot, func, 0x00);
        uint16_t ven = (uint16_t)(id & 0xFFFFu);
        uint16_t dev = (uint16_t)(id >> 16);
        if(ven == 0xFFFFu) continue;
        uint32_t classreg = pci_cfg_read32((uint8_t)bus, slot, func, 0x08);
        uint8_t class_code = (uint8_t)(classreg >> 24);
        uint8_t subclass = (uint8_t)(classreg >> 16);
        ax_bus_note_device((uint64_t)class_code, (uint64_t)subclass);
        if(ven == INTEL_VENDOR && dev == Q35_HOST_BRIDGE) host = 1;
        if(ven == INTEL_VENDOR && dev == ICH9_LPC) lpc = 1;
        if(ven == VIRTIO_VENDOR && (dev == VIRTIO_BLK_MODERN || dev == VIRTIO_BLK_TRANSITIONAL)) storage = 1;
    }
    if(host) com1_puts("DRV_Q35_HOST_OK\n"); else com1_puts("DRV_Q35_HOST_FAIL\n");
    if(lpc) com1_puts("DRV_ICH9_LPC_OK\n"); else com1_puts("DRV_ICH9_LPC_FAIL\n");
    if(storage) com1_puts("DRV_VIRTIO_BLK_PRESENT\n"); else com1_puts("DRV_VIRTIO_BLK_ABSENT\n");
    status->q35_ready = (uint8_t)(host && lpc);
    status->storage_ready = (uint8_t)storage;
}
