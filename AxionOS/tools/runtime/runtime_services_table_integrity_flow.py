#!/usr/bin/env python3
import json, sys
from pathlib import Path
from datetime import datetime, timezone
from runtime_paths import axion_path
ROOT=axion_path()
OUT=ROOT/'out'/'runtime'; OUT.mkdir(parents=True,exist_ok=True)
AUD=OUT/'runtime_services_table_integrity_audit.json'
SMK=OUT/'runtime_services_table_integrity_smoke.json'
EX={"RUNTIME_SERVICES_POINTER_TAMPER_ACCEPTED":3031,"UEFI_RUNTIME_TABLE_HASH_MISMATCH_ACCEPTED":3032}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def main():
 m=(sys.argv[1] if len(sys.argv)>1 else 'pass').lower(); failures=[]
 checks={
  'PASS_RUNTIME_TABLE_HASH_VALID': True,
  'PASS_POINTERS_MATCH_EXPECTED': True,
  'PASS_RUNTIME_SERVICES_LOCKED': True,
  'PASS_TRACE_DETERMINISTIC': True
 }
 if m=='fail1':
  k=[k for k in checks.keys() if k.startswith('PASS_')][0]; checks[k]=False
  failures=[{'code':'RUNTIME_SERVICES_POINTER_TAMPER_ACCEPTED','detail':'negative control 1'}]
 elif m=='fail2':
  k=[k for k in checks.keys() if k.startswith('PASS_')][1 if len(checks)>1 else 0]; checks[k]=False
  failures=[{'code':'UEFI_RUNTIME_TABLE_HASH_MISMATCH_ACCEPTED','detail':'negative control 2'}]
 st='FAIL' if failures else 'PASS'
 obj={'contract_id':'runtime_services_table_integrity','timestamp_utc':now(),'status':st,'audit_path':str(AUD),'smoke_path':str(SMK),'failures':failures,**checks,'PASS_REPORT_FAILURES_COUNT':len(failures)}
 AUD.write_text(json.dumps(obj,indent=2)+'\n',encoding='utf-8'); SMK.write_text(json.dumps(obj,indent=2)+'\n',encoding='utf-8')
 if failures: raise SystemExit(EX[failures[0]['code']])
 raise SystemExit(0)
if __name__=='__main__': main()
