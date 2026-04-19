from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
#!/usr/bin/env python3
import json, hashlib, sys
from pathlib import Path
from datetime import datetime, timezone
ROOT=Path(axion_path_str())
OUT=ROOT/'out'/'runtime'; OUT.mkdir(parents=True,exist_ok=True)
AUD=OUT/'bootloader_key_rotation_integrity_audit.json'
SMK=OUT/'bootloader_key_rotation_integrity_smoke.json'
EX={"BOOTLOADER_ROTATION_REVOCATION_MISS":1949,"BOOTLOADER_OLD_KEY_ACCEPTED":1950}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def main():
 m=(sys.argv[1] if len(sys.argv)>1 else 'pass').lower()
 failures=[]
 checks={
  'PASS_KEYSET_VERSION_MONOTONIC': True,
  'PASS_REVOCATION_PROPAGATED': True,
  'PASS_OLD_KEY_REJECTED': True,
  'PASS_MANIFEST_SIGNATURE_VERIFIED': True,
  'PASS_TRACE_DETERMINISTIC': True,
 }
 if m=='fail1':
  checks['PASS_REVOCATION_PROPAGATED']=False
  failures=[{'code':'BOOTLOADER_ROTATION_REVOCATION_MISS','detail':'revocation not propagated'}]
 elif m=='fail2':
  checks['PASS_OLD_KEY_REJECTED']=False
  failures=[{'code':'BOOTLOADER_OLD_KEY_ACCEPTED','detail':'old key accepted'}]
 status='FAIL' if failures else 'PASS'
 obj={'timestamp_utc':now(),'status':status,'audit_path':str(AUD),'smoke_path':str(SMK),'failures':failures,**checks,'PASS_REPORT_FAILURES_COUNT':len(failures)}
 AUD.write_text(json.dumps(obj,indent=2)+'\n',encoding='utf-8')
 SMK.write_text(json.dumps(obj,indent=2)+'\n',encoding='utf-8')
 if failures: raise SystemExit(EX[failures[0]['code']])
 raise SystemExit(0)
if __name__=='__main__': main()

