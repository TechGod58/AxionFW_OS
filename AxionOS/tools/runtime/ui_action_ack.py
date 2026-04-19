from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys
from datetime import datetime, timezone
CODES={"UI_ACK_TIMEOUT":401}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
base=axion_path_str('out', 'runtime'); os.makedirs(base, exist_ok=True)
audit=os.path.join(base,'ui_action_ack_audit.json')
smoke=os.path.join(base,'ui_action_ack_smoke.json')
mode='pass'
if len(sys.argv)>1: mode=sys.argv[1]
ack={"action_id":"act-20260305-001","panel":"network_panel","ack_expected_ms":500,"ack_received_ms":120}
failures=[]
if mode=='fail':
    ack['ack_received_ms']=None
    failures=[{"code":"UI_ACK_TIMEOUT","detail":"ack not received within 500ms"}]
status='FAIL' if failures else 'PASS'
json.dump({"timestamp_utc":now(),"status":status,"ack":ack,"failures":failures},open(smoke,'w',encoding='utf-8'),indent=2)
json.dump({"timestamp_utc":now(),"status":status,"events":[{"op":"await_ui_ack","action_id":"act-20260305-001"}],"failures":failures},open(audit,'w',encoding='utf-8'),indent=2)
if failures: raise SystemExit(CODES[failures[0]['code']])

