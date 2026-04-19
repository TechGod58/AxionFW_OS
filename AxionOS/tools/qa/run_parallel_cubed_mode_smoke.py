#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

TOOLS_DIR = Path(__file__).resolve().parent.parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.append(str(TOOLS_DIR))

from common.pathing import axion_path

OUT = axion_path('out', 'qa')
OUT.mkdir(parents=True, exist_ok=True)

LAUNCHER_DIR = axion_path('runtime', 'capsule', 'launchers')
if str(LAUNCHER_DIR) not in sys.path:
    sys.path.append(str(LAUNCHER_DIR))

from app_runtime_launcher import launch


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_parallel_flow(mode: str, expected_exit: int, expected_code: str | None):
    script = axion_path('tools', 'runtime', 'parallel_cubed_sandbox_domain_integrity_flow.py')
    smoke = axion_path('out', 'runtime', 'parallel_cubed_sandbox_domain_integrity_smoke.json')
    audit = axion_path('out', 'runtime', 'parallel_cubed_sandbox_domain_integrity_audit.json')
    p = subprocess.run(['python', str(script), mode], capture_output=True, text=True)
    smoke_obj = None
    if smoke.exists():
        try:
            smoke_obj = json.loads(smoke.read_text(encoding='utf-8-sig'))
        except Exception:
            smoke_obj = None

    code = None
    if isinstance(smoke_obj, dict):
        failures = smoke_obj.get('failures', [])
        if isinstance(failures, list) and failures:
            first = failures[0]
            if isinstance(first, dict):
                code = first.get('code')

    ok_exit = p.returncode == expected_exit
    ok_code = (code == expected_code) if expected_code is not None else (code is None)
    return {
        'mode': mode,
        'expected_exit': expected_exit,
        'actual_exit': p.returncode,
        'expected_code': expected_code,
        'actual_code': code,
        'smoke_path': str(smoke),
        'audit_path': str(audit),
        'ok': bool(ok_exit and ok_code and isinstance(smoke_obj, dict)),
        'stdout_tail': (p.stdout or '').strip()[-300:],
        'stderr_tail': (p.stderr or '').strip()[-300:],
    }


def main() -> int:
    checks: list[dict[str, Any]] = []

    checks.append(run_parallel_flow('pass', 0, None))
    checks.append(run_parallel_flow('policy_drift', 411, 'PARALLEL_CUBED_SANDBOX_POLICY_DRIFT'))
    checks.append(run_parallel_flow('domain_drift', 412, 'PARALLEL_CUBED_SANDBOX_DOMAIN_DRIFT'))

    cmd = launch('command_prompt', 'corr_parallel_mode_smoke_001')
    checks.append({
        'mode': 'launch_command_prompt',
        'expected_exit': 0,
        'actual_exit': 0,
        'expected_code': 'LAUNCH_OK',
        'actual_code': cmd.get('code'),
        'ok': bool(
            cmd.get('ok')
            and str((cmd.get('compatibility') or {}).get('execution_model')) == 'host_native_guarded'
            and bool((cmd.get('system_policy') or {}).get('internet_required') is False)
        ),
        'details': {
            'compatibility': cmd.get('compatibility'),
            'system_policy': cmd.get('system_policy'),
            'firewall_guard_session': cmd.get('firewall_guard_session'),
        },
    })

    passed = sum(1 for c in checks if bool(c.get('ok')))
    failed = len(checks) - passed
    summary = {
        'ts': now_iso(),
        'suite': 'parallel_cubed_mode_smoke',
        'checks_total': len(checks),
        'checks_passed': passed,
        'checks_failed': failed,
        'ok': failed == 0,
        'checks': checks,
    }

    out_json = OUT / 'parallel_cubed_mode_smoke_summary.json'
    out_md = OUT / 'parallel_cubed_mode_smoke_summary.md'
    out_json.write_text(json.dumps(summary, indent=2), encoding='utf-8')

    lines = [
        '# Parallel Cubed Mode Smoke',
        '',
        f"- Timestamp: {summary['ts']}",
        f"- Checks: {summary['checks_total']}",
        f"- Passed: {summary['checks_passed']}",
        f"- Failed: {summary['checks_failed']}",
        f"- Overall: {'PASS' if summary['ok'] else 'FAIL'}",
        '',
        '## Checks',
    ]
    for c in checks:
        lines.append(f"- [{'PASS' if c.get('ok') else 'FAIL'}] {c.get('mode')} expected={c.get('expected_code')} actual={c.get('actual_code')}")
    out_md.write_text('\n'.join(lines), encoding='utf-8')

    print(json.dumps({
        'ok': summary['ok'],
        'summary_json': str(out_json),
        'summary_md': str(out_md),
        'checks_passed': passed,
        'checks_failed': failed,
    }, indent=2))
    return 0 if summary['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
