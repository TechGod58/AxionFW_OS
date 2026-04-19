from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(axion_path_str())
DOMAIN_PATH = ROOT / "config" / "PARALLEL_CUBED_SANDBOX_DOMAINS_V1.json"
APP_POLICY_PATH = ROOT / "config" / "APP_VM_ENFORCEMENT_V1.json"
COMPAT_PATH = ROOT / "config" / "APP_COMPATIBILITY_ENVIRONMENTS_V1.json"
SYSTEM_POLICY_PATH = ROOT / "config" / "SYSTEM_PROGRAM_EXECUTION_POLICY_V1.json"
BASE = ROOT / "out" / "runtime"
AUDIT_PATH = BASE / "parallel_cubed_sandbox_domain_integrity_audit.json"
SMOKE_PATH = BASE / "parallel_cubed_sandbox_domain_integrity_smoke.json"

CODES = {
    "PARALLEL_CUBED_SANDBOX_POLICY_DRIFT": 411,
    "PARALLEL_CUBED_SANDBOX_DOMAIN_DRIFT": 412,
}


def now():
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def load_json(path: Path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def write_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2) + "\n", encoding='utf-8')


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else 'pass'
    domain = load_json(DOMAIN_PATH)
    app_policy = load_json(APP_POLICY_PATH)
    compat_policy = load_json(COMPAT_PATH)
    system_policy = load_json(SYSTEM_POLICY_PATH) if SYSTEM_POLICY_PATH.exists() else {"apps": {}}
    failures = []

    def fail(code: str, detail: str):
        failures.append({'code': code, 'detail': detail})

    rails = domain.get('rails', {})
    regions = domain.get('regions', {})
    app_modes = app_policy.get('apps', {})
    compat_apps = (compat_policy.get('apps') or {})
    system_apps = (system_policy.get('apps') or {})
    required_rules = set(domain.get('requiredAppVmRules', []))
    present_rules = set(app_policy.get('rules', []))
    expected_host = set(domain.get('hostRequiredServices', []))
    actual_host = set((app_policy.get('exceptions') or {}).get('host_required', []))
    host_non_sandbox_mode = str(domain.get('hostNonSandboxMode', 'host_native_guarded'))
    host_non_sandbox_apps = {str(x) for x in domain.get('hostNonSandboxApps', [])}

    if domain.get('appVmPolicyId') != app_policy.get('policyId'):
        fail('PARALLEL_CUBED_SANDBOX_POLICY_DRIFT', f"appVmPolicyId mismatch: domain={domain.get('appVmPolicyId')} app={app_policy.get('policyId')}")
    if app_policy.get('defaultMode') != 'capsule':
        fail('PARALLEL_CUBED_SANDBOX_POLICY_DRIFT', f"defaultMode must be capsule, got {app_policy.get('defaultMode')}")
    if not required_rules.issubset(present_rules):
        fail('PARALLEL_CUBED_SANDBOX_POLICY_DRIFT', f"missing app VM rules: {sorted(required_rules - present_rules)}")
    if actual_host != expected_host:
        fail('PARALLEL_CUBED_SANDBOX_DOMAIN_DRIFT', f"host-required service drift: expected={sorted(expected_host)} actual={sorted(actual_host)}")

    install = rails.get('install', {})
    execute = rails.get('execute', {})
    persist = rails.get('persist', {})
    if not (install.get('sandbox_required') and install.get('capsule_image_required') and install.get('host_mount_visibility') == 'denied'):
        fail('PARALLEL_CUBED_SANDBOX_POLICY_DRIFT', 'install rail must require sandbox capsule images with denied host mounts')
    if not (execute.get('sandbox_required') and execute.get('default_launch_mode') == 'capsule' and execute.get('host_process_spawn') == 'denied' and execute.get('close_terminates_capsule')):
        fail('PARALLEL_CUBED_SANDBOX_POLICY_DRIFT', 'execute rail must force capsule launches, deny host spawns, and terminate on close')
    if not (persist.get('sandbox_required') and persist.get('promotion_required') and persist.get('direct_os_write') == 'denied' and persist.get('target_scheme') == 'safe://'):
        fail('PARALLEL_CUBED_SANDBOX_POLICY_DRIFT', 'persist rail must require promotion and deny direct OS writes')

    assignments = {}
    default_rails = domain.get('defaultRailBindings', [])
    for region_id, meta in regions.items():
        if meta.get('rail_bindings') != default_rails:
            fail('PARALLEL_CUBED_SANDBOX_DOMAIN_DRIFT', f"region {region_id} rail_bindings drift: {meta.get('rail_bindings')}")
        for app_id in meta.get('apps', []):
            if app_id in assignments:
                fail('PARALLEL_CUBED_SANDBOX_DOMAIN_DRIFT', f"app {app_id} assigned to multiple regions: {assignments[app_id]} and {region_id}")
                continue
            assignments[app_id] = region_id
            app_mode = app_modes.get(app_id)
            if app_mode is None:
                fail('PARALLEL_CUBED_SANDBOX_DOMAIN_DRIFT', f"app {app_id} missing from APP_VM_ENFORCEMENT_V1")
                continue
            if app_mode not in meta.get('allowed_modes', []):
                fail('PARALLEL_CUBED_SANDBOX_DOMAIN_DRIFT', f"app {app_id} mode {app_mode} not allowed in region {region_id}")
            if app_id in host_non_sandbox_apps:
                if str(app_mode) != host_non_sandbox_mode:
                    fail('PARALLEL_CUBED_SANDBOX_POLICY_DRIFT', f"host-nonsandbox app {app_id} mode drift: expected={host_non_sandbox_mode} got={app_mode}")
                sp = system_apps.get(app_id)
                if not isinstance(sp, dict):
                    fail('PARALLEL_CUBED_SANDBOX_POLICY_DRIFT', f"host-nonsandbox app {app_id} missing from SYSTEM_PROGRAM_EXECUTION_POLICY_V1")
                else:
                    if bool(sp.get('internet_required', True)):
                        fail('PARALLEL_CUBED_SANDBOX_POLICY_DRIFT', f"host-nonsandbox app {app_id} must declare internet_required=false")
                cp = compat_apps.get(app_id)
                if not isinstance(cp, dict):
                    fail('PARALLEL_CUBED_SANDBOX_POLICY_DRIFT', f"host-nonsandbox app {app_id} missing from APP_COMPATIBILITY_ENVIRONMENTS_V1")
                else:
                    if str(cp.get('family')) != 'native_system':
                        fail('PARALLEL_CUBED_SANDBOX_POLICY_DRIFT', f"host-nonsandbox app {app_id} must use native_system family")
            else:
                if not str(app_mode).startswith('capsule'):
                    fail('PARALLEL_CUBED_SANDBOX_POLICY_DRIFT', f"app {app_id} escapes sandbox mode with {app_mode}")

    missing_apps = sorted(set(app_modes) - set(assignments))
    extra_apps = sorted(set(assignments) - set(app_modes))
    if missing_apps:
        fail('PARALLEL_CUBED_SANDBOX_DOMAIN_DRIFT', f"apps missing region assignment: {missing_apps}")
    if extra_apps:
        fail('PARALLEL_CUBED_SANDBOX_DOMAIN_DRIFT', f"domain config references undeclared apps: {extra_apps}")
    missing_host_apps = sorted(host_non_sandbox_apps - set(assignments))
    if missing_host_apps:
        fail('PARALLEL_CUBED_SANDBOX_DOMAIN_DRIFT', f"host-nonsandbox apps missing region assignment: {missing_host_apps}")

    for syn in domain.get('synapses', []):
        if syn.get('src') not in regions or syn.get('dst') not in regions:
            fail('PARALLEL_CUBED_SANDBOX_DOMAIN_DRIFT', f"synapse references unknown region: {syn}")
        if syn.get('via') not in rails:
            fail('PARALLEL_CUBED_SANDBOX_DOMAIN_DRIFT', f"synapse references unknown rail: {syn}")

    if mode == 'policy_drift':
        fail('PARALLEL_CUBED_SANDBOX_POLICY_DRIFT', 'negative control: simulated sandbox policy drift')
    elif mode == 'domain_drift':
        fail('PARALLEL_CUBED_SANDBOX_DOMAIN_DRIFT', 'negative control: simulated region/domain drift')

    status = 'FAIL' if failures else 'PASS'
    summary = {
        'timestamp_utc': now(),
        'status': status,
        'policy_id': domain.get('policyId'),
        'app_vm_policy_id': app_policy.get('policyId'),
        'default_mode': app_policy.get('defaultMode'),
        'host_required_services': sorted(actual_host),
        'rails': rails,
        'regions': {
            region_id: {
                'sandbox_domain': meta.get('sandbox_domain'),
                'rail_bindings': meta.get('rail_bindings'),
                'app_count': len(meta.get('apps', [])),
                'apps': meta.get('apps', []),
            }
            for region_id, meta in regions.items()
        },
        'synapses': domain.get('synapses', []),
        'failures': failures,
    }
    audit = {
        'timestamp_utc': now(),
        'status': status,
        'checks': [
            'app_vm_policy_binding',
            'sandbox_default_mode',
            'install_execute_persist_rails',
            'region_assignment_coverage',
            'host_service_control_plane',
            'synapse_reference_integrity',
        ],
        'failures': failures,
        'evidence': {
            'domain_policy_path': str(DOMAIN_PATH),
            'app_vm_policy_path': str(APP_POLICY_PATH),
        },
    }
    write_json(SMOKE_PATH, summary)
    write_json(AUDIT_PATH, audit)
    if failures:
        raise SystemExit(CODES[failures[0]['code']])


if __name__ == '__main__':
    main()

