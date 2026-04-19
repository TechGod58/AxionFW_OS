#pragma once
#include <stdint.h>

typedef struct {
    uint64_t initialized;
    uint64_t channel_count;
    uint64_t queue_capacity;
    uint64_t queue_depth;
    uint64_t enqueued_total;
    uint64_t dequeued_total;
    uint64_t dropped_total;
    uint64_t last_channel_id;
} ax_ipc_state_t;

void ax_ipc_init(uint64_t channel_count, uint64_t queue_capacity);
int ax_ipc_send(uint64_t channel_id, uint64_t tag, uint64_t data);
int ax_ipc_recv(uint64_t channel_id, uint64_t *tag, uint64_t *data);
ax_ipc_state_t ax_ipc_state(void);

