#include <stdint.h>
#include <stddef.h>

#define VIRTIO_PCI_VENDOR 0x1AF4
#define VIRTIO_BLK_DEV_MODERN 0x1042
#define VIRTIO_BLK_DEV_TRANSITIONAL 0x1001

#define VIRTIO_PCI_CAP_VENDOR 0x09
#define VIRTIO_PCI_CAP_COMMON_CFG 1
#define VIRTIO_PCI_CAP_NOTIFY_CFG 2
#define VIRTIO_PCI_CAP_ISR_CFG 3

#define VIRTIO_STATUS_ACK 1
#define VIRTIO_STATUS_DRIVER 2
#define VIRTIO_STATUS_DRIVER_OK 4
#define VIRTIO_STATUS_FEATURES_OK 8

#define OFF_DRIVER_FEAT_SEL    0x08
#define OFF_DRIVER_FEAT        0x0C
#define OFF_DEVICE_STATUS      0x14
#define OFF_QUEUE_SELECT       0x16
#define OFF_QUEUE_SIZE         0x18
#define OFF_QUEUE_ENABLE       0x1C
#define OFF_QUEUE_NOTIFY_OFF   0x1E
#define OFF_QUEUE_DESC_LO      0x20
#define OFF_QUEUE_DESC_HI      0x24
#define OFF_QUEUE_AVAIL_LO     0x28
#define OFF_QUEUE_AVAIL_HI     0x2C
#define OFF_QUEUE_USED_LO      0x30
#define OFF_QUEUE_USED_HI      0x34

#define VRING_DESC_F_NEXT 1
#define VRING_DESC_F_WRITE 2
#define VIRTIO_BLK_T_IN 0

struct vr_desc { uint64_t addr; uint32_t len; uint16_t flags; uint16_t next; };
struct vr_avail { uint16_t flags; uint16_t idx; uint16_t ring[8]; };
struct vr_used_elem { uint32_t id; uint32_t len; };
struct vr_used { uint16_t flags; uint16_t idx; struct vr_used_elem ring[8]; };
struct vblk_req_hdr { uint32_t type; uint32_t reserved; uint64_t sector; };

__attribute__((aligned(4096))) static uint8_t qregion[12288];
__attribute__((aligned(16))) static struct vblk_req_hdr req_hdr;
__attribute__((aligned(16))) static uint8_t sector_buf[512];
__attribute__((aligned(16))) static uint8_t req_status;

static inline void outl(uint16_t p, uint32_t v){ __asm__ volatile("outl %0,%1"::"a"(v),"Nd"(p)); }
static inline uint32_t inl(uint16_t p){ uint32_t v; __asm__ volatile("inl %1,%0":"=a"(v):"Nd"(p)); return v; }

static inline void com1_out(char c){ __asm__ volatile("outb %0, %1" : : "a"((uint8_t)c), "Nd"((uint16_t)0x3F8)); }
static void com1_puts(const char *s){ while(*s) com1_out(*s++); }
static void com1_hex8(uint8_t v){ const char* h="0123456789ABCDEF"; com1_out(h[(v>>4)&0xF]); com1_out(h[v&0xF]); }
static void com1_hex16(uint16_t v){ com1_hex8((uint8_t)(v>>8)); com1_hex8((uint8_t)v); }
static void com1_hex32(uint32_t v){ com1_hex16((uint16_t)(v>>16)); com1_hex16((uint16_t)v); }
static void com1_hex64(uint64_t v){ com1_hex32((uint32_t)(v>>32)); com1_hex32((uint32_t)v); }

static inline uint8_t mmio_r8(volatile uint8_t* b, uint32_t o){ return *(volatile uint8_t*)(b+o); }
static inline uint16_t mmio_r16(volatile uint8_t* b, uint32_t o){ return *(volatile uint16_t*)(void*)(b+o); }
static inline uint32_t mmio_r32(volatile uint8_t* b, uint32_t o){ return *(volatile uint32_t*)(void*)(b+o); }
static inline void mmio_w8(volatile uint8_t* b, uint32_t o, uint8_t v){ *(volatile uint8_t*)(b+o)=v; }
static inline void mmio_w16(volatile uint8_t* b, uint32_t o, uint16_t v){ *(volatile uint16_t*)(void*)(b+o)=v; }
static inline void mmio_w32(volatile uint8_t* b, uint32_t o, uint32_t v){ *(volatile uint32_t*)(void*)(b+o)=v; }

