def ig_verdict(meta):
    """
    v1 real toggle behavior:
    - If metadata contains ig_force_fail=true => fail
    - If env AXION_IG_FORCE_FAIL=1|true => fail
    - Else pass
    """
    import os

    if isinstance(meta, dict) and bool(meta.get('ig_force_fail', False)):
        return False, 'IG_FORCED_FAIL_META'

    env_force = os.getenv('AXION_IG_FORCE_FAIL', '').strip().lower()
    if env_force in ('1', 'true', 'yes', 'on'):
        return False, 'IG_FORCED_FAIL_ENV'

    return True, 'IG_PASS'
