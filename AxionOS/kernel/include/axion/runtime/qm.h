#pragma once
#include <stdint.h>

typedef enum {
    AXION_QM_PHASE_COLD_BOOT = 0,
    AXION_QM_PHASE_SECURE_INIT = 1,
    AXION_QM_PHASE_RUNTIME_READY = 2,
    AXION_QM_PHASE_DEGRADED = 3,
    AXION_QM_PHASE_RECOVERY = 4,
} axion_qm_phase_t;

typedef enum {
    AXION_QM_REASON_ALLOW = 0,
    AXION_QM_REASON_DENY_NOT_INITIALIZED = 1,
    AXION_QM_REASON_DENY_BAD_TARGET = 2,
    AXION_QM_REASON_DENY_POLICY_LEVEL = 3,
    AXION_QM_REASON_DENY_STRICT_PATH = 4,
} axion_qm_reason_t;

typedef struct {
    uint64_t strict_forward_only;
    uint64_t allow_recovery_anytime;
    uint64_t min_transition_level;
    uint64_t min_policy_write_level;
} axion_qm_policy_t;

typedef struct {
    uint64_t initialized;
    axion_qm_phase_t phase;
    uint64_t policy_epoch;
    uint64_t transitions_total;
    uint64_t transitions_denied;
    uint64_t transitions_recovery;
    axion_qm_reason_t last_reason;
    axion_qm_phase_t last_target;
    uint64_t last_policy_epoch;
} axion_qm_state_t;

void axion_qm_init(void);
int axion_qm_set_policy_checked(axion_qm_policy_t policy, uint64_t actor_level);
axion_qm_policy_t axion_qm_get_policy(void);
int axion_qm_transition(const char *state);
int axion_qm_transition_ex(axion_qm_phase_t target, uint64_t requested_level);
axion_qm_state_t axion_qm_state(void);