static uint32_t pci_cfg_read32(uint8_t bus, uint8_t slot, uint8_t func, uint8_t off){
  uint32_t a = 0x80000000u | ((uint32_t)bus<<16) | ((uint32_t)slot<<11) | ((uint32_t)func<<8) | (off & 0xFC);
  outl(0xCF8, a); return inl(0xCFC);
}
static uint8_t pci_cfg_read8(uint8_t bus, uint8_t slot, uint8_t func, uint8_t off){
  uint32_t v=pci_cfg_read32(bus,slot,func,off); return (uint8_t)((v >> ((off & 3u)*8u)) & 0xFFu);
}

void ax_kdisk_modern_probe(void){
  com1_puts("KDISK_BUILD_ID=20260303T_NOTIFY_USED_GATE\n");

  uint8_t bus=0,slot=0,func=0; int found=0;
  for(uint16_t b=0;b<256 && !found;b++) for(uint8_t s=0;s<32 && !found;s++) for(uint8_t f=0;f<8 && !found;f++){
    uint32_t id=pci_cfg_read32((uint8_t)b,s,f,0x00); uint16_t ven=(uint16_t)(id&0xFFFFu), dev=(uint16_t)(id>>16);
    if(ven==VIRTIO_PCI_VENDOR && (dev==VIRTIO_BLK_DEV_MODERN || dev==VIRTIO_BLK_DEV_TRANSITIONAL)){ bus=(uint8_t)b; slot=s; func=f; found=1; }
  }
  if(!found){ com1_puts("KDISK_LBA0_FAIL\n"); return; }

  uint32_t bar4_lo = pci_cfg_read32(bus,slot,func,0x20);
  uint32_t bar5_hi = pci_cfg_read32(bus,slot,func,0x24);
  uint32_t type = (bar4_lo >> 1) & 0x3u;
  uint64_t bar4_base = (type==0x2u) ? (((uint64_t)bar5_hi<<32) | (uint64_t)(bar4_lo & ~0xFu)) : (uint64_t)(bar4_lo & ~0xFu);

  volatile uint8_t *common=0, *notify_base=0, *isr=0;
  uint32_t notify_off=0, notify_mult=0;

  uint8_t cap=pci_cfg_read8(bus,slot,func,0x34);
  while(cap){
    uint8_t id=pci_cfg_read8(bus,slot,func,cap), next=pci_cfg_read8(bus,slot,func,cap+1);
    if(id==VIRTIO_PCI_CAP_VENDOR){
      uint8_t t=pci_cfg_read8(bus,slot,func,cap+3), bar=pci_cfg_read8(bus,slot,func,cap+4);
      uint32_t off=pci_cfg_read32(bus,slot,func,cap+8);
      if(bar==4){
        if(t==VIRTIO_PCI_CAP_COMMON_CFG) common=(volatile uint8_t*)(uintptr_t)(bar4_base + off);
        else if(t==VIRTIO_PCI_CAP_NOTIFY_CFG){ notify_base=(volatile uint8_t*)(uintptr_t)(bar4_base + off); notify_off=off; notify_mult=pci_cfg_read32(bus,slot,func,cap+16); }
        else if(t==VIRTIO_PCI_CAP_ISR_CFG){ isr=(volatile uint8_t*)(uintptr_t)(bar4_base + off); }
      }
    }
    cap=next;
  }
  if(!common || !notify_base || !isr){ com1_puts("KDISK_LBA0_FAIL\n"); return; }

  mmio_w8(common, OFF_DEVICE_STATUS, 0);
  mmio_w8(common, OFF_DEVICE_STATUS, VIRTIO_STATUS_ACK);
  mmio_w8(common, OFF_DEVICE_STATUS, (uint8_t)(mmio_r8(common, OFF_DEVICE_STATUS)|VIRTIO_STATUS_DRIVER));
  mmio_w32(common, OFF_DRIVER_FEAT_SEL, 0); mmio_w32(common, OFF_DRIVER_FEAT, 0);
  mmio_w32(common, OFF_DRIVER_FEAT_SEL, 1); mmio_w32(common, OFF_DRIVER_FEAT, 0x00000001u);
  mmio_w8(common, OFF_DEVICE_STATUS, (uint8_t)(mmio_r8(common, OFF_DEVICE_STATUS)|VIRTIO_STATUS_FEATURES_OK));

  mmio_w16(common, OFF_QUEUE_SELECT, 0);
  uint16_t qsz=mmio_r16(common, OFF_QUEUE_SIZE);
  uint16_t qnoff=mmio_r16(common, OFF_QUEUE_NOTIFY_OFF);
  if(qsz==0 || qsz==0xFFFF){ com1_puts("KDISK_LBA0_FAIL\n"); return; }
  if(qsz>8) qsz=8;

  uint32_t desc_sz=16u*qsz, avail_sz=4u+2u*qsz, used_off=(desc_sz+avail_sz+4095u)&~4095u;
  struct vr_desc *desc=(struct vr_desc*)(void*)(qregion+0);
  struct vr_avail *avail=(struct vr_avail*)(void*)(qregion+desc_sz);
  struct vr_used *used=(struct vr_used*)(void*)(qregion+used_off);
  for(size_t i=0;i<sizeof(qregion);i++) qregion[i]=0;

  req_hdr.type=VIRTIO_BLK_T_IN; req_hdr.reserved=0; req_hdr.sector=0; req_status=0xFF;
  desc[0].addr=(uint64_t)(uintptr_t)&req_hdr; desc[0].len=sizeof(req_hdr); desc[0].flags=VRING_DESC_F_NEXT; desc[0].next=1;
  desc[1].addr=(uint64_t)(uintptr_t)&sector_buf[0]; desc[1].len=512; desc[1].flags=VRING_DESC_F_NEXT|VRING_DESC_F_WRITE; desc[1].next=2;
  desc[2].addr=(uint64_t)(uintptr_t)&req_status; desc[2].len=1; desc[2].flags=VRING_DESC_F_WRITE; desc[2].next=0;

  uint64_t dpa=(uint64_t)(uintptr_t)desc, apa=(uint64_t)(uintptr_t)avail, upa=(uint64_t)(uintptr_t)used;
  mmio_w16(common, OFF_QUEUE_SELECT, 0);
  mmio_w16(common, OFF_QUEUE_SIZE, qsz);
  mmio_w32(common, OFF_QUEUE_DESC_LO, (uint32_t)dpa);
  mmio_w32(common, OFF_QUEUE_DESC_HI, (uint32_t)(dpa>>32));
  mmio_w32(common, OFF_QUEUE_AVAIL_LO, (uint32_t)apa);
  mmio_w32(common, OFF_QUEUE_AVAIL_HI, (uint32_t)(apa>>32));
  mmio_w32(common, OFF_QUEUE_USED_LO, (uint32_t)upa);
  mmio_w32(common, OFF_QUEUE_USED_HI, (uint32_t)(upa>>32));
  mmio_w16(common, OFF_QUEUE_ENABLE, 1);
  mmio_w8(common, OFF_DEVICE_STATUS, (uint8_t)(mmio_r8(common, OFF_DEVICE_STATUS)|VIRTIO_STATUS_DRIVER_OK));

  avail->flags=0;
  avail->ring[0]=0;
  avail->idx=1;
  com1_puts("QNOFF_RD="); com1_hex16(qnoff); com1_puts(" MULT="); com1_hex32(notify_mult); com1_puts("\n");
  com1_puts("AVAIL_IDX="); com1_hex16(avail->idx); com1_puts("\n");
  com1_puts("AVAIL_RING0="); com1_hex16(avail->ring[0]); com1_puts("\n");
  com1_puts("DESC0 addr=0x"); com1_hex64(desc[0].addr); com1_puts(" len="); com1_hex32(desc[0].len); com1_puts(" flags="); com1_hex16(desc[0].flags); com1_puts(" next="); com1_hex16(desc[0].next); com1_puts("\n");
  __asm__ volatile("mfence" ::: "memory");
  com1_puts("MFENCE_OK\n");

  volatile uint8_t *notify_ptr = (volatile uint8_t*)(uintptr_t)(bar4_base + notify_off + ((uint64_t)qnoff * (uint64_t)notify_mult));
  com1_puts("NOTIFY_PTR=0x"); com1_hex64((uint64_t)(uintptr_t)notify_ptr); com1_puts("\n");
  *(volatile uint16_t*)(notify_ptr)=0;
  com1_puts("NOTIFY_WRITE=mmio16 val=0\n");

  uint8_t isrv = *isr;
  com1_puts("ISR=0x"); com1_hex8(isrv); com1_puts("\n");

  uint32_t spin=5000000; while(spin-- && used->idx==0){ __asm__ volatile("pause"); }
  com1_puts("USED_IDX="); com1_hex16(used->idx); com1_puts("\n");
  com1_puts("STATUS_BYTE=0x"); com1_hex8(req_status); com1_puts("\n");
  if(used->idx>0 && req_status==0) com1_puts("KDISK_LBA0_OK\n"); else com1_puts("KDISK_LBA0_FAIL\n");
}
