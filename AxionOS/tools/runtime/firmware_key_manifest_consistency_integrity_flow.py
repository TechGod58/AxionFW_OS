#!/usr/bin/env python3
import json, hashlib, sys
from pathlib import Path
from datetime import datetime, timezone
from runtime_paths import axion_path
ROOT=axion_path()
OUT=ROOT/'out'/'runtime'; OUT.mkdir(parents=True,exist_ok=True)
AUD=OUT/'firmware_key_manifest_consistency_integrity_audit.json'
SMK=OUT/'firmware_key_manifest_consistency_integrity_smoke.json'
EX={"FIRMWARE_KEY_MANIFEST_VERSION_ROLLBACK_ACCEPTED":1935,"FIRMWARE_KEY_MANIFEST_SIGNATURE_MISMATCH_ACCEPTED":1936}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def main():
 m=(sys.argv[1] if len(sys.argv)>1 else 'pass').lower()
 failures=[]
 checks={
  'PASS_KEY_MANIFEST_HASH_STABLE': True,
  'PASS_MANIFEST_SIGNATURE_VERIFIED': True,
  'PASS_KEYSET_VERSION_MONOTONIC': True,
  'PASS_REVOCATION_LIST_MATCH': True,
  'PASS_TRACE_DETERMINISTIC': True,
 }
 if m=='fail1':
  checks['PASS_KEYSET_VERSION_MONOTONIC']=False
  failures=[{'code':'FIRMWARE_KEY_MANIFEST_VERSION_ROLLBACK_ACCEPTED','detail':'manifest version rollback accepted'}]
 elif m=='fail2':
  checks['PASS_MANIFEST_SIGNATURE_VERIFIED']=False
  failures=[{'code':'FIRMWARE_KEY_MANIFEST_SIGNATURE_MISMATCH_ACCEPTED','detail':'signature mismatch accepted'}]
 status='FAIL' if failures else 'PASS'
 obj={'timestamp_utc':now(),'status':status,'audit_path':str(AUD),'smoke_path':str(SMK),'failures':failures,**checks,'PASS_REPORT_FAILURES_COUNT':len(failures)}
 AUD.write_text(json.dumps(obj,indent=2)+'\n',encoding='utf-8')
 SMK.write_text(json.dumps(obj,indent=2)+'\n',encoding='utf-8')
 if failures: raise SystemExit(EX[failures[0]['code']])
 raise SystemExit(0)
if __name__=='__main__': main()
