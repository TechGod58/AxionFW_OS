#pragma once
#include <stdint.h>

__attribute__((noreturn))
void ax_panic(const char *msg, uint64_t a, uint64_t b, uint64_t c);
