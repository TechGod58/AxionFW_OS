#include "axion/panic.h"
#include "axion/telemetry.h"
#include "axion/console.h"

__attribute__((noreturn))
void ax_panic(const char *msg, uint64_t a, uint64_t b, uint64_t c) {
    ax_trace(AX_EVT_PANIC, a, b, c);
    ax_printf("PANIC: %s\n", msg ? msg : "(null)");
    for (;;) { __asm__ volatile("cli; hlt"); }
}
