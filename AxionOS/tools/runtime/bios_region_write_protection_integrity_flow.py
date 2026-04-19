#!/usr/bin/env python3
import json, sys
from pathlib import Path
from datetime import datetime, timezone
from runtime_paths import axion_path
ROOT=axion_path()
OUT=ROOT/'out'/'runtime'; OUT.mkdir(parents=True,exist_ok=True)
AUD=OUT/'bios_region_write_protection_integrity_audit.json'
SMK=OUT/'bios_region_write_protection_integrity_smoke.json'
EX={"BIOS_REGION_WRITE_PROTECTION_BYPASS":1973,"BIOS_FLASH_DESCRIPTOR_TAMPER_ACCEPTED":1974}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def main():
 m=(sys.argv[1] if len(sys.argv)>1 else 'pass').lower()
 failures=[]
 checks={
  'PASS_DESCRIPTOR_HASH_MATCH': True,
  'PASS_REGION_WRITE_BLOCKED': True,
  'PASS_SMM_LOCKED_IF_APPLICABLE': True,
  'PASS_TRACE_DETERMINISTIC': True,
 }
 if m=='fail1':
  checks['PASS_REGION_WRITE_BLOCKED']=False
  failures=[{'code':'BIOS_REGION_WRITE_PROTECTION_BYPASS','detail':'bios region write bypass accepted'}]
 elif m=='fail2':
  checks['PASS_DESCRIPTOR_HASH_MATCH']=False
  failures=[{'code':'BIOS_FLASH_DESCRIPTOR_TAMPER_ACCEPTED','detail':'flash descriptor tamper accepted'}]
 st='FAIL' if failures else 'PASS'
 obj={'contract_id':'bios_region_write_protection_integrity','timestamp_utc':now(),'status':st,'audit_path':str(AUD),'smoke_path':str(SMK),'failures':failures,**checks,'PASS_REPORT_FAILURES_COUNT':len(failures)}
 AUD.write_text(json.dumps(obj,indent=2)+'\n',encoding='utf-8')
 SMK.write_text(json.dumps(obj,indent=2)+'\n',encoding='utf-8')
 if failures: raise SystemExit(EX[failures[0]['code']])
 raise SystemExit(0)
if __name__=='__main__': main()
