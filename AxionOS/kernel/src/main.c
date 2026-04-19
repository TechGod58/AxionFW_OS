#include <stdint.h>
#include <stddef.h>
#include "axion/bootinfo.h"
#include "axion/hooks.h"
#include "axion/telemetry.h"
#include "axion/console.h"
#include "axion/panic.h"
#include "axion/drivers.h"
#include "axion/subsys/memory.h"
#include "axion/subsys/scheduler.h"
#include "axion/subsys/security.h"
#include "axion/subsys/syscall.h"
#include "axion/subsys/irq.h"
#include "axion/subsys/time.h"
#include "axion/subsys/ipc.h"
#include "axion/subsys/bus.h"
#include "axion/subsys/parallel_guard.h"
#include "axion/subsys/driver.h"
#include "axion/subsys/userland.h"
#include "axion/subsys/lifecycle.h"
#include "axion/runtime/e_runtime.h"
#include "axion/runtime/qm.h"
#include "axion/runtime/ig.h"
#include "axion/runtime/ledger.h"
#include "axion/runtime/qecc.h"
#include "axion/runtime/smart_driver_handoff.h"
#include "axion/runtime/parallel_cubed_hardware_guard.h"

typedef struct { ax_bootinfo_t *bi; } ax_boot_ctx_t;

static void hook_early(void *ctx);
static void hook_mem_early(void *ctx);
static void hook_mm_init(void *ctx);
static void hook_irq_init(void *ctx);
static void hook_time_init(void *ctx);
static void hook_sched_init(void *ctx);
static void hook_ipc_init(void *ctx);
static void hook_security_init(void *ctx);
static void hook_bus_init(void *ctx);
static void hook_driver_init(void *ctx);
static void hook_syscall_init(void *ctx);
static void hook_userland_init(void *ctx);
static void hook_late(void *ctx);
void ax_kdisk_modern_probe(void);

static inline void com1_out(char c){ __asm__ volatile("outb %0, %1" : : "a"((uint8_t)c), "Nd"((uint16_t)0x3F8)); }
static void com1_puts(const char *s){ while(*s) com1_out(*s++); }
static void com1_hex8(uint8_t v){ const char* h="0123456789ABCDEF"; com1_out(h[(v>>4)&0xF]); com1_out(h[v&0xF]); }
static void com1_hex16(uint16_t v){ com1_hex8((uint8_t)(v>>8)); com1_hex8((uint8_t)(v&0xFF)); }
static void com1_hex32(uint32_t v){ com1_hex16((uint16_t)(v>>16)); com1_hex16((uint16_t)(v&0xFFFF)); }
static void com1_hex64(uint64_t v){ com1_hex32((uint32_t)(v>>32)); com1_hex32((uint32_t)(v&0xFFFFFFFFu)); }

static inline void outl(uint16_t p, uint32_t v){ __asm__ volatile("outl %0,%1"::"a"(v),"Nd"(p)); }
static inline void outw(uint16_t p, uint16_t v){ __asm__ volatile("outw %0,%1"::"a"(v),"Nd"(p)); }
static inline void outb(uint16_t p, uint8_t v){ __asm__ volatile("outb %0,%1"::"a"(v),"Nd"(p)); }
static inline uint32_t inl(uint16_t p){ uint32_t v; __asm__ volatile("inl %1,%0":"=a"(v):"Nd"(p)); return v; }
static inline uint16_t inw(uint16_t p){ uint16_t v; __asm__ volatile("inw %1,%0":"=a"(v):"Nd"(p)); return v; }
static inline uint8_t inb(uint16_t p){ uint8_t v; __asm__ volatile("inb %1,%0":"=a"(v):"Nd"(p)); return v; }
static inline void io_wait(void){ __asm__ volatile("outb %0, $0x80" : : "a"((uint8_t)0)); }

static uint32_t pci_cfg_read32(uint8_t bus, uint8_t slot, uint8_t func, uint8_t off){
    uint32_t a = 0x80000000u | ((uint32_t)bus<<16) | ((uint32_t)slot<<11) | ((uint32_t)func<<8) | (off & 0xFC);
    outl(0xCF8, a);
    return inl(0xCFC);
}
static uint16_t pci_cfg_read16(uint8_t bus, uint8_t slot, uint8_t func, uint8_t off){
    uint32_t v = pci_cfg_read32(bus,slot,func,off);
    return (uint16_t)((v >> ((off & 2u)*8u)) & 0xFFFFu);
}
static void pci_cfg_write16(uint8_t bus, uint8_t slot, uint8_t func, uint8_t off, uint16_t val){
    uint32_t a = 0x80000000u | ((uint32_t)bus<<16) | ((uint32_t)slot<<11) | ((uint32_t)func<<8) | (off & 0xFC);
    outl(0xCF8, a);
    uint32_t old = inl(0xCFC);
    uint32_t sh = (uint32_t)((off & 2u)*8u);
    uint32_t nw = (old & ~(0xFFFFu << sh)) | ((uint32_t)val << sh);
    outl(0xCF8, a);
    outl(0xCFC, nw);
}

