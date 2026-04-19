#pragma once
#include <stdint.h>

static inline void ax_hlt(void) { __asm__ volatile("hlt"); }
static inline void ax_cli(void) { __asm__ volatile("cli"); }
static inline void ax_sti(void) { __asm__ volatile("sti"); }
