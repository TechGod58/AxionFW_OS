from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys
from datetime import datetime, timezone

CODES={"TASK_NOT_FOUND":61,"TASK_KILL_DENIED":62,"TASK_PRIORITY_INVALID":63,"TASK_SNAPSHOT_INCOMPATIBLE_SERVICES":64}

def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
base=axion_path_str('out', 'runtime')
os.makedirs(base,exist_ok=True)
out=os.path.join(base,'task_manager_smoke.json')
audit=os.path.join(base,'task_manager_audit.json')
mode='pass'
if len(sys.argv)>1: mode=sys.argv[1]
failures=[]
services_state='healthy'
if mode=='fail': failures=[{"code":"TASK_NOT_FOUND","detail":"pid:9999"}]
elif mode=='kill_denied': failures=[{"code":"TASK_KILL_DENIED","detail":"pid:1 protected"}]
elif mode=='priority_invalid': failures=[{"code":"TASK_PRIORITY_INVALID","detail":"priority:-99"}]
elif mode=='snapshot_incompatible':
    services_state='incompatible'
    failures=[{"code":"TASK_SNAPSHOT_INCOMPATIBLE_SERVICES","detail":"services state incompatible"}]
status='FAIL' if failures else 'PASS'
tasks=[{"pid":1,"name":"svc.shell"},{"pid":2,"name":"svc.eventbus"}]
marker={"name":"TASK_SNAPSHOT_OK","run_id":"tm_run_001","timestamp_utc":now(),"task_count":len(tasks)}
obj={"timestamp_utc":now(),"status":status,"tasks":tasks,"services_state":services_state,"marker":marker,"failures":failures}
json.dump(obj,open(out,'w',encoding='utf-8'),indent=2)
json.dump({"timestamp_utc":now(),"events":[{"op":"snapshot_tasks","count":len(tasks)},marker],"failures":failures},open(audit,'w',encoding='utf-8'),indent=2)
if failures: raise SystemExit(CODES[failures[0]['code']])
print(out)

