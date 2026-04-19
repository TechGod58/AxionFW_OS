from qm_ecc_bridge import evaluate_signal, evaluate_packet, load_policy


def test_qm_ecc_policy_enabled():
    policy = load_policy()
    assert policy['policyId'] == 'AXION_QM_ECC_POLICY_V1'
    assert bool(policy.get('enabled', False)) is True


def test_qm_ecc_pass_signal():
    out = evaluate_signal({'entropy': 0.05, 'error_rate': 0.02, 'instability': 0.01}, domain='unit_test', corr='corr_qm_unit_001')
    assert out['ok'] is True
    assert out['action'] == 'continue'


def test_qm_ecc_halt_signal_forced():
    out = evaluate_signal({'qm_force_action': 'halt', 'entropy': 0.95, 'error_rate': 0.9, 'instability': 0.95}, domain='unit_test', corr='corr_qm_unit_002')
    assert out['ok'] is False
    assert out['action'] == 'halt'


def test_qm_ecc_packet_rollback_forced():
    out = evaluate_packet({'qm_force_action': 'rollback', 'ecc_error_rate': 0.8, 'instability': 0.75}, app_id='external_installer', corr='corr_qm_unit_003')
    assert out['ok'] is False
    assert out['action'] == 'rollback'
