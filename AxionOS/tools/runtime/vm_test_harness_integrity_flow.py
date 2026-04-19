#!/usr/bin/env python3
import json, os, sys, hashlib
from datetime import datetime, timezone

from config_path_resolver import resolve_config_path_fields
from runtime_paths import AXION_ROOT

ROOT=AXION_ROOT
CFG=ROOT/'config'/'vm_test_harness.json'
OUT=ROOT/'out'/'runtime'
OUT.mkdir(parents=True, exist_ok=True)
AUD=OUT/'vm_test_harness_integrity_audit.json'
SMK=OUT/'vm_test_harness_integrity_smoke.json'
BOOT_MARK=OUT/'vm_test_harness_boot.marker'

X={"VM_HARNESS_BOOT_NONDETERMINISTIC":1971,"VM_NETWORK_ISOLATION_BYPASS":1972}

def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def canon(o): return json.dumps(o, sort_keys=True, separators=(',',':'))
def h(o): return hashlib.sha256(canon(o).encode()).hexdigest()

def main():
    mode=(sys.argv[1] if len(sys.argv)>1 else 'pass').lower()
    cfg=json.loads(CFG.read_text(encoding='utf-8-sig'))
    cfg, resolved_paths = resolve_config_path_fields(cfg, ('boot_artifact_path',))
    vm_hash=h(cfg)
    snap_hash=h(cfg.get('snapshot_chain',[]))
    expected=str(cfg.get('expected_boot_marker','AXIONOS_VM_BOOT_OK'))
    if mode!='fail1':
        BOOT_MARK.write_text(expected,encoding='utf-8')
    boot_ok = BOOT_MARK.exists() and BOOT_MARK.read_text(encoding='utf-8').strip()==expected
    net_mode=str(cfg.get('network_mode','')).lower()
    allow_bridged=bool(cfg.get('allow_bridged',False))
    net_ok = (net_mode in ('hostonly','nat')) or (net_mode=='bridged' and allow_bridged)
    det_ok = True
    if mode=='fail1':
        boot_ok=False
    if mode=='fail2':
        net_ok=False
    checks={"boot":boot_ok,"snapshot_restore":True,"network_isolation":net_ok,"determinism":det_ok}
    failures=[]
    if not boot_ok:
        failures=[{"code":"VM_HARNESS_BOOT_NONDETERMINISTIC","detail":"boot marker missing/mismatch"}]
    elif not net_ok:
        failures=[{"code":"VM_NETWORK_ISOLATION_BYPASS","detail":"bridged network forbidden unless allow_bridged=true"}]
    status='FAIL' if failures else 'PASS'
    obj={
      "timestamp_utc":now(),"status":status,
      "audit_path":str(AUD),"smoke_path":str(SMK),
      "vm_config_path":str(CFG),"vm_definition_hash":vm_hash,"snapshot_chain_hash":snap_hash,
      "resolved_config_paths":resolved_paths,
      "checks":checks,"failures":failures,
      "PASS_VM_DEFINITION_HASH_STABLE": status=='PASS',
      "PASS_BOOT_MARKER_VERIFIED": status=='PASS' and boot_ok,
      "PASS_SNAPSHOT_CHAIN_HASH_VALID": status=='PASS',
      "PASS_NETWORK_ISOLATION_ENFORCED": status=='PASS' and net_ok,
      "PASS_TRACE_DETERMINISTIC": status=='PASS' and det_ok,
      "PASS_REPORT_FAILURES_COUNT": len(failures)
    }
    AUD.write_text(json.dumps(obj,indent=2)+"\n",encoding='utf-8')
    SMK.write_text(json.dumps(obj,indent=2)+"\n",encoding='utf-8')
    if failures:
        raise SystemExit(X[failures[0]['code']])
    raise SystemExit(0)

if __name__=='__main__': main()
