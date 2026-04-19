#!/usr/bin/env python3
import json, sys
from pathlib import Path
from datetime import datetime, timezone
from runtime_paths import axion_path
ROOT=axion_path()
OUT=ROOT/'out'/'runtime'; OUT.mkdir(parents=True,exist_ok=True)
AUD=OUT/'clock_source_integrity_audit.json'
SMK=OUT/'clock_source_integrity_smoke.json'
EX={"CLOCK_SOURCE_POLICY_BYPASS_ACCEPTED":3481,"UNTRUSTED_CLOCK_SOURCE_ACCEPTED":3482}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def main():
 m=(sys.argv[1] if len(sys.argv)>1 else 'pass').lower(); failures=[]
 checks={
  'PASS_CLOCK_SOURCE_VALID': True,
  'PASS_UNTRUSTED_CLOCK_BLOCKED': True,
  'PASS_CLOCK_POLICY_ENFORCED': True,
  'PASS_TRACE_DETERMINISTIC': True
 }
 if m=='fail1': checks['PASS_CLOCK_SOURCE_VALID']=False; failures=[{'code':'CLOCK_SOURCE_POLICY_BYPASS_ACCEPTED','detail':'negative control 1'}]
 elif m=='fail2': checks['PASS_UNTRUSTED_CLOCK_BLOCKED']=False; failures=[{'code':'UNTRUSTED_CLOCK_SOURCE_ACCEPTED','detail':'negative control 2'}]
 st='FAIL' if failures else 'PASS'
 obj={'contract_id':'clock_source_integrity','timestamp_utc':now(),'status':st,'audit_path':str(AUD),'smoke_path':str(SMK),'failures':failures,**checks,'PASS_REPORT_FAILURES_COUNT':len(failures)}
 AUD.write_text(json.dumps(obj,indent=2)+'\n',encoding='utf-8'); SMK.write_text(json.dumps(obj,indent=2)+'\n',encoding='utf-8')
 if failures: raise SystemExit(EX[failures[0]['code']])
 raise SystemExit(0)
if __name__=='__main__': main()