static void serial_probe_pci_net_disk(void){
    int net_found = 0, disk_found = 0;
    for (uint16_t bus=0; bus<256; bus++) for(uint8_t slot=0; slot<32; slot++) for(uint8_t func=0; func<8; func++){
        uint32_t id = pci_cfg_read32((uint8_t)bus,slot,func,0x00);
        if((id & 0xFFFFu)==0xFFFFu) continue;
        uint8_t base_class = (uint8_t)(pci_cfg_read32((uint8_t)bus,slot,func,0x08)>>24);
        if(base_class==0x02) net_found=1;
        if(base_class==0x01) disk_found=1;
        if(net_found && disk_found) goto done;
    }
 done:
    com1_puts(net_found?"NET_PCI_FOUND\n":"NET_PCI_NONE\n");
    com1_puts(disk_found?"DISK_PCI_FOUND\n":"DISK_PCI_NONE\n");
}

#define VRING_DESC_F_NEXT  1
#define VRING_DESC_F_WRITE 2
struct vr_desc { uint64_t addr; uint32_t len; uint16_t flags; uint16_t next; };
struct vr_avail { uint16_t flags; uint16_t idx; uint16_t ring[8]; };
struct vr_used_elem { uint32_t id; uint32_t len; };
struct vr_used { uint16_t flags; uint16_t idx; struct vr_used_elem ring[8]; };
struct vblk_req_hdr { uint32_t type; uint32_t reserved; uint64_t sector; };

__attribute__((aligned(4096))) static uint8_t vr_region[12288];
__attribute__((aligned(16))) static struct vblk_req_hdr req_hdr;
__attribute__((aligned(16))) static uint8_t sector_buf[512];
__attribute__((aligned(16))) static uint8_t req_status;

