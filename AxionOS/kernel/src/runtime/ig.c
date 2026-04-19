#include <axion/runtime/ig.h>
#include "axion/telemetry.h"

static axion_ig_state_t g_ig;

static uint64_t hash64(const char *s) {
    uint64_t h = 1469598103934665603ull;
    if (!s) return h;
    while (*s) {
        h ^= (uint8_t)(*s);
        h *= 1099511628211ull;
        s++;
    }
    return h;
}

static int contains_token(const char *s, const char *token) {
    if (!s || !token) return 0;
    while (*s) {
        const char *a = s;
        const char *b = token;
        while (*a && *b && *a == *b) {
            a++;
            b++;
        }
        if (*b == 0) return 1;
        s++;
    }
    return 0;
}

int axion_ig_validate(const char *event) {
    uint64_t h = hash64(event);
    int allow = 1;
    if (!event || event[0] == 0) allow = 0;
    if (allow && contains_token(event, "deny")) allow = 0;
    if (allow && contains_token(event, "bypass")) allow = 0;
    if (allow && contains_token(event, "escape")) allow = 0;

    g_ig.total++;
    g_ig.last_hash = h;
    if (allow) g_ig.allowed++;
    else g_ig.denied++;
    ax_trace(AX_EVT_RUNTIME_IG_VALIDATE, allow, g_ig.total, h);
    return allow;
}

axion_ig_state_t axion_ig_state(void) {
    return g_ig;
}

