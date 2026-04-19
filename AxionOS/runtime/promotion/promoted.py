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
from pathlib import Path

from config import load_policy
from envelope import validate_envelope
from hasher import verify_hash
from safe_uri import resolve_safe_uri
from scanner import scan_artifact
from ig_gate import ig_verdict
from mover import move_to_quarantine, move_to_target
from audit import append_audit
from codes import *


def process_once(artifact, meta, quarantine_dir, audit_path):
    ok, meta_obj = validate_envelope(meta)
    if not ok:
        append_audit({'decision': DECISION_REJECT_SCHEMA, 'detail': meta_obj}, audit_path)
        return EXIT_SCHEMA

    if not verify_hash(artifact, meta_obj['sha256']):
        move_to_quarantine(artifact, quarantine_dir)
        append_audit({'corr': meta_obj.get('corr'), 'artifact_id': meta_obj.get('artifact_id'), 'decision': DECISION_REJECT_HASH}, audit_path)
        return EXIT_HASH

    policy = load_policy()
    ok_map, code, target = resolve_safe_uri(meta_obj['safe_uri'], policy, meta_obj)
    if not ok_map:
        move_to_quarantine(artifact, quarantine_dir)
        append_audit({'corr': meta_obj['corr'], 'artifact_id': meta_obj['artifact_id'], 'decision': DECISION_REJECT_POLICY, 'detail': code}, audit_path)
        return EXIT_POLICY

    s_ok, scan_code = scan_artifact(artifact, meta_obj)
    if not s_ok:
        move_to_quarantine(artifact, quarantine_dir)
        append_audit({'corr': meta_obj['corr'], 'artifact_id': meta_obj['artifact_id'], 'decision': DECISION_REJECT_SCAN, 'detail': scan_code}, audit_path)
        return EXIT_SCAN

    ig_ok, ig_code = ig_verdict(meta_obj)
    if not ig_ok:
        move_to_quarantine(artifact, quarantine_dir)
        append_audit({'corr': meta_obj['corr'], 'artifact_id': meta_obj['artifact_id'], 'decision': DECISION_REJECT_IG, 'detail': ig_code}, audit_path)
        return EXIT_IG

    move_to_target(artifact, target)
    append_audit({'corr': meta_obj['corr'], 'artifact_id': meta_obj['artifact_id'], 'decision': DECISION_PROMOTE_OK, 'resolved_path': target}, audit_path)
    return EXIT_OK


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('command', choices=['process-once'])
    ap.add_argument('--artifact', required=True)
    ap.add_argument('--meta', required=True)
    ap.add_argument('--quarantine', default=axion_path_str('data', 'staging', 'quarantine'))
    ap.add_argument('--audit', default=axion_path_str('data', 'audit', 'promotion.ndjson'))
    args = ap.parse_args()

    if args.command == 'process-once':
        raise SystemExit(process_once(args.artifact, args.meta, args.quarantine, args.audit))


if __name__ == '__main__':
    main()

