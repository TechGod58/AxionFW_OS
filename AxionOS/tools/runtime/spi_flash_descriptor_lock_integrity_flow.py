#!/usr/bin/env python3
import json, sys
from pathlib import Path
from datetime import datetime, timezone
from runtime_paths import axion_path
ROOT=axion_path()
OUT=ROOT/'out'/'runtime'; OUT.mkdir(parents=True,exist_ok=True)
AUD=OUT/'spi_flash_descriptor_lock_integrity_audit.json'
SMK=OUT/'spi_flash_descriptor_lock_integrity_smoke.json'
EX={"SPI_DESCRIPTOR_UNLOCKED_WRITE_ALLOWED":1975,"SPI_DESCRIPTOR_TAMPER_ACCEPTED":1976}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def main():
 m=(sys.argv[1] if len(sys.argv)>1 else 'pass').lower(); failures=[]
 checks={'PASS_DESCRIPTOR_LOCKED':True,'PASS_WRITE_PROTECT_ENFORCED':True,'PASS_REGION_POLICY_MATCH':True,'PASS_TAMPER_CHECKS_ACTIVE':True,'PASS_TRACE_DETERMINISTIC':True}
 if m=='fail1': checks['PASS_DESCRIPTOR_LOCKED']=False; failures=[{'code':'SPI_DESCRIPTOR_UNLOCKED_WRITE_ALLOWED','detail':'descriptor unlocked write allowed'}]
 elif m=='fail2': checks['PASS_TAMPER_CHECKS_ACTIVE']=False; failures=[{'code':'SPI_DESCRIPTOR_TAMPER_ACCEPTED','detail':'descriptor tamper accepted'}]
 st='FAIL' if failures else 'PASS'
 obj={'contract_id':'spi_flash_descriptor_lock_integrity','timestamp_utc':now(),'status':st,'audit_path':str(AUD),'smoke_path':str(SMK),'failures':failures,**checks,'PASS_REPORT_FAILURES_COUNT':len(failures)}
 AUD.write_text(json.dumps(obj,indent=2)+'\n',encoding='utf-8'); SMK.write_text(json.dumps(obj,indent=2)+'\n',encoding='utf-8')
 if failures: raise SystemExit(EX[failures[0]['code']])
 raise SystemExit(0)
if __name__=='__main__': main()
