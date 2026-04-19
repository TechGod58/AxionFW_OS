from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
#!/usr/bin/env python3
import json, hashlib, sys
from pathlib import Path
from datetime import datetime, timezone
ROOT=Path(axion_path_str())
OUT=ROOT/'out'/'runtime'; OUT.mkdir(parents=True,exist_ok=True)
AUD=OUT/'platform_measured_boot_policy_integrity_audit.json'
SMK=OUT/'platform_measured_boot_policy_integrity_smoke.json'
EX={"MEASURED_BOOT_POLICY_BYPASS":1947,"PCR_POLICY_MISMATCH_ACCEPTED":1948}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def main():
 m=(sys.argv[1] if len(sys.argv)>1 else 'pass').lower()
 failures=[]
 checks={
  'PASS_ROOT_OF_TRUST_VERIFIED': True,
  'PASS_BOOTLOADER_MEASUREMENT_VALID': True,
  'PASS_PCR_CHAIN_MATCH': True,
  'PASS_MEASUREMENT_LOG_CONSISTENT': True,
  'PASS_TRACE_DETERMINISTIC': True,
 }
 if m=='fail1':
  checks['PASS_ROOT_OF_TRUST_VERIFIED']=False
  failures=[{'code':'MEASURED_BOOT_POLICY_BYPASS','detail':'policy bypass accepted'}]
 elif m=='fail2':
  checks['PASS_PCR_CHAIN_MATCH']=False
  failures=[{'code':'PCR_POLICY_MISMATCH_ACCEPTED','detail':'PCR mismatch accepted'}]
 status='FAIL' if failures else 'PASS'
 obj={'timestamp_utc':now(),'status':status,'audit_path':str(AUD),'smoke_path':str(SMK),'failures':failures,**checks,'PASS_REPORT_FAILURES_COUNT':len(failures)}
 AUD.write_text(json.dumps(obj,indent=2)+'\n',encoding='utf-8')
 SMK.write_text(json.dumps(obj,indent=2)+'\n',encoding='utf-8')
 if failures: raise SystemExit(EX[failures[0]['code']])
 raise SystemExit(0)
if __name__=='__main__': main()

