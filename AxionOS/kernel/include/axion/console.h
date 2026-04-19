#pragma once
#include <stdint.h>
#include <stdarg.h>

typedef struct {
    uint64_t fb_base;
    uint32_t w, h, ppsl, bpp;
} ax_console_t;

void ax_console_init(ax_console_t *c);
void ax_print(const char *s);
void ax_printf(const char *fmt, ...);
