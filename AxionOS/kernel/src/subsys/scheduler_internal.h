#pragma once
#include <stdint.h>
#include "axion/subsys/scheduler.h"

void ax_sched_internal_enable_syscall_gate(uint64_t token);
int ax_sched_internal_apply_policy_syscall(ax_sched_policy_t policy, uint64_t actor_level, uint64_t token);
