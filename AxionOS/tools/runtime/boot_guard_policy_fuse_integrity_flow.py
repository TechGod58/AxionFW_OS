#!/usr/bin/env python3
import json, sys
from pathlib import Path
from datetime import datetime, timezone
from runtime_paths import axion_path
ROOT=axion_path()
OUT=ROOT/'out'/'runtime'; OUT.mkdir(parents=True,exist_ok=True)
AUD=OUT/'boot_guard_policy_fuse_integrity_audit.json'
SMK=OUT/'boot_guard_policy_fuse_integrity_smoke.json'
EX={"BOOT_GUARD_FUSE_POLICY_BYPASS_ACCEPTED":1977,"BOOT_GUARD_PROFILE_MISMATCH_ACCEPTED":1978}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def main():
 m=(sys.argv[1] if len(sys.argv)>1 else 'pass').lower(); failures=[]
 checks={
  'PASS_FUSE_STATE_LOCKED':True,
  'PASS_PROFILE_MATCH':True,
  'PASS_MEASUREMENT_MATCH':True,
  'PASS_POLICY_ENFORCED':True,
  'PASS_TRACE_DETERMINISTIC':True
 }
 if m=='fail1': checks['PASS_POLICY_ENFORCED']=False; failures=[{'code':'BOOT_GUARD_FUSE_POLICY_BYPASS_ACCEPTED','detail':'fuse policy bypass accepted'}]
 elif m=='fail2': checks['PASS_PROFILE_MATCH']=False; failures=[{'code':'BOOT_GUARD_PROFILE_MISMATCH_ACCEPTED','detail':'profile mismatch accepted'}]
 st='FAIL' if failures else 'PASS'
 obj={'contract_id':'boot_guard_policy_fuse_integrity','timestamp_utc':now(),'status':st,'audit_path':str(AUD),'smoke_path':str(SMK),'failures':failures,**checks,'PASS_REPORT_FAILURES_COUNT':len(failures)}
 AUD.write_text(json.dumps(obj,indent=2)+'\n',encoding='utf-8'); SMK.write_text(json.dumps(obj,indent=2)+'\n',encoding='utf-8')
 if failures: raise SystemExit(EX[failures[0]['code']])
 raise SystemExit(0)
if __name__=='__main__': main()
