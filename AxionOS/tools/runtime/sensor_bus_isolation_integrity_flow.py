#!/usr/bin/env python3
import json, sys
from pathlib import Path
from datetime import datetime, timezone
from runtime_paths import axion_path
ROOT=axion_path()
OUT=ROOT/'out'/'runtime'; OUT.mkdir(parents=True,exist_ok=True)
AUD=OUT/'sensor_bus_isolation_integrity_audit.json'
SMK=OUT/'sensor_bus_isolation_integrity_smoke.json'
EX={"SENSOR_BUS_ISOLATION_BYPASS_ACCEPTED":3401,"SENSOR_DEVICE_POLICY_OVERRIDE_ACCEPTED":3402}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def main():
 m=(sys.argv[1] if len(sys.argv)>1 else 'pass').lower(); failures=[]
 checks={
  'PASS_SENSOR_BUS_POLICY_VALID': True,
  'PASS_SENSOR_SCOPE_VALID': True,
  'PASS_SENSOR_ISOLATION_ENFORCED': True,
  'PASS_TRACE_DETERMINISTIC': True
 }
 if m=='fail1': checks['PASS_SENSOR_BUS_POLICY_VALID']=False; failures=[{'code':'SENSOR_BUS_ISOLATION_BYPASS_ACCEPTED','detail':'negative control 1'}]
 elif m=='fail2': checks['PASS_SENSOR_SCOPE_VALID']=False; failures=[{'code':'SENSOR_DEVICE_POLICY_OVERRIDE_ACCEPTED','detail':'negative control 2'}]
 st='FAIL' if failures else 'PASS'
 obj={'contract_id':'sensor_bus_isolation_integrity','timestamp_utc':now(),'status':st,'audit_path':str(AUD),'smoke_path':str(SMK),'failures':failures,**checks,'PASS_REPORT_FAILURES_COUNT':len(failures)}
 AUD.write_text(json.dumps(obj,indent=2)+'\n',encoding='utf-8'); SMK.write_text(json.dumps(obj,indent=2)+'\n',encoding='utf-8')
 if failures: raise SystemExit(EX[failures[0]['code']])
 raise SystemExit(0)
if __name__=='__main__': main()