static void kernel_disk_full_probe(void){
    com1_puts("KDISK_BUILD_ID=20260302T1610Z\n");
    uint8_t f_bus=0, f_slot=0, f_func=0; int found=0;
    for(uint16_t bus=0; bus<256 && !found; bus++) for(uint8_t slot=0; slot<32 && !found; slot++) for(uint8_t func=0; func<8 && !found; func++){
        uint32_t id = pci_cfg_read32((uint8_t)bus,slot,func,0x00);
        uint16_t ven=(uint16_t)(id&0xFFFFu), dev=(uint16_t)(id>>16);
        if(ven==0x1AF4 && (dev==0x1001 || dev==0x1042)) { f_bus=(uint8_t)bus; f_slot=slot; f_func=func; found=1; }
    }
    if(!found){ com1_puts("KDISK_LBA0_FAIL\n"); return; }

    uint16_t cmd = pci_cfg_read16(f_bus,f_slot,f_func,0x04);
    cmd |= (uint16_t)((1u<<0) | (1u<<2));
    pci_cfg_write16(f_bus,f_slot,f_func,0x04,cmd);
    cmd = pci_cfg_read16(f_bus,f_slot,f_func,0x04);
    com1_puts("KDISK_PCI_CMD=0x"); com1_hex16(cmd); com1_puts("\n");

    uint32_t bar0 = pci_cfg_read32(f_bus,f_slot,f_func,0x10);
    com1_puts("KDISK_BAR0_RAW=0x"); com1_hex32(bar0);
    if((bar0 & 0x1u)==0){
        com1_puts(" KDISK_BAR0_TYPE=MMIO BASE=0x"); com1_hex32(bar0 & ~0xFu); com1_puts("\n");
        com1_puts("KDISK_LBA0_FAIL\n"); return;
    }
    uint16_t io = (uint16_t)(bar0 & ~0x3u);
    com1_puts(" KDISK_BAR0_TYPE=IO BASE=0x"); com1_hex16(io); com1_puts("\n");

    outb(io + 0x12, 0);
    outb(io + 0x12, 1);
    com1_puts("KDISK_ST_A_WR=0x01 RD=0x"); com1_hex8(inb(io + 0x12)); com1_puts("\n");
    outb(io + 0x12, (uint8_t)(1|2));
    com1_puts("KDISK_ST_D_WR=0x03 RD=0x"); com1_hex8(inb(io + 0x12)); com1_puts("\n");
    outb(io + 0x12, (uint8_t)(1|2|8));
    com1_puts("KDISK_ST_FOK_WR=0x0B RD=0x"); com1_hex8(inb(io + 0x12)); com1_puts("\n");

    outw(io + 0x0E, 0);
    uint16_t qmax = inw(io + 0x0C);
    if(qmax < 3){ com1_puts("KDISK_LBA0_FAIL\n"); return; }
    uint16_t Q = (qmax > 8) ? 8 : qmax;
    com1_puts("KDISK_QNUM_MAX="); com1_hex16(qmax); com1_puts("\n");

    for(size_t i=0;i<sizeof(vr_region);i++) vr_region[i]=0;
    uint32_t desc_sz = 16u * (uint32_t)Q;
    uint32_t avail_sz = 4u + 2u * (uint32_t)Q;
    uint32_t used_off = (desc_sz + avail_sz + 4095u) & ~4095u;
    struct vr_desc *desc = (struct vr_desc *)(void *)(vr_region + 0);
    struct vr_avail *avail = (struct vr_avail *)(void *)(vr_region + desc_sz);
    struct vr_used *used = (struct vr_used *)(void *)(vr_region + used_off);

    com1_puts("KDISK_QBASE=0x"); com1_hex64((uint64_t)(uintptr_t)vr_region);
    com1_puts(" USED_OFF=0x"); com1_hex32(used_off);
    com1_puts(" Q="); com1_hex16(Q); com1_puts("\n");

    req_hdr.type = 0; req_hdr.reserved = 0; req_hdr.sector = 0;
    for(int i=0;i<512;i++) sector_buf[i]=0;
    req_status = 0xFF;

    desc[0].addr = (uint64_t)(uintptr_t)&req_hdr; desc[0].len = sizeof(req_hdr); desc[0].flags = VRING_DESC_F_NEXT; desc[0].next = 1;
    desc[1].addr = (uint64_t)(uintptr_t)&sector_buf[0]; desc[1].len = 512; desc[1].flags = VRING_DESC_F_NEXT | VRING_DESC_F_WRITE; desc[1].next = 2;
    desc[2].addr = (uint64_t)(uintptr_t)&req_status; desc[2].len = 1; desc[2].flags = VRING_DESC_F_WRITE; desc[2].next = 0;

    avail->flags = 0; avail->idx = 0; used->flags = 0; used->idx = 0;

    outw(io + 0x0E, 0);
    outw(io + 0x0C, Q);
    uint32_t qpfn_wr = (uint32_t)(((uintptr_t)vr_region) >> 12);
    outl(io + 0x08, qpfn_wr);
    uint32_t qpfn_rd = inl(io + 0x08);
    com1_puts("KDISK_QSEL=0\n");
    com1_puts("KDISK_QPFN_WR=0x"); com1_hex32(qpfn_wr); com1_puts(" RD=0x"); com1_hex32(qpfn_rd); com1_puts("\n");

    outb(io + 0x12, (uint8_t)(1|2|4));
    com1_puts("KDISK_ST_DOK_WR=0x07 RD=0x"); com1_hex8(inb(io + 0x12)); com1_puts("\n");

    com1_puts("KDISK_AVAIL_IDX="); com1_hex16(avail->idx); com1_puts(" USED_IDX="); com1_hex16(used->idx); com1_puts("\n");
    avail->ring[avail->idx % Q] = 0;
    __asm__ volatile("" ::: "memory");
    avail->idx = (uint16_t)(avail->idx + 1);
    __asm__ volatile("" ::: "memory");

    com1_puts("KDISK_NOTIFY_PORT=0x"); com1_hex16((uint16_t)(io + 0x10)); com1_puts(" Q=0\n");
    com1_puts("NOTIFY_WRITE=outw\n");
    outw(io + 0x10, 0); io_wait();
    outw(io + 0x10, 0); io_wait();
    outw(io + 0x10, 0); io_wait();
    uint8_t isr1 = inb(io + 0x13);
    uint8_t isr2 = inb(io + 0x13);
    com1_puts("KDISK_ISR1=0x"); com1_hex8(isr1); com1_puts(" ISR2=0x"); com1_hex8(isr2); com1_puts("\n");

    uint32_t spin = 5000000;
    while(spin-- && used->idx == 0) { __asm__ volatile("pause"); }

    com1_puts("KDISK_USED_IDX="); com1_hex16(used->idx); com1_puts("\n");
    com1_puts("KDISK_STATUS_BYTE=0x"); com1_hex8(req_status); com1_puts("\n");
    if(used->idx == 0){ com1_puts("KDISK_LBA0_FAIL\n"); return; }
    if(req_status == 0){ com1_puts("KDISK_LBA0_OK\n"); } else { com1_puts("KDISK_LBA0_FAIL\n"); }
}

static ax_console_t g_console;

