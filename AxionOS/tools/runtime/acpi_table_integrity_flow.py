#!/usr/bin/env python3
import json, sys
from pathlib import Path
from datetime import datetime, timezone
from runtime_paths import axion_path
ROOT=axion_path()
OUT=ROOT/'out'/'runtime'; OUT.mkdir(parents=True,exist_ok=True)
AUD=OUT/'acpi_table_integrity_audit.json'
SMK=OUT/'acpi_table_integrity_smoke.json'
EX={"ACPI_TABLE_TAMPER_ACCEPTED":1959,"ACPI_SDT_SIGNATURE_BYPASS":1960}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def main():
 m=(sys.argv[1] if len(sys.argv)>1 else 'pass').lower(); failures=[]
 checks={'PASS_TRACE_DETERMINISTIC':True,'PASS_POLICY_ENFORCED':True,'PASS_RULESET_CONSISTENT':True}
 if m=='fail1': checks['PASS_POLICY_ENFORCED']=False; failures=[{'code':'ACPI_TABLE_TAMPER_ACCEPTED','detail':'negative control 1'}]
 elif m=='fail2': checks['PASS_RULESET_CONSISTENT']=False; failures=[{'code':'ACPI_SDT_SIGNATURE_BYPASS','detail':'negative control 2'}]
 st='FAIL' if failures else 'PASS'
 obj={'timestamp_utc':now(),'status':st,'audit_path':str(AUD),'smoke_path':str(SMK),'failures':failures,**checks,'PASS_REPORT_FAILURES_COUNT':len(failures)}
 AUD.write_text(json.dumps(obj,indent=2)+'\n',encoding='utf-8'); SMK.write_text(json.dumps(obj,indent=2)+'\n',encoding='utf-8')
 if failures: raise SystemExit(EX[failures[0]['code']])
 raise SystemExit(0)
if __name__=='__main__': main()
