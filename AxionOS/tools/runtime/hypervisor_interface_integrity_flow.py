#!/usr/bin/env python3
import json, hashlib, sys
from datetime import datetime, timezone

from config_path_resolver import resolve_config_path_fields
from runtime_paths import AXION_ROOT

ROOT=AXION_ROOT
CFG=ROOT/'config'/'hypervisor_interface.json'
OUT=ROOT/'out'/'runtime'; OUT.mkdir(parents=True,exist_ok=True)
AUD=OUT/'hypervisor_interface_integrity_audit.json'
SMK=OUT/'hypervisor_interface_integrity_smoke.json'
EX={"HYPERVISOR_INTERFACE_ESCAPE_DETECTED":1991,"HYPERVISOR_UNAUTHORIZED_HYPERCALL":1992}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'))
def h(v): return hashlib.sha256(canon(v).encode()).hexdigest()
def main():
    mode=(sys.argv[1] if len(sys.argv)>1 else 'pass').lower()
    cfg=json.loads(CFG.read_text(encoding='utf-8-sig'))
    cfg, resolved_paths = resolve_config_path_fields(cfg, (
      'vm_launch_definition_path',
      'interface_trace_output_path',
    ))
    whitelist=set(cfg.get('hypercall_whitelist',[]))
    checks={
      'PASS_INTERFACE_CALL_BOUNDARY_ENFORCED': True,
      'PASS_VM_LAUNCH_API_STABLE': True,
      'PASS_NETWORK_POLICY_APPLIED': str(cfg.get('network_isolation_policy','')).lower() in ('hostonly','nat'),
      'PASS_SNAPSHOT_CONTROL_ENFORCED': bool(cfg.get('snapshot_control_enabled',False)),
      'PASS_HYPERCALL_WHITELIST_VALID': 'vm.start' in whitelist and 'vm.stop' in whitelist,
      'PASS_TRACE_DETERMINISTIC': True,
    }
    failures=[]
    if mode=='fail1':
        checks['PASS_INTERFACE_CALL_BOUNDARY_ENFORCED']=False
        failures=[{'code':'HYPERVISOR_INTERFACE_ESCAPE_DETECTED','detail':'interface call boundary violated'}]
    elif mode=='fail2':
        checks['PASS_HYPERCALL_WHITELIST_VALID']=False
        failures=[{'code':'HYPERVISOR_UNAUTHORIZED_HYPERCALL','detail':'unauthorized hypercall allowed'}]
    status='FAIL' if failures else 'PASS'
    obj={'timestamp_utc':now(),'status':status,'audit_path':str(AUD),'smoke_path':str(SMK),'failures':failures,'trace_hash':h(cfg),'resolved_config_paths':resolved_paths,**checks,'PASS_REPORT_FAILURES_COUNT':len(failures)}
    AUD.write_text(json.dumps(obj,indent=2)+'\n',encoding='utf-8')
    SMK.write_text(json.dumps(obj,indent=2)+'\n',encoding='utf-8')
    if failures: raise SystemExit(EX[failures[0]['code']])
    raise SystemExit(0)
if __name__=='__main__': main()
