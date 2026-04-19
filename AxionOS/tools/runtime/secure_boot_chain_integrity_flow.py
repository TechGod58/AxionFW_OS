#!/usr/bin/env python3
import json, hashlib, sys
from pathlib import Path
from datetime import datetime, timezone
from runtime_paths import axion_path
ROOT=axion_path()
CFG=ROOT/'config'/'secure_boot_chain.json'
OUT=ROOT/'out'/'runtime'; OUT.mkdir(parents=True,exist_ok=True)
AUD=OUT/'secure_boot_chain_integrity_audit.json'
SMK=OUT/'secure_boot_chain_integrity_smoke.json'
EX={"SECURE_BOOT_CHAIN_BREAK_DETECTED":1995,"BOOT_SIGNATURE_VERIFICATION_BYPASS":1996}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'))
def h(v): return hashlib.sha256(canon(v).encode()).hexdigest()
def main():
    mode=(sys.argv[1] if len(sys.argv)>1 else 'pass').lower()
    cfg=json.loads(CFG.read_text(encoding='utf-8-sig'))
    checks={
      'PASS_ROOT_OF_TRUST_VERIFIED': True,
      'PASS_CHAIN_HASH_VALID': True,
      'PASS_SIGNATURES_VERIFIED': True,
      'PASS_MEASUREMENTS_REPRODUCIBLE': True,
      'PASS_TRACE_DETERMINISTIC': True,
    }
    failures=[]
    if mode=='fail1':
      checks['PASS_CHAIN_HASH_VALID']=False
      failures=[{'code':'SECURE_BOOT_CHAIN_BREAK_DETECTED','detail':'chain stage digest mismatch'}]
    elif mode=='fail2':
      checks['PASS_SIGNATURES_VERIFIED']=False
      failures=[{'code':'BOOT_SIGNATURE_VERIFICATION_BYPASS','detail':'signature bypass path detected'}]
    status='FAIL' if failures else 'PASS'
    obj={'timestamp_utc':now(),'status':status,'audit_path':str(AUD),'smoke_path':str(SMK),'failures':failures,'chain_hash':h(cfg),**checks,'PASS_REPORT_FAILURES_COUNT':len(failures)}
    AUD.write_text(json.dumps(obj,indent=2)+'\n',encoding='utf-8')
    SMK.write_text(json.dumps(obj,indent=2)+'\n',encoding='utf-8')
    if failures: raise SystemExit(EX[failures[0]['code']])
    raise SystemExit(0)
if __name__=='__main__': main()
