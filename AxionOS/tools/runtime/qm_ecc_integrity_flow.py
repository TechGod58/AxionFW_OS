from runtime_paths import axion_path, axion_path_str
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(axion_path_str())
SECURITY_DIR = ROOT / 'runtime' / 'security'
if str(SECURITY_DIR) not in sys.path:
    sys.path.append(str(SECURITY_DIR))

from qm_ecc_bridge import evaluate_signal, load_policy

BASE = ROOT / 'out' / 'runtime'
AUDIT_PATH = BASE / 'qm_ecc_integrity_audit.json'
SMOKE_PATH = BASE / 'qm_ecc_integrity_smoke.json'

CODES = {
    'QM_ECC_HALT_REQUIRED': 3611,
    'QM_ECC_ROLLBACK_REQUIRED': 3612,
}


def now():
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def write_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2) + '\n', encoding='utf-8')


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else 'pass'
    failures = []

    def fail(code: str, detail: str):
        failures.append({'code': code, 'detail': detail})

    policy = load_policy()
    if not bool(policy.get('enabled', True)):
        fail('QM_ECC_HALT_REQUIRED', 'QM ECC policy disabled')
    else:
        if mode == 'pass':
            decision = evaluate_signal({'entropy': 0.05, 'error_rate': 0.02, 'instability': 0.01}, domain='security_core', corr='corr_qm_ecc_001')
            if not bool(decision.get('ok')):
                fail('QM_ECC_HALT_REQUIRED', f'expected allow decision, got {decision.get("action")}')
        elif mode == 'halt_action':
            decision = evaluate_signal({'qm_force_action': 'halt', 'entropy': 0.95, 'error_rate': 0.95, 'instability': 0.95}, domain='security_core', corr='corr_qm_ecc_002')
            action = str(decision.get('action'))
            if action != 'halt':
                fail('QM_ECC_HALT_REQUIRED', f'expected halt action, got {action}')
            else:
                # Negative control: prove halt path maps to contract exit 3611.
                fail('QM_ECC_HALT_REQUIRED', 'halt action required by QM/ECC policy')
        elif mode == 'rollback_action':
            decision = evaluate_signal(
                {
                    'qm_force_action': 'rollback',
                    'entropy': 0.65,
                    'error_rate': 0.75,
                    'instability': 0.72,
                    'checkpoint_available': True,
                    'checkpoint_candidates': [
                        {'checkpoint_id': 'cp_qm_ecc_001', 'step': 4, 'quality': 'gold', 'risk': 0.30, 'level': 'elevated'}
                    ],
                },
                domain='security_core',
                corr='corr_qm_ecc_003',
            )
            action = str(decision.get('action'))
            if action != 'rollback':
                fail('QM_ECC_ROLLBACK_REQUIRED', f'expected rollback action, got {action}')
            else:
                # Negative control: prove rollback path maps to contract exit 3612.
                fail('QM_ECC_ROLLBACK_REQUIRED', 'rollback action required by QM/ECC policy')
        else:
            fail('QM_ECC_HALT_REQUIRED', f'unknown mode {mode}')

    status = 'FAIL' if failures else 'PASS'
    summary = {
        'timestamp_utc': now(),
        'status': status,
        'policy_id': policy.get('policyId'),
        'failures': failures,
    }
    audit = {
        'timestamp_utc': now(),
        'status': status,
        'checks': ['qm_policy_enabled', 'qm_decision_contract', 'qm_action_enforcement'],
        'failures': failures,
        'evidence': {
            'policy_path': str(ROOT / 'config' / 'QM_ECC_POLICY_V1.json'),
            'state_path': str(ROOT / 'config' / 'QM_ECC_STATE_V1.json'),
        },
    }
    write_json(SMOKE_PATH, summary)
    write_json(AUDIT_PATH, audit)
    if failures:
        raise SystemExit(CODES[failures[0]['code']])


if __name__ == '__main__':
    main()
