#include <stdint.h>
#include "axion/drivers.h"

#define INTEL_VENDOR 0x8086
#define E1000_DEV 0x100E

static uint32_t pci_cfg_read32(uint8_t bus, uint8_t slot, uint8_t func, uint8_t off);

static inline void outl(uint16_t p, uint32_t v){ __asm__ volatile("outl %0,%1"::"a"(v),"Nd"(p)); }
static inline uint32_t inl(uint16_t p){ uint32_t v; __asm__ volatile("inl %1,%0":"=a"(v):"Nd"(p)); return v; }
static uint16_t pci_cfg_read16(uint8_t bus, uint8_t slot, uint8_t func, uint8_t off){
    uint32_t v = pci_cfg_read32(bus, slot, func, off);
    return (uint16_t)((v >> ((off & 2u) * 8u)) & 0xFFFFu);
}
static void pci_cfg_write16(uint8_t bus, uint8_t slot, uint8_t func, uint8_t off, uint16_t val){
    uint32_t a = 0x80000000u | ((uint32_t)bus<<16) | ((uint32_t)slot<<11) | ((uint32_t)func<<8) | (off & 0xFC);
    outl(0xCF8, a);
    uint32_t old = inl(0xCFC);
    uint32_t sh = (uint32_t)((off & 2u) * 8u);
    uint32_t nw = (old & ~(0xFFFFu << sh)) | ((uint32_t)val << sh);
    outl(0xCF8, a);
    outl(0xCFC, nw);
}
static inline void com1_out(char c){ __asm__ volatile("outb %0, %1" : : "a"((uint8_t)c), "Nd"((uint16_t)0x3F8)); }
static void com1_puts(const char *s){ while(*s) com1_out(*s++); }
static void com1_hex8(uint8_t v){ const char* h="0123456789ABCDEF"; com1_out(h[(v>>4)&0xF]); com1_out(h[v&0xF]); }
static void com1_hex32(uint32_t v){ com1_hex8((uint8_t)(v>>24)); com1_hex8((uint8_t)(v>>16)); com1_hex8((uint8_t)(v>>8)); com1_hex8((uint8_t)v); }

static uint32_t pci_cfg_read32(uint8_t bus, uint8_t slot, uint8_t func, uint8_t off){
    uint32_t a = 0x80000000u | ((uint32_t)bus<<16) | ((uint32_t)slot<<11) | ((uint32_t)func<<8) | (off & 0xFC);
    outl(0xCF8, a); return inl(0xCFC);
}

void ax_drv_e1000_probe(ax_reference_bsp_status_t *status){
    for(uint16_t bus=0; bus<256; bus++) for(uint8_t slot=0; slot<32; slot++) for(uint8_t func=0; func<8; func++){
        uint32_t id = pci_cfg_read32((uint8_t)bus, slot, func, 0x00);
        uint16_t ven = (uint16_t)(id & 0xFFFFu);
        uint16_t dev = (uint16_t)(id >> 16);
        if(ven == INTEL_VENDOR && dev == E1000_DEV){
            uint16_t cmd = pci_cfg_read16((uint8_t)bus, slot, func, 0x04);
            cmd |= (uint16_t)((1u << 1) | (1u << 2));
            pci_cfg_write16((uint8_t)bus, slot, func, 0x04, cmd);
            uint32_t bar0 = pci_cfg_read32((uint8_t)bus, slot, func, 0x10);
            uint32_t mmio = bar0 & ~0xFu;
            volatile uint32_t *regs = (volatile uint32_t *)(uintptr_t)mmio;
            uint32_t device_status = regs[0x0008/4];
            uint32_t ral = regs[0x5400/4];
            uint32_t rah = regs[0x5404/4];
            com1_puts("DRV_E1000_OK BAR0=0x"); com1_hex32(bar0); com1_puts(" STATUS=0x"); com1_hex32(device_status); com1_puts(" CMD=0x"); com1_hex32(cmd); com1_puts("\n");
            if((ral | rah) != 0){
                com1_puts("DRV_E1000_MAC_PRESENT\n");
            }
            status->net_ready = 1;
            return;
        }
    }
    com1_puts("DRV_E1000_ABSENT\n");
    status->net_ready = 0;
}
