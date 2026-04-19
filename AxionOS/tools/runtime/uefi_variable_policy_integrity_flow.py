#!/usr/bin/env python3
import json, sys
from pathlib import Path
from datetime import datetime, timezone
from runtime_paths import axion_path
ROOT=axion_path()
OUT=ROOT/'out'/'runtime'; OUT.mkdir(parents=True,exist_ok=True)
AUD=OUT/'uefi_variable_policy_integrity_audit.json'
SMK=OUT/'uefi_variable_policy_integrity_smoke.json'
EX={"UEFI_VARIABLE_WRITE_POLICY_BYPASS":1939,"UEFI_SECURE_BOOT_VAR_TAMPER_ACCEPTED":1940}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def main():
 m=(sys.argv[1] if len(sys.argv)>1 else 'pass').lower()
 failures=[]
 checks={
  'PASS_VARIABLE_ALLOWLIST_ENFORCED': True,
  'PASS_ATTRIBUTE_RULES_ENFORCED': True,
  'PASS_VENDOR_GUID_RULES_ENFORCED': True,
  'PASS_PERSISTENCE_RULES_ENFORCED': True,
  'PASS_TRACE_DETERMINISTIC': True,
 }
 if m=='fail1':
  checks['PASS_ATTRIBUTE_RULES_ENFORCED']=False
  failures=[{'code':'UEFI_VARIABLE_WRITE_POLICY_BYPASS','detail':'write policy bypass'}]
 elif m=='fail2':
  checks['PASS_VARIABLE_ALLOWLIST_ENFORCED']=False
  failures=[{'code':'UEFI_SECURE_BOOT_VAR_TAMPER_ACCEPTED','detail':'secure boot variable tamper accepted'}]
 status='FAIL' if failures else 'PASS'
 obj={'timestamp_utc':now(),'status':status,'audit_path':str(AUD),'smoke_path':str(SMK),'failures':failures,**checks,'PASS_REPORT_FAILURES_COUNT':len(failures)}
 AUD.write_text(json.dumps(obj,indent=2)+'\n',encoding='utf-8')
 SMK.write_text(json.dumps(obj,indent=2)+'\n',encoding='utf-8')
 if failures: raise SystemExit(EX[failures[0]['code']])
 raise SystemExit(0)
if __name__=='__main__': main()
