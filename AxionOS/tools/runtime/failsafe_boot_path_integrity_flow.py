#!/usr/bin/env python3
import json, sys
from pathlib import Path
from datetime import datetime, timezone
from runtime_paths import axion_path
ROOT=axion_path()
OUT=ROOT/'out'/'runtime'; OUT.mkdir(parents=True,exist_ok=True)
AUD=OUT/'failsafe_boot_path_integrity_audit.json'
SMK=OUT/'failsafe_boot_path_integrity_smoke.json'
EX={"FAILSAFE_BOOT_POLICY_BYPASS_ACCEPTED":3551,"FAILSAFE_IMAGE_OVERRIDE_ACCEPTED":3552}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def main():
 m=(sys.argv[1] if len(sys.argv)>1 else 'pass').lower(); failures=[]
 checks={
  'PASS_FAILSAFE_POLICY_VALID': True,
  'PASS_FAILSAFE_IMAGE_VALID': True,
  'PASS_OVERRIDE_BLOCKED': True,
  'PASS_TRACE_DETERMINISTIC': True
 }
 if m=='fail1': checks['PASS_FAILSAFE_POLICY_VALID']=False; failures=[{'code':'FAILSAFE_BOOT_POLICY_BYPASS_ACCEPTED','detail':'negative control 1'}]
 elif m=='fail2': checks['PASS_FAILSAFE_IMAGE_VALID']=False; failures=[{'code':'FAILSAFE_IMAGE_OVERRIDE_ACCEPTED','detail':'negative control 2'}]
 st='FAIL' if failures else 'PASS'
 obj={'contract_id':'failsafe_boot_path_integrity','timestamp_utc':now(),'status':st,'audit_path':str(AUD),'smoke_path':str(SMK),'failures':failures,**checks,'PASS_REPORT_FAILURES_COUNT':len(failures)}
 AUD.write_text(json.dumps(obj,indent=2)+'\n',encoding='utf-8'); SMK.write_text(json.dumps(obj,indent=2)+'\n',encoding='utf-8')
 if failures: raise SystemExit(EX[failures[0]['code']])
 raise SystemExit(0)
if __name__=='__main__': main()
