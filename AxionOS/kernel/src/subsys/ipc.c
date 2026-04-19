#include "axion/subsys/ipc.h"
#include "axion/telemetry.h"

#define AX_IPC_Q_CAP 32

typedef struct {
    uint64_t used;
    uint64_t channel_id;
    uint64_t tag;
    uint64_t data;
} ax_ipc_msg_t;

static ax_ipc_state_t g_ipc;
static ax_ipc_msg_t g_q[AX_IPC_Q_CAP];
static uint64_t g_head;
static uint64_t g_tail;

static uint64_t clamp_capacity(uint64_t cap) {
    if (cap == 0) return 8;
    if (cap > AX_IPC_Q_CAP) return AX_IPC_Q_CAP;
    return cap;
}

void ax_ipc_init(uint64_t channel_count, uint64_t queue_capacity) {
    g_ipc.initialized = 1;
    g_ipc.channel_count = channel_count == 0 ? 1 : channel_count;
    g_ipc.queue_capacity = clamp_capacity(queue_capacity);
    g_ipc.queue_depth = 0;
    g_ipc.enqueued_total = 0;
    g_ipc.dequeued_total = 0;
    g_ipc.dropped_total = 0;
    g_ipc.last_channel_id = 0;
    g_head = 0;
    g_tail = 0;
    for (uint64_t i = 0; i < AX_IPC_Q_CAP; i++) g_q[i].used = 0;
    ax_trace(AX_EVT_IPC_INIT, g_ipc.channel_count, g_ipc.queue_capacity, 0);
}

int ax_ipc_send(uint64_t channel_id, uint64_t tag, uint64_t data) {
    if (!g_ipc.initialized) return 0;
    if (channel_id >= g_ipc.channel_count) {
        g_ipc.dropped_total++;
        return 0;
    }
    if (g_ipc.queue_depth >= g_ipc.queue_capacity) {
        g_ipc.dropped_total++;
        return 0;
    }
    g_q[g_tail] = (ax_ipc_msg_t){ .used = 1, .channel_id = channel_id, .tag = tag, .data = data };
    g_tail = (g_tail + 1) % AX_IPC_Q_CAP;
    g_ipc.queue_depth++;
    g_ipc.enqueued_total++;
    g_ipc.last_channel_id = channel_id;
    ax_trace(AX_EVT_IPC_SEND, channel_id, tag, data);
    return 1;
}

int ax_ipc_recv(uint64_t channel_id, uint64_t *tag, uint64_t *data) {
    if (!g_ipc.initialized) return 0;
    if (g_ipc.queue_depth == 0) return 0;
    ax_ipc_msg_t m = g_q[g_head];
    if (!m.used || m.channel_id != channel_id) return 0;

    if (tag) *tag = m.tag;
    if (data) *data = m.data;
    g_q[g_head].used = 0;
    g_head = (g_head + 1) % AX_IPC_Q_CAP;
    g_ipc.queue_depth--;
    g_ipc.dequeued_total++;
    g_ipc.last_channel_id = channel_id;
    ax_trace(AX_EVT_IPC_RECV, channel_id, m.tag, m.data);
    return 1;
}

ax_ipc_state_t ax_ipc_state(void) {
    return g_ipc;
}

