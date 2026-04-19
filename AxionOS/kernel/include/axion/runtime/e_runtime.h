#pragma once
#include <stdint.h>

typedef enum {
    AXION_E_TASK_UNKNOWN = 0,
    AXION_E_TASK_USER_APP = 1,
    AXION_E_TASK_INSTALLER = 2,
    AXION_E_TASK_MODULE_ATTACH = 3,
    AXION_E_TASK_SYSTEM = 4,
} axion_e_task_class_t;

typedef enum {
    AXION_E_REASON_ALLOW = 0,
    AXION_E_REASON_DENY_NOT_INITIALIZED = 1,
    AXION_E_REASON_DENY_POLICY_LEVEL = 2,
    AXION_E_REASON_DENY_SANDBOX_REQUIRED = 3,
    AXION_E_REASON_DENY_IG = 4,
    AXION_E_REASON_DENY_INVALID_TASK = 5,
} axion_e_reason_t;

typedef struct {
    uint64_t enforce_ig;
    uint64_t require_ledger;
    uint64_t require_qecc;
    uint64_t sandbox_required_for_external;
    uint64_t min_policy_write_level;
    uint64_t max_task_name_len;
} axion_e_policy_t;

typedef struct {
    uint64_t initialized;
    uint64_t policy_epoch;
    uint64_t total_exec;
    uint64_t denied_exec;
    uint64_t installer_exec;
    uint64_t module_attach_exec;
    uint64_t external_exec;
    uint64_t sandbox_exec;
    axion_e_reason_t last_reason;
    uint64_t last_policy_epoch;
} axion_e_state_t;

void axion_e_init(void);
int axion_e_set_policy_checked(axion_e_policy_t policy, uint64_t actor_level);
axion_e_policy_t axion_e_get_policy(void);
int axion_e_execute(const char *task);
int axion_e_execute_ex(
    const char *task,
    axion_e_task_class_t task_class,
    uint64_t requested_level,
    uint64_t is_external,
    uint64_t from_sandbox
);
axion_e_state_t axion_e_state(void);

