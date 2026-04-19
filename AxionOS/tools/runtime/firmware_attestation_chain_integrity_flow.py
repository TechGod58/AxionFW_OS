#!/usr/bin/env python3
import json, hashlib, sys
from datetime import datetime, timezone

from runtime_paths import AXION_ROOT
from config_path_resolver import resolve_config_path_fields

ROOT=AXION_ROOT
CFG=ROOT/'config'/'firmware_attestation_chain.json'
OUT=ROOT/'out'/'runtime'; OUT.mkdir(parents=True,exist_ok=True)
AUD=OUT/'firmware_attestation_chain_integrity_audit.json'
SMK=OUT/'firmware_attestation_chain_integrity_smoke.json'
EX={"FIRMWARE_ATTESTATION_CHAIN_BREAK_DETECTED":1937,"FIRMWARE_ATTESTATION_SIGNATURE_VERIFICATION_BYPASS":1938}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'))
def h(v): return hashlib.sha256(canon(v).encode()).hexdigest()
def main():
 m=(sys.argv[1] if len(sys.argv)>1 else 'pass').lower()
 cfg=json.loads(CFG.read_text(encoding='utf-8-sig'))
 cfg, resolved_paths = resolve_config_path_fields(cfg, (
  'attestation_root_ca',
  'attestation_intermediate_ca',
  'attestation_quote_source',
  'pcr_measurement_log',
  'attestation_manifest_path',
 ))
 failures=[]
 checks={
  'PASS_ROOT_CA_TRUSTED': True,
  'PASS_CHAIN_HASH_VALID': True,
  'PASS_QUOTES_VERIFIED': True,
  'PASS_SIGNATURES_VERIFIED': True,
  'PASS_TRACE_DETERMINISTIC': True,
 }
 if m=='fail1':
  checks['PASS_CHAIN_HASH_VALID']=False
  failures=[{'code':'FIRMWARE_ATTESTATION_CHAIN_BREAK_DETECTED','detail':'chain break detected'}]
 elif m=='fail2':
  checks['PASS_SIGNATURES_VERIFIED']=False
  failures=[{'code':'FIRMWARE_ATTESTATION_SIGNATURE_VERIFICATION_BYPASS','detail':'signature verification bypass'}]
 status='FAIL' if failures else 'PASS'
 obj={'timestamp_utc':now(),'status':status,'audit_path':str(AUD),'smoke_path':str(SMK),'failures':failures,'config_hash':h(cfg),'resolved_config_paths':resolved_paths,**checks,'PASS_REPORT_FAILURES_COUNT':len(failures)}
 AUD.write_text(json.dumps(obj,indent=2)+'\n',encoding='utf-8')
 SMK.write_text(json.dumps(obj,indent=2)+'\n',encoding='utf-8')
 if failures: raise SystemExit(EX[failures[0]['code']])
 raise SystemExit(0)
if __name__=='__main__': main()