void kmain(ax_bootinfo_t *bootinfo){
    ax_telemetry_init();
    g_console.fb_base = bootinfo->fb_base;
    g_console.w = bootinfo->fb_width;
    g_console.h = bootinfo->fb_height;
    g_console.ppsl = bootinfo->fb_pixels_per_scanline;
    g_console.bpp = bootinfo->fb_bpp;
    ax_console_init(&g_console);

    ax_printf("AxionOS kernel start\n");
    com1_puts("KERNEL_MAIN_START\n");
    serial_probe_pci_net_disk();
    ax_reference_bsp_q35_init(bootinfo);
    ax_run_boot_diagnostics(bootinfo);
    ax_kdisk_modern_probe();
    ax_trace(AX_EVT_BOOT_STAGE, 0, 0, 0);

    ax_boot_ctx_t ctx = { .bi = bootinfo };
    ax_hooks_register(AX_HOOK_EARLY,         (ax_hook_t){ "early", hook_early });
    ax_hooks_register(AX_HOOK_MEM_EARLY,     (ax_hook_t){ "mem_early", hook_mem_early });
    ax_hooks_register(AX_HOOK_MM_INIT,       (ax_hook_t){ "mm_init", hook_mm_init });
    ax_hooks_register(AX_HOOK_IRQ_INIT,      (ax_hook_t){ "irq_init", hook_irq_init });
    ax_hooks_register(AX_HOOK_TIME_INIT,     (ax_hook_t){ "time_init", hook_time_init });
    ax_hooks_register(AX_HOOK_SCHED_INIT,    (ax_hook_t){ "sched_init", hook_sched_init });
    ax_hooks_register(AX_HOOK_IPC_INIT,      (ax_hook_t){ "ipc_init", hook_ipc_init });
    ax_hooks_register(AX_HOOK_SECURITY_INIT, (ax_hook_t){ "security_init", hook_security_init });
    ax_hooks_register(AX_HOOK_BUS_INIT,      (ax_hook_t){ "bus_init", hook_bus_init });
    ax_hooks_register(AX_HOOK_DRIVER_INIT,   (ax_hook_t){ "driver_init", hook_driver_init });
    ax_hooks_register(AX_HOOK_SYSCALL_INIT,  (ax_hook_t){ "syscall_init", hook_syscall_init });
    ax_hooks_register(AX_HOOK_USERLAND_INIT, (ax_hook_t){ "userland_init", hook_userland_init });
    ax_hooks_register(AX_HOOK_LATE,          (ax_hook_t){ "late", hook_late });

    for (int s=0; s<AX_HOOK_COUNT; s++){ ax_trace(AX_EVT_BOOT_STAGE, (uint64_t)s, 0, 0); ax_hooks_run((ax_hook_stage_t)s, &ctx); }
    ax_printf("AxionOS kernel idle\n");
    for(;;){ __asm__ volatile("hlt"); }
}

