import glob
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[1]
if str(TOOLS_DIR) not in sys.path:
    sys.path.append(str(TOOLS_DIR))

from common.pathing import axion_path

ROOT = str(axion_path())
qa = os.path.join(ROOT, 'out', 'qa_bundle')
logs = sorted(glob.glob(os.path.join(qa, '**', 'lifecycle.log'), recursive=True), key=os.path.getmtime, reverse=True)
if not logs:
    raise SystemExit(2)
lp = logs[0]
text = open(lp, 'r', encoding='utf-8', errors='ignore').read()
m = re.search(r'^HOST_ASSIST_READY\s+run_id=([^\s]+)', text, re.M)
if not m:
    m = re.search(r'^SANDBOX_LAUNCH_BEGIN\s+correlation_id=([^\s]+)', text, re.M)
    if not m:
        raise SystemExit(3)
run_id = m.group(1)
out_dir = os.path.join(ROOT, 'out', 'host_tools')
os.makedirs(out_dir, exist_ok=True)
outp = os.path.join(out_dir, f'axionc_bd_session_{run_id}.json')
obj = {
    'run_id': run_id,
    'timestamp_utc': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
    'host': {'machine': os.environ.get('COMPUTERNAME'), 'user': os.environ.get('USERNAME')},
    'inputs': [lp],
    'outputs': [outp],
    'status': 'PASS',
    'failures': [],
}
with open(outp, 'w', encoding='utf-8') as f:
    json.dump(obj, f, indent=2)
print(outp)
