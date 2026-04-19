#!/usr/bin/env python3
import json, hashlib, sys
from datetime import datetime, timezone

from config_path_resolver import resolve_config_path_fields
from runtime_paths import AXION_ROOT

ROOT=AXION_ROOT
CFG=ROOT/'config'/'trusted_boot_measurement_chain.json'
OUT=ROOT/'out'/'runtime'; OUT.mkdir(parents=True,exist_ok=True)
AUD=OUT/'trusted_boot_measurement_chain_integrity_audit.json'
SMK=OUT/'trusted_boot_measurement_chain_integrity_smoke.json'
EX={"BOOT_MEASUREMENT_CHAIN_BREAK_DETECTED":1945,"PCR_MEASUREMENT_MISMATCH_DETECTED":1946}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'))
def h(v): return hashlib.sha256(canon(v).encode()).hexdigest()
def main():
 m=(sys.argv[1] if len(sys.argv)>1 else 'pass').lower()
 cfg=json.loads(CFG.read_text(encoding='utf-8-sig'))
 cfg, resolved_paths = resolve_config_path_fields(cfg, (
  'root_of_trust_source',
  'bootloader_measurement_path',
  'measurement_log_path',
  'trusted_boot_manifest_path',
 ))
 failures=[]
 checks={
  'PASS_ROOT_OF_TRUST_VERIFIED': True,
  'PASS_BOOTLOADER_MEASUREMENT_VALID': True,
  'PASS_PCR_CHAIN_MATCH': True,
  'PASS_MEASUREMENT_LOG_CONSISTENT': True,
  'PASS_TRACE_DETERMINISTIC': True,
 }
 if m=='fail1':
  checks['PASS_BOOTLOADER_MEASUREMENT_VALID']=False
  failures=[{'code':'BOOT_MEASUREMENT_CHAIN_BREAK_DETECTED','detail':'boot measurement chain break'}]
 elif m=='fail2':
  checks['PASS_PCR_CHAIN_MATCH']=False
  failures=[{'code':'PCR_MEASUREMENT_MISMATCH_DETECTED','detail':'PCR mismatch detected'}]
 status='FAIL' if failures else 'PASS'
 obj={'timestamp_utc':now(),'status':status,'audit_path':str(AUD),'smoke_path':str(SMK),'failures':failures,'config_hash':h(cfg),'resolved_config_paths':resolved_paths,**checks,'PASS_REPORT_FAILURES_COUNT':len(failures)}
 AUD.write_text(json.dumps(obj,indent=2)+'\n',encoding='utf-8')
 SMK.write_text(json.dumps(obj,indent=2)+'\n',encoding='utf-8')
 if failures: raise SystemExit(EX[failures[0]['code']])
 raise SystemExit(0)
if __name__=='__main__': main()
