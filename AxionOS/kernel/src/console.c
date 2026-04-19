#include "axion/console.h"
#include <stddef.h>

static ax_console_t *g_c = NULL;

static uint32_t g_x = 0;
static uint32_t g_y = 0;

static void putpixel(uint32_t x, uint32_t y, uint32_t v) {
    if (!g_c) return;
    if (x >= g_c->w || y >= g_c->h) return;
    uint32_t *fb = (uint32_t *)(uintptr_t)g_c->fb_base;
    fb[y * g_c->ppsl + x] = v;
}

// Very crude 8x16-ish block font substitute: draw rectangles per character.
// Replace with a real bitmap font later.
static void draw_char(char ch) {
    // Each char is 8x16 block; pattern based on ascii value for visibility.
    uint32_t v = 0xFF000000u | ((uint8_t)ch * 0x00010101u);
    uint32_t x0 = g_x * 8;
    uint32_t y0 = g_y * 16;
    for (uint32_t y = 0; y < 16; y++) {
        for (uint32_t x = 0; x < 8; x++) {
            putpixel(x0 + x, y0 + y, v);
        }
    }
    g_x++;
    if ((g_x + 1) * 8 >= g_c->w) { g_x = 0; g_y++; }
    if ((g_y + 1) * 16 >= g_c->h) { g_y = 0; }
}

void ax_console_init(ax_console_t *c) {
    g_c = c;
    g_x = g_y = 0;
}

void ax_print(const char *s) {
    for (; *s; s++) {
        if (*s == '\n') { g_x = 0; g_y++; continue; }
        if (*s == '\r') { g_x = 0; continue; }
        draw_char(*s);
    }
}

static void u64_to_hex(uint64_t v, char *out) {
    const char *hex = "0123456789abcdef";
    for (int i = 0; i < 16; i++) {
        out[15 - i] = hex[(v >> (i * 4)) & 0xF];
    }
    out[16] = 0;
}

static void u64_to_dec(uint64_t v, char *out) {
    char tmp[32];
    int n = 0;
    if (v == 0) { out[0] = '0'; out[1] = 0; return; }
    while (v && n < (int)sizeof(tmp)) { tmp[n++] = '0' + (v % 10); v /= 10; }
    for (int i = 0; i < n; i++) out[i] = tmp[n - 1 - i];
    out[n] = 0;
}

void ax_printf(const char *fmt, ...) {
    va_list ap;
    va_start(ap, fmt);

    for (const char *p = fmt; *p; p++) {
        if (*p != '%') { char c[2] = {*p,0}; ax_print(c); continue; }
        p++;
        if (*p == '%') { ax_print("%"); continue; }
        if (*p == 's') {
            const char *s = va_arg(ap, const char *);
            ax_print(s ? s : "(null)");
            continue;
        }
        if (*p == 'l' && *(p+1) == 'u') {
            p++;
            uint64_t v = va_arg(ap, uint64_t);
            char buf[32]; u64_to_dec(v, buf);
            ax_print(buf);
            continue;
        }
        if (*p == 'l' && *(p+1) == 'x') {
            p++;
            uint64_t v = va_arg(ap, uint64_t);
            char buf[32]; buf[0]='0'; buf[1]='x'; u64_to_hex(v, buf+2);
            ax_print(buf);
            continue;
        }
        // Unknown specifier: print it raw
        ax_print("%?");
    }

    va_end(ap);
}
