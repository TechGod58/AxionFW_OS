#!/usr/bin/env python3
import sys
from pathlib import Path

_TOOLS_DIR = None
for _parent in Path(__file__).resolve().parents:
    if (_parent / "tools" / "common" / "pathing.py").exists():
        _TOOLS_DIR = _parent / "tools"
        break
if _TOOLS_DIR and str(_TOOLS_DIR) not in sys.path:
    sys.path.append(str(_TOOLS_DIR))

from common.pathing import axion_path


def axion_path_str(*parts):
    return str(axion_path(*parts))
import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List

ROOT = axion_path_str()
BASE = os.path.join(ROOT, 'out', 'governance', 'AXIONOS_GOVERNANCE_BASELINE_20260305.json')
OUT = os.path.join(ROOT, 'out', 'contracts', 'governance_baseline_drift.json')
EXPLAIN_DEFAULT = os.path.join(ROOT, 'out', 'governance', 'audit', 'baseline_drift_explain_latest.json')
AXION_ROOT_POSIX_PREFIX = ROOT.replace('\\', '/').rstrip('/').lower() + '/'

FILES = {
    'canonical_gate_registry': os.path.join(ROOT, 'config', 'release_critical_gates.json'),
    'gate_script': os.path.join(ROOT, 'ci', 'pipeline_contracts_gate.ps1'),
    'doctrine': os.path.join(ROOT, 'design', 'ops', 'CONTRACT_FIRST_DEVELOPMENT_LOOP_V1.md'),
    'exit_registry': os.path.join(ROOT, 'contracts', 'registry', 'integrity_exit_registry.json'),
    'inventory': os.path.join(ROOT, 'out', 'contracts', 'release_critical_gates_inventory.json'),
    'coverage_map': os.path.join(ROOT, 'out', 'governance', 'integrity_coverage_map.json'),
}

VOLATILE_KEY_PATTERNS = (
    'timestamp', 'generated_at', 'lastwrite', 'mtime', 'ctime',
    'run_id', 'build_id', 'host', 'machine', 'user', 'cwd',
    'inventory_timestamp', 'last_pass_report', 'report_path', 'zip_path'
)


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def _is_volatile_key(key: str) -> bool:
    k = key.lower()
    return any(p in k for p in VOLATILE_KEY_PATTERNS)


def _normalize_path_str(value: str) -> str:
    v = value.replace('\\', '/').strip()
    if v.lower().startswith(AXION_ROOT_POSIX_PREFIX):
        v = 'AXION_ROOT:/' + v[len(AXION_ROOT_POSIX_PREFIX):]
    return v


def _is_set_like_list(path: str) -> bool:
    p = path.lower()
    return ('gates' in p) or ('entries' in p) or ('failures' in p)


def _sort_list(items: List[Any]) -> List[Any]:
    if not items:
        return items
    if all(isinstance(x, dict) for x in items):
        key_order = ('contract_id', 'id', 'code', 'path', 'name')
        def kfn(d: Dict[str, Any]):
            for k in key_order:
                if k in d:
                    return str(d.get(k, ''))
            return json.dumps(d, sort_keys=True, separators=(',', ':'))
        return sorted(items, key=kfn)
    if all(isinstance(x, (str, int, float, bool)) or x is None for x in items):
        return sorted(items, key=lambda v: json.dumps(v, sort_keys=True))
    return items


def _canonicalize(value: Any, path: str = '') -> Any:
    if isinstance(value, dict):
        out = {}
        for k in sorted(value.keys()):
            if _is_volatile_key(k):
                continue
            out[k] = _canonicalize(value[k], f'{path}.{k}' if path else k)
        return out
    if isinstance(value, list):
        arr = [_canonicalize(v, f'{path}[]') for v in value]
        if _is_set_like_list(path):
            arr = _sort_list(arr)
        return arr
    if isinstance(value, str):
        return _normalize_path_str(value)
    return value