static void hook_early(void *c){
    (void)c;
    ax_lifecycle_init();
    ax_lifecycle_set_required_mask(
        (1ull << 0) | // memory
        (1ull << 1) | // irq
        (1ull << 2) | // time
        (1ull << 3) | // scheduler
        (1ull << 4) | // ipc
        (1ull << 5) | // security
        (1ull << 6) | // bus
        (1ull << 7) | // driver
        (1ull << 8)   // userland/runtime
    );
    ax_printf("[hook] early lifecycle=init required=0x%lx\n", ax_lifecycle_state().required_stage_mask);
}
static void hook_mem_early(void *c){ ax_boot_ctx_t *ctx=(ax_boot_ctx_t*)c; ax_printf("[hook] mem_early mmap=0x%lx size=%lu\n", ctx->bi->mmap, ctx->bi->mmap_size); }
static void hook_mm_init(void *c){
    ax_boot_ctx_t *ctx=(ax_boot_ctx_t*)c;
    ax_mem_init(ctx ? ctx->bi : (ax_bootinfo_t*)0);
    ax_mem_run_stress(4, 12);
    ax_mem_state_t ms = ax_mem_state();
    ax_mem_health_t mh = ax_mem_health();
    ax_printf("[hook] mm_init regions=%lu usable_mb=%lu total_mb=%lu tracked=%lu active=%lu hi=%lu alloc=%lu/%lu release=%lu/%lu stress=%lu fail=%lu pressure=%lu%%\n",
              ms.desc_count, (ms.usable_bytes >> 20), (ms.total_bytes >> 20), mh.tracked_pages,
              mh.active_allocations, mh.high_watermark, mh.alloc_success, mh.alloc_attempts,
              mh.release_success, mh.release_attempts, mh.stress_cycles, mh.stress_failures, mh.pressure_peak_pct);
}
static void hook_irq_init(void *c){
    ax_boot_ctx_t *ctx=(ax_boot_ctx_t*)c;
    uint64_t fw_tables = (ctx && ctx->bi && ctx->bi->rsdp != 0) ? 1 : 0;
    ax_irq_init(fw_tables);
    (void)ax_irq_enable_line(1);
    (void)ax_irq_enable_line(14);
    ax_irq_state_t before = ax_irq_state();
    ax_irq_dispatch(before.vector_base + 1);
    ax_irq_dispatch(0xFF);
    ax_irq_state_t st = ax_irq_state();
    ax_printf("[hook] irq_init base=%lu count=%lu mask_lo=0x%lx dispatch=%lu spurious=%lu\n",
              st.vector_base, st.vector_count, st.enabled_lines_mask_lo, st.dispatch_total, st.spurious_total);
}
static void hook_time_init(void *c){
    ax_boot_ctx_t *ctx=(ax_boot_ctx_t*)c;
    uint64_t caps1 = (ctx && ctx->bi) ? ctx->bi->caps1 : 0;
    ax_time_init(caps1);
    ax_time_tick(17);
    ax_time_tick(5);
    ax_time_state_t st = ax_time_state();
    ax_printf("[hook] time_init src=%lu hz=%lu ticks=%lu ms=%lu drift_ppm=%lu\n",
              (uint64_t)st.source, st.tick_hz, st.ticks, ax_time_now_ms(), st.drift_ppm_limit);
}
static void hook_sched_init(void *c){
    (void)c;
    ax_sched_init();
    ax_sched_enqueue_ex(1, 12, AX_SCHED_CLASS_SYSTEM, 2);
    ax_sched_enqueue_ex(2, 7, AX_SCHED_CLASS_USER, 1);
    ax_sched_enqueue_ex(3, 15, AX_SCHED_CLASS_REALTIME, 1);
    ax_sched_tick();
    ax_sched_tick();
    uint64_t next = ax_sched_next();
    ax_sched_run_stress(6, 12);
    ax_sched_stats_t st = ax_sched_stats();
    ax_sched_stress_state_t stress = ax_sched_stress_state();
    ax_printf("[hook] sched_init depth=%lu next_tid=%lu enq=%lu disp=%lu drop=%lu ticks=%lu epoch=%lu class=%lu stress_cycles=%lu/%lu stress_enq=%lu/%lu stress_disp=%lu stress_drop=%lu stress_ok=%lu\n",
              st.depth, next, st.enqueued_total, st.dispatched_total, st.dropped_total,
              st.tick_count, st.policy_epoch, st.last_class_dispatched,
              stress.cycles_completed, stress.cycles_requested, stress.enqueues_accepted, stress.enqueues_attempted,
              stress.dispatches, stress.drop_events, stress.last_ok);
}
static void hook_ipc_init(void *c){
    (void)c;
    ax_ipc_init(4, 8);
    (void)ax_ipc_send(1, 0xA1, 0x1001);
    (void)ax_ipc_send(1, 0xA2, 0x1002);
    uint64_t tag = 0, data = 0;
    int recv_ok = ax_ipc_recv(1, &tag, &data);
    ax_ipc_state_t st = ax_ipc_state();
    ax_printf("[hook] ipc_init recv=%d tag=0x%lx data=0x%lx depth=%lu enq=%lu deq=%lu drop=%lu\n",
              recv_ok, tag, data, st.queue_depth, st.enqueued_total, st.dequeued_total, st.dropped_total);
}
static void hook_security_init(void *c){
    ax_boot_ctx_t *ctx=(ax_boot_ctx_t*)c;
    uint64_t caps0 = (ctx && ctx->bi) ? ctx->bi->caps0 : 0;
    ax_security_init(caps0);
    int sec_policy_ok = ax_security_set_policy_checked((ax_security_policy_t){
        .default_allow = 0,
        .strict_action_allowlist = 1,
        .require_preboot_auth_level2_plus = 1,
        .deny_repair_mode_level3_plus = 1,
        .deny_debug_without_preboot_auth = 1,
        .max_rules = 64,
        .min_policy_write_level = 2,
    }, 3);
    ax_security_register_rule_ex("scheduler_policy_write", AX_CAP0_PREBOOT_AUTH, 3, 3, AX_SEC_RULE_ALLOW, AX_SEC_MATCH_EXACT, 3);
    ax_security_register_rule_ex("scheduler_tune", AX_CAP0_PREBOOT_AUTH, 2, 3, AX_SEC_RULE_ALLOW, AX_SEC_MATCH_PREFIX, 3);
    ax_security_register_rule_ex("scheduler_tune/unsafe_overclock", AX_CAP0_PREBOOT_AUTH, 2, 3, AX_SEC_RULE_DENY, AX_SEC_MATCH_EXACT, 3);
    ax_security_register_rule_ex("network_egress_open", 0, 1, 3, AX_SEC_RULE_ALLOW, AX_SEC_MATCH_EXACT, 3);
    ax_security_register_rule_ex("kernel_mem_write", AX_CAP0_PREBOOT_AUTH, 3, 3, AX_SEC_RULE_DENY, AX_SEC_MATCH_PREFIX, 3);

    // Kernel-owned network guard model (runtime bridge uses these tags/contracts).
    ax_security_net_guard_reset();
    (void)ax_security_net_guard_register_rule(0x1001, 6, 443, 0xA100, AX_NET_GUARD_RULE_ALLOW, 3);
    (void)ax_security_net_guard_register_rule(0x1001, 6, 443, 0xDEAD, AX_NET_GUARD_RULE_DENY, 3);

    uint64_t vm_launch = (uint64_t)ax_security_check("vm_launch", 0, 1);
    uint64_t dbg_enable = (uint64_t)ax_security_check("enable_kernel_debug", AX_CAP0_PREBOOT_AUTH, 3);
    uint64_t sched_tune = (uint64_t)ax_security_check("scheduler_tune/foreground_boost", AX_CAP0_PREBOOT_AUTH, 2);
    uint64_t sched_unsafe = (uint64_t)ax_security_check("scheduler_tune/unsafe_overclock", AX_CAP0_PREBOOT_AUTH, 2);
    uint64_t mem_write = (uint64_t)ax_security_check("kernel_mem_write/page_table", AX_CAP0_PREBOOT_AUTH, 3);
    uint64_t net_repo = (uint64_t)ax_security_net_guard_check(0x1001, 6, 443, 0xA100);
    uint64_t net_rogue = (uint64_t)ax_security_net_guard_check(0x1001, 6, 443, 0xDEAD);
    ax_security_selftest_result_t selftest = ax_security_selftest_rule_precedence();
    ax_security_stress_reset();
    int sec_stress_ok = ax_security_run_stress_cycle(3, AX_CAP0_PREBOOT_AUTH);
    ax_security_decision_t last = ax_security_last_decision();
    ax_net_guard_decision_t net_last = ax_security_net_guard_last_decision();
    ax_net_guard_stats_t ngs = ax_security_net_guard_stats();
    ax_security_stress_state_t stress = ax_security_stress_state();
    ax_sched_stats_t sst = ax_sched_stats();
    ax_printf("[hook] security_init policy_ok=%d vm_launch=%lu kernel_debug=%lu sched_tune=%lu sched_unsafe=%lu mem_write=%lu net_repo=%lu net_rogue=%lu net_allow=%lu/%lu denied=%lu total=%lu deny_rule=%lu selftest=%lu/%lu stress_ok=%d stress_cycle=%lu stress_actions=%lu unexpected=%lu stress_net=%lu net_unexpected=%lu precedence_fail=%lu last_reason=%lu rule_idx=%ld net_last=%lu net_rule=%ld sec_epoch=%lu sched_epoch=%lu\n",
              sec_policy_ok, vm_launch, dbg_enable, sched_tune, sched_unsafe, mem_write, net_repo, net_rogue, ngs.allowed, ngs.total,
              ax_security_decisions_denied(), ax_security_decisions_total(),
              ax_security_reason_count(AX_SEC_DENY_RULE_EFFECT), selftest.passed, selftest.total,
              sec_stress_ok, stress.cycles_total, stress.actions_checked, stress.actions_unexpected,
              stress.network_checked, stress.network_unexpected, stress.precedence_failed, (uint64_t)last.reason,
              (long)last.matched_rule_index, (uint64_t)net_last.reason, (long)net_last.matched_rule_index, last.policy_epoch, sst.policy_epoch);
}
static void hook_bus_init(void *c){
    ax_boot_ctx_t *ctx=(ax_boot_ctx_t*)c;
    uint64_t rsdp = (ctx && ctx->bi) ? ctx->bi->rsdp : 0;
    ax_parallel_guard_init(
        AX_PCGUARD_ENABLED,
        AX_PCGUARD_STRICT_MODE,
        AX_PCGUARD_INVENTORY_REQUIRED,
        (AX_SDF_HANDOFF_RESOLVED_TOTAL > 0) ? 1 : 0,
        AX_SDF_HANDOFF_READY
    );
    ax_parallel_guard_set_policy_masks(AX_PCGUARD_ALLOW_MASK, AX_PCGUARD_DENY_MASK);
    ax_bus_init(rsdp);
    ax_bus_note_device(0x06, 0x00);
    ax_bus_note_device(0x01, 0x06);
    ax_bus_note_device(0x02, 0x00);
    ax_bus_state_t st = ax_bus_state();
    ax_parallel_guard_state_t g = ax_parallel_guard_state();
    ax_printf("[hook] bus_init acpi=%lu seg=%lu rounds=%lu dev=%lu bridge=%lu endpoint=%lu guard_allow=%lu guard_deny=%lu guard_reason=%lu\n",
              st.acpi_present, st.segment_count, st.scan_rounds, st.devices_seen, st.bridges_seen, st.endpoints_seen,
              st.guard_allowed, st.guard_denied, g.last_reason);
}
static void hook_driver_init(void *c){
    ax_boot_ctx_t *ctx=(ax_boot_ctx_t*)c;
    uint64_t caps0 = (ctx && ctx->bi) ? ctx->bi->caps0 : 0;
    uint64_t caps1 = (ctx && ctx->bi) ? ctx->bi->caps1 : 0;
    ax_driver_init();
    int q35 = ax_driver_activate("q35_chipset", caps0, caps1);
    int blk = ax_driver_activate("virtio_blk_modern", caps0, caps1);
    int net = ax_driver_activate("e1000_probe", caps0, caps1);
    ax_driver_state_t st = ax_driver_state();
    ax_printf("[hook] driver_init reg=%lu active=%lu blocked=%lu q35=%d blk=%d net=%d epoch=%lu handoff_ready=%lu token_hi=0x%lx token_lo=0x%lx handoff_resolved=%lu handoff_synth=%lu handoff_artifacts=%lu\n",
              st.registered_total, st.active_total, st.blocked_total, q35, blk, net, st.policy_epoch,
              st.handoff_ready, st.handoff_token_hi, st.handoff_token_lo,
              st.handoff_resolved_total, st.handoff_synthesized_total, st.handoff_signed_artifacts_total);
}
static void hook_syscall_init(void *c){
    ax_boot_ctx_t *ctx=(ax_boot_ctx_t*)c;
    uint64_t caps0 = (ctx && ctx->bi) ? ctx->bi->caps0 : 0;
    ax_syscall_init(caps0);

    // Direct scheduler policy writes must be rejected outside syscall mediation.
    int direct_denied = ax_sched_set_policy_checked((ax_sched_policy_t){
        .mode = AX_SCHED_POLICY_WEIGHTED_RR,
        .queue_capacity = 52,
        .min_priority = 0,
        .max_priority = 31,
        .default_quantum = 2,
        .aging_step = 1,
        .aging_interval_ticks = 2,
        .class_weights = { 1, 3, 5, 7 },
        .min_policy_write_level = 3,
    }, 3) == 0;

    int write_ok = ax_syscall_sched_policy_write(
        "scheduler_policy_write",
        (ax_sched_policy_t){
            .mode = AX_SCHED_POLICY_WEIGHTED_RR,
            .queue_capacity = 56,
            .min_priority = 0,
            .max_priority = 31,
            .default_quantum = 2,
            .aging_step = 1,
            .aging_interval_ticks = 2,
            .class_weights = { 1, 3, 4, 8 },
            .min_policy_write_level = 3,
        },
        3,
        AX_CAP0_PREBOOT_AUTH
    );

    int tune_ok = ax_syscall_sched_policy_write(
        "scheduler_tune/foreground_boost",
        (ax_sched_policy_t){
            .mode = AX_SCHED_POLICY_WEIGHTED_RR,
            .queue_capacity = 60,
            .min_priority = 0,
            .max_priority = 31,
            .default_quantum = 2,
            .aging_step = 1,
            .aging_interval_ticks = 2,
            .class_weights = { 1, 4, 5, 8 },
            .min_policy_write_level = 3,
        },
        2,
        AX_CAP0_PREBOOT_AUTH
    );

    int tune_unsafe = ax_syscall_sched_policy_write(
        "scheduler_tune/unsafe_overclock",
        (ax_sched_policy_t){
            .mode = AX_SCHED_POLICY_WEIGHTED_RR,
            .queue_capacity = 64,
            .min_priority = 0,
            .max_priority = 31,
            .default_quantum = 1,
            .aging_step = 0,
            .aging_interval_ticks = 1,
            .class_weights = { 1, 1, 1, 16 },
            .min_policy_write_level = 3,
        },
        2,
        AX_CAP0_PREBOOT_AUTH
    );

    int net_allow = ax_syscall_network_egress_open(0x1001, 6, 443, 0xA100, 1, 0);
    int net_block = ax_syscall_network_egress_open(0x1001, 6, 443, 0xDEAD, 1, 0);
    int net_bad = ax_syscall_network_egress_open(0, 6, 443, 0xA100, 1, 0);

    ax_syscall_policy_stats_t ss = ax_syscall_policy_stats();
    ax_sched_stats_t st = ax_sched_stats();
    ax_printf("[hook] syscall_init direct_denied=%d write_ok=%d tune_ok=%d tune_unsafe=%d net_allow=%d net_block=%d net_bad=%d allowed=%lu deny_sec=%lu deny_gate=%lu net_allowed=%lu net_den_sec=%lu net_den_policy=%lu net_den_bad=%lu epoch=%lu\n",
              direct_denied, write_ok, tune_ok, tune_unsafe, net_allow, net_block, net_bad,
              ss.allowed, ss.denied_security, ss.denied_sched_gate, ss.net_allowed, ss.net_denied_security,
              ss.net_denied_policy, ss.net_denied_bad_input, st.policy_epoch);
}
static void hook_userland_init(void *c){
    ax_boot_ctx_t *ctx=(ax_boot_ctx_t*)c;
    uint64_t caps0 = (ctx && ctx->bi) ? ctx->bi->caps0 : 0;
    ax_userland_init(3);
    int q_shell = ax_userland_queue_service("shell/ui", 1, caps0);
    int q_secure = ax_userland_queue_service("secure/settings", 2, caps0);
    int q_diag = ax_userland_queue_service("diag/telemetry", 1, caps0);
    int l1 = ax_userland_launch_next();
    int l2 = ax_userland_launch_next();

    axion_ledger_init();
    axion_qm_init();
    (void)axion_qm_set_policy_checked((axion_qm_policy_t){
        .strict_forward_only = 1,
        .allow_recovery_anytime = 1,
        .min_transition_level = 1,
        .min_policy_write_level = 2,
    }, 3);
    int qm_secure = axion_qm_transition("secure_init");
    int qm_ready = axion_qm_transition("runtime_ready");
    int qm_bad = axion_qm_transition("cold_boot");

    axion_e_init();
    (void)axion_e_set_policy_checked((axion_e_policy_t){
        .enforce_ig = 1,
        .require_ledger = 1,
        .require_qecc = 1,
        .sandbox_required_for_external = 1,
        .min_policy_write_level = 2,
        .max_task_name_len = 128,
    }, 3);
    int exec_native = axion_e_execute_ex("userland/session/bootstrap", AXION_E_TASK_USER_APP, 1, 0, 1);
    int exec_module = axion_e_execute_ex("module/attach/builder_demo", AXION_E_TASK_MODULE_ATTACH, 2, 0, 1);
    int exec_install_ok = axion_e_execute_ex("installer/windows/setup.exe", AXION_E_TASK_INSTALLER, 2, 1, 1);
    int exec_install_denied = axion_e_execute_ex("installer/windows/escape_attempt.exe", AXION_E_TASK_INSTALLER, 2, 1, 0);

    ax_userland_state_t st = ax_userland_state();
    axion_e_state_t est = axion_e_state();
    axion_qm_state_t qst = axion_qm_state();
    axion_ig_state_t ist = axion_ig_state();
    axion_ledger_state_t lst = axion_ledger_state();
    axion_qecc_state_t qec = axion_qecc_state();
    ax_printf("[hook] userland_init queued=%lu launched=%lu denied=%lu ready=%lu q_shell=%d q_secure=%d q_diag=%d l1=%d l2=%d qm_phase=%lu qm_secure=%d qm_ready=%d qm_bad=%d e_ok=%d/%d/%d e_denied=%d e_total=%lu ig=%lu/%lu ledger=%lu qecc=%lu\n",
              st.queued, st.launched, st.denied, st.ready_services, q_shell, q_secure, q_diag, l1, l2,
              (uint64_t)qst.phase, qm_secure, qm_ready, qm_bad, exec_native, exec_module, exec_install_ok, exec_install_denied,
              est.total_exec, ist.allowed, ist.denied, lst.commits, qec.attached_total);
}
static void hook_late(void *c){
    (void)c;
    ax_mem_state_t mem = ax_mem_state();
    ax_mem_health_t memh = ax_mem_health();
    ax_sched_stats_t sch = ax_sched_stats();
    ax_sched_stress_state_t schs = ax_sched_stress_state();
    ax_security_stress_state_t secs = ax_security_stress_state();
    ax_irq_state_t irq = ax_irq_state();
    ax_time_state_t tim = ax_time_state();
    ax_ipc_state_t ipc = ax_ipc_state();
    ax_bus_state_t bus = ax_bus_state();
    ax_driver_state_t drv = ax_driver_state();
    ax_userland_state_t usr = ax_userland_state();
    axion_e_state_t est = axion_e_state();
    axion_qm_state_t qst = axion_qm_state();

    ax_lifecycle_mark_stage(0, mem.usable_bytes > 0 && memh.tracked_pages > 0 && memh.stress_failures == 0 && memh.active_allocations == 0);
    ax_lifecycle_mark_stage(1, irq.initialized && irq.dispatch_total > 0);
    ax_lifecycle_mark_stage(2, tim.initialized && tim.monotonic_ms > 0);
    ax_lifecycle_mark_stage(3, sch.policy_epoch > 0 && schs.last_ok && schs.dispatches > 0);
    ax_lifecycle_mark_stage(4, ipc.initialized && ipc.enqueued_total >= ipc.dequeued_total);
    ax_lifecycle_mark_stage(5, ax_security_decisions_total() > 0 && secs.last_ok && secs.actions_unexpected == 0 && secs.network_unexpected == 0);
    ax_lifecycle_mark_stage(6, bus.initialized && bus.devices_seen > 0);
    uint64_t drv_handoff_ok = (drv.handoff_ready == 0) ? 1 : (drv.handoff_signed_artifacts_total > 0);
    ax_lifecycle_mark_stage(7, drv.initialized && drv.active_total > 0 && drv_handoff_ok);
    ax_lifecycle_mark_stage(8, usr.initialized && usr.launched > 0 && est.total_exec > 0 && qst.phase == AXION_QM_PHASE_RUNTIME_READY);
    ax_lifecycle_finalize();

    ax_lifecycle_state_t life = ax_lifecycle_state();
    ax_printf("[hook] late required=0x%lx stage_mask=0x%lx stage_ok=0x%lx checks=%lu failed=%lu warnings=%lu health=%lu finalized=%lu ready=%lu\n",
              life.required_stage_mask, life.stage_mask, life.stage_ok_mask, life.ownership_checks, life.ownership_failed,
              life.warnings, life.health_score, life.finalized, ax_lifecycle_is_ready());
}





