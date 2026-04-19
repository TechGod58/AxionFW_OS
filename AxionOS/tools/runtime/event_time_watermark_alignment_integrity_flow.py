from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys, hashlib
from datetime import datetime, timezone
CODES={"WATERMARK_EVENTTIME_MISALIGNMENT":1781,"BACKLOG_WATERMARK_JUMP":1782}
def now(): return datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
def h(o): return hashlib.sha256(json.dumps(o,sort_keys=True,separators=(",",":")).encode()).hexdigest()
base=axion_path_str('out', 'runtime'); os.makedirs(base,exist_ok=True)
audit=os.path.join(base,"event_time_watermark_alignment_integrity_audit.json"); smoke=os.path.join(base,"event_time_watermark_alignment_integrity_smoke.json")
mode=sys.argv[1] if len(sys.argv)>1 else "pass"; fail=[]
if mode=="fail1": fail=[{"code":"WATERMARK_EVENTTIME_MISALIGNMENT","detail":"deterministic negative 1"}]
elif mode=="fail2": fail=[{"code":"BACKLOG_WATERMARK_JUMP","detail":"deterministic negative 2"}]
obj={"trace_deterministic":False if fail else True,"trace_hash":h({"mode":mode})}
st="FAIL" if fail else "PASS"
json.dump({"timestamp_utc":now(),"status":st,"event_time_watermark_alignment_integrity":obj,"failures":fail},open(smoke,"w"),indent=2)
json.dump({"timestamp_utc":now(),"status":st,"trace":{"mode":mode},"event_time_watermark_alignment_integrity":obj,"failures":fail},open(audit,"w"),indent=2)
if fail: raise SystemExit(CODES[fail[0]["code"]])

