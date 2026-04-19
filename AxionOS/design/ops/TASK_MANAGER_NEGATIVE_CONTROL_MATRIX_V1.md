# TASK_MANAGER_NEGATIVE_CONTROL_MATRIX_V1

| mode | expected_exit | expected_code | expected_report_pattern |
|---|---:|---|---|
| fail | 61 | TASK_NOT_FOUND | contract_report_*_TM_FAIL.json |
| kill_denied | 62 | TASK_KILL_DENIED | contract_report_*_TM_KILL_DENIED_FAIL.json |
| priority_invalid | 63 | TASK_PRIORITY_INVALID | contract_report_*_TM_PRIORITY_INVALID_FAIL.json |
