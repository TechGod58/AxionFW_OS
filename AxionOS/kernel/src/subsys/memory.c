#include "axion/subsys/memory.h"
#include "axion/telemetry.h"

#define AX_MEM_TRACKED_PAGE_CAP 8192

static ax_mem_state_t g_state;
static ax_mem_health_t g_health;
static uint8_t g_page_used[AX_MEM_TRACKED_PAGE_CAP];
static uint64_t g_page_count = 0;
static uint64_t g_page_base = 0;
static uint64_t g_page_next_hint = 0;

static uint32_t rd_u32(const uint8_t *p) {
    return ((uint32_t)p[0])
        | ((uint32_t)p[1] << 8)
        | ((uint32_t)p[2] << 16)
        | ((uint32_t)p[3] << 24);
}

static uint64_t rd_u64(const uint8_t *p) {
    return ((uint64_t)p[0])
        | ((uint64_t)p[1] << 8)
        | ((uint64_t)p[2] << 16)
        | ((uint64_t)p[3] << 24)
        | ((uint64_t)p[4] << 32)
        | ((uint64_t)p[5] << 40)
        | ((uint64_t)p[6] << 48)
        | ((uint64_t)p[7] << 56);
}

static uint64_t clamp_u64(uint64_t value, uint64_t lo, uint64_t hi) {
    if (value < lo) return lo;
    if (value > hi) return hi;
    return value;
}

static void reset_tracking(void) {
    g_page_count = 0;
    g_page_base = 0;
    g_page_next_hint = 0;
    for (uint64_t i = 0; i < AX_MEM_TRACKED_PAGE_CAP; i++) g_page_used[i] = 0;

    g_health.tracked_pages = 0;
    g_health.active_allocations = 0;
    g_health.high_watermark = 0;
    g_health.alloc_attempts = 0;
    g_health.alloc_success = 0;
    g_health.release_attempts = 0;
    g_health.release_success = 0;
    g_health.stress_cycles = 0;
    g_health.stress_failures = 0;
    g_health.pressure_peak_pct = 0;
    g_health.last_alloc_addr = 0;
}

static void update_pressure_peak(void) {
    if (g_health.tracked_pages == 0) return;
    uint64_t pressure = (g_health.active_allocations * 100) / g_health.tracked_pages;
    if (pressure > g_health.pressure_peak_pct) g_health.pressure_peak_pct = pressure;
}

static int page_index_for_addr(uint64_t page_addr, uint64_t *idx_out) {
    if (g_page_count == 0 || g_page_base == 0) return 0;
    if (page_addr < g_page_base) return 0;
    if ((page_addr & 0xFFFu) != 0) return 0;
    uint64_t rel = page_addr - g_page_base;
    uint64_t idx = rel >> 12;
    if ((idx << 12) != rel) return 0;
    if (idx >= g_page_count) return 0;
    if (idx_out) *idx_out = idx;
    return 1;
}

void ax_mem_init(const ax_bootinfo_t *bi) {
    g_state.total_bytes = 0;
    g_state.usable_bytes = 0;
    g_state.first_usable_base = 0;
    g_state.desc_count = 0;
    reset_tracking();

    if (!bi) return;
    if (bi->mmap == 0 || bi->mmap_desc_size < 32 || bi->mmap_size < bi->mmap_desc_size) {
        ax_trace(AX_EVT_MEM_INIT, 0, 0, 0);
        return;
    }

    const uint8_t *base = (const uint8_t *)(uintptr_t)bi->mmap;
    uint64_t count = bi->mmap_size / bi->mmap_desc_size;
    g_state.desc_count = count;

    for (uint64_t i = 0; i < count; i++) {
        const uint8_t *d = base + (i * bi->mmap_desc_size);
        uint32_t type = rd_u32(d + 0);
        uint64_t pstart = rd_u64(d + 8);
        uint64_t pages = rd_u64(d + 24);
        uint64_t bytes = pages << 12; // 4 KiB pages
        if (pages == 0) continue;

        g_state.total_bytes += bytes;
        // EFI conventional memory type is 7.
        if (type == 7) {
            g_state.usable_bytes += bytes;
            if (g_state.first_usable_base == 0) g_state.first_usable_base = pstart;
        }

        if (i < 8) {
            ax_trace(AX_EVT_MEM_REGION, (uint64_t)type, pstart, bytes);
        }
    }

    if (g_state.first_usable_base != 0 && g_state.usable_bytes >= 4096) {
        g_page_base = g_state.first_usable_base;
        g_page_count = g_state.usable_bytes >> 12;
        if (g_page_count > AX_MEM_TRACKED_PAGE_CAP) g_page_count = AX_MEM_TRACKED_PAGE_CAP;
        g_health.tracked_pages = g_page_count;
    }

    ax_trace(AX_EVT_MEM_INIT, g_state.desc_count, g_state.usable_bytes, g_state.total_bytes);
}

