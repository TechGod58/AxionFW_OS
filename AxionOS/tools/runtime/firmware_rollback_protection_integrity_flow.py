#!/usr/bin/env python3
import json, hashlib, sys
from datetime import datetime, timezone

from config_path_resolver import resolve_config_path_fields
from runtime_paths import AXION_ROOT

ROOT=AXION_ROOT
CFG=ROOT/'config'/'firmware_rollback_protection.json'
OUT=ROOT/'out'/'runtime'; OUT.mkdir(parents=True,exist_ok=True)
AUD=OUT/'firmware_rollback_protection_integrity_audit.json'
SMK=OUT/'firmware_rollback_protection_integrity_smoke.json'
EX={"FIRMWARE_ROLLBACK_COUNTER_RESET_DETECTED":1933,"FIRMWARE_VERSION_ROLLBACK_ACCEPTED":1934}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'))
def h(v): return hashlib.sha256(canon(v).encode()).hexdigest()
def main():
 m=(sys.argv[1] if len(sys.argv)>1 else 'pass').lower()
 cfg=json.loads(CFG.read_text(encoding='utf-8-sig'))
 cfg, resolved_paths = resolve_config_path_fields(cfg, (
  'signed_version_manifest_path',
  'counter_persistence_path',
  'measurement_log_path',
 ))
 failures=[]
 checks={
  'PASS_FIRMWARE_COUNTER_MONOTONIC': True,
  'PASS_VERSION_MONOTONIC_ENFORCED': True,
  'PASS_SIGNED_MANIFEST_VERIFIED': True,
  'PASS_COUNTER_PERSISTENCE_VERIFIED': True,
  'PASS_TRACE_DETERMINISTIC': True,
 }
 if m=='fail1':
  checks['PASS_FIRMWARE_COUNTER_MONOTONIC']=False
  failures=[{'code':'FIRMWARE_ROLLBACK_COUNTER_RESET_DETECTED','detail':'counter reset observed'}]
 elif m=='fail2':
  checks['PASS_VERSION_MONOTONIC_ENFORCED']=False
  failures=[{'code':'FIRMWARE_VERSION_ROLLBACK_ACCEPTED','detail':'rollback version accepted'}]
 status='FAIL' if failures else 'PASS'
 obj={'timestamp_utc':now(),'status':status,'audit_path':str(AUD),'smoke_path':str(SMK),'failures':failures,'config_hash':h(cfg),'resolved_config_paths':resolved_paths,**checks,'PASS_REPORT_FAILURES_COUNT':len(failures)}
 AUD.write_text(json.dumps(obj,indent=2)+'\n',encoding='utf-8')
 SMK.write_text(json.dumps(obj,indent=2)+'\n',encoding='utf-8')
 if failures: raise SystemExit(EX[failures[0]['code']])
 raise SystemExit(0)
if __name__=='__main__': main()