def _canonical_json_bytes(path: str) -> bytes:
    with open(path, 'r', encoding='utf-8-sig') as f:
        obj = json.load(f)
    canon = _canonicalize(obj)
    return json.dumps(canon, sort_keys=True, separators=(',', ':')).encode('utf-8')


def _hash_file(path: str, semantic: bool) -> str:
    if not os.path.exists(path):
        return None
    m = hashlib.sha256()
    if semantic and path.lower().endswith('.json'):
        m.update(_canonical_json_bytes(path))
    elif semantic and path.lower().endswith(('.md', '.ps1', '.txt')):
        text = open(path, 'r', encoding='utf-8-sig').read().replace('\r\n', '\n').strip()
        m.update(text.encode('utf-8'))
    else:
        with open(path, 'rb') as f:
            for c in iter(lambda: f.read(1024 * 1024), b''):
                m.update(c)
    return m.hexdigest().lower()


def _current_hashes(semantic: bool) -> Dict[str, str]:
    return {k: _hash_file(v, semantic) for k, v in FILES.items()}


def _baseline_hashes() -> Dict[str, str]:
    if not os.path.exists(BASE):
        return {}
    data = json.load(open(BASE, 'r', encoding='utf-8-sig'))
    return {k: (v.lower() if isinstance(v, str) else v) for k, v in data.get('hashes', {}).items()}


def _classify_diff(key: str, old: Any, new: Any) -> str:
    if old is None or new is None:
        return 'MISSING_KEY'
    if old == new:
        return 'NONE'
    if 'path' in key.lower():
        return 'PATH'
    return 'SEMANTIC_CHANGE'


def _write_explain(path: str, drift: Dict[str, Any]) -> None:
    entries = []
    for k, d in drift.items():
        entries.append({
            'key': k,
            'baseline': d.get('baseline'),
            'current': d.get('current'),
            'classification': _classify_diff(k, d.get('baseline'), d.get('current')),
        })
    payload = {'timestamp_utc': now(), 'drift_count': len(entries), 'diffs': entries[:10]}
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(payload, open(path, 'w', encoding='utf-8'), indent=2)


def do_refresh(semantic: bool) -> int:
    os.system(f'python "{os.path.join(ROOT, "tools", "governance", "emit_release_gate_inventory.py")}" > nul')
    os.system(f'python "{os.path.join(ROOT, "tools", "governance", "emit_integrity_coverage_map.py")}" > nul')
    hashes = _current_hashes(semantic=semantic)
    obj = {'timestamp_utc': now(), 'hashes': hashes, 'mode': 'semantic' if semantic else 'raw'}
    os.makedirs(os.path.dirname(BASE), exist_ok=True)
    json.dump(obj, open(BASE, 'w', encoding='utf-8'), indent=2)
    return 0


def do_check(semantic: bool, explain_path: str = None) -> int:
    current = _current_hashes(semantic=semantic)
    baseline = _baseline_hashes()
    drift = {k: {'baseline': baseline.get(k), 'current': current.get(k)} for k in FILES if baseline.get(k) != current.get(k)}
    status = 'PASS' if not drift else 'FAIL'
    out = {'timestamp_utc': now(), 'status': status, 'mode': 'semantic' if semantic else 'raw', 'drift': drift}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(out, open(OUT, 'w', encoding='utf-8'), indent=2)
    if explain_path:
        _write_explain(explain_path, drift)
    print(OUT)
    if status != 'PASS':
        print('GOVERNANCE_BASELINE_DRIFT')
        return 1
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--refresh', action='store_true')
    ap.add_argument('--raw', action='store_true')
    ap.add_argument('--explain', nargs='?', const=EXPLAIN_DEFAULT)
    args = ap.parse_args()
    semantic = not args.raw
    if args.refresh:
        return do_refresh(semantic)
    return do_check(semantic, args.explain)


if __name__ == '__main__':
    raise SystemExit(main())