ax_mem_state_t ax_mem_state(void) {
    return g_state;
}

uint64_t ax_mem_alloc_page(void) {
    g_health.alloc_attempts++;
    if (g_page_count == 0 || g_page_base == 0) {
        ax_trace(AX_EVT_MEM_ALLOC, 0, 0, g_health.alloc_attempts);
        return 0;
    }
    for (uint64_t n = 0; n < g_page_count; n++) {
        uint64_t idx = (g_page_next_hint + n) % g_page_count;
        if (g_page_used[idx]) continue;
        g_page_used[idx] = 1;
        g_page_next_hint = (idx + 1) % g_page_count;
        g_health.alloc_success++;
        g_health.active_allocations++;
        if (g_health.active_allocations > g_health.high_watermark) g_health.high_watermark = g_health.active_allocations;
        update_pressure_peak();
        uint64_t page_addr = g_page_base + (idx << 12);
        g_health.last_alloc_addr = page_addr;
        ax_trace(AX_EVT_MEM_ALLOC, idx, g_health.active_allocations, page_addr);
        return page_addr;
    }
    g_health.stress_failures++;
    ax_trace(AX_EVT_MEM_ALLOC, (uint64_t)-1, g_health.active_allocations, g_health.alloc_attempts);
    return 0;
}

int ax_mem_release_page(uint64_t page_addr) {
    g_health.release_attempts++;
    uint64_t idx = 0;
    if (!page_index_for_addr(page_addr, &idx)) {
        ax_trace(AX_EVT_MEM_RELEASE, (uint64_t)-1, page_addr, g_health.release_attempts);
        return 0;
    }
    if (!g_page_used[idx]) {
        ax_trace(AX_EVT_MEM_RELEASE, (uint64_t)-1, page_addr, g_health.release_attempts);
        return 0;
    }
    g_page_used[idx] = 0;
    if (g_health.active_allocations > 0) g_health.active_allocations--;
    g_health.release_success++;
    ax_trace(AX_EVT_MEM_RELEASE, idx, g_health.active_allocations, page_addr);
    return 1;
}

void ax_mem_run_stress(uint64_t cycles, uint64_t alloc_burst) {
    uint64_t local[256];
    cycles = clamp_u64(cycles, 1, 128);
    alloc_burst = clamp_u64(alloc_burst, 1, 256);

    for (uint64_t c = 0; c < cycles; c++) {
        uint64_t acquired = 0;
        g_health.stress_cycles++;
        for (uint64_t i = 0; i < alloc_burst; i++) {
            uint64_t page = ax_mem_alloc_page();
            if (page == 0) break;
            local[acquired++] = page;
        }
        if (acquired < alloc_burst) g_health.stress_failures++;
        for (uint64_t i = 0; i < acquired; i += 2) (void)ax_mem_release_page(local[i]);
        for (uint64_t i = 1; i < acquired; i += 2) (void)ax_mem_release_page(local[i]);
    }

    ax_trace(AX_EVT_MEM_STRESS, g_health.stress_cycles, g_health.stress_failures, g_health.pressure_peak_pct);
}

ax_mem_health_t ax_mem_health(void) {
    return g_health;
}
