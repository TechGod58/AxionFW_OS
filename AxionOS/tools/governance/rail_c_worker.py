import sys
from pathlib import Path

_TOOLS_DIR = None
for _parent in Path(__file__).resolve().parents:
    if (_parent / "tools" / "common" / "pathing.py").exists():
        _TOOLS_DIR = _parent / "tools"
        break
if _TOOLS_DIR and str(_TOOLS_DIR) not in sys.path:
    sys.path.append(str(_TOOLS_DIR))

from common.pathing import axion_path


def axion_path_str(*parts):
    return str(axion_path(*parts))
import json, subprocess, os, hashlib
from datetime import datetime, timezone
ROOT=axion_path_str()
cmds=[
 [os.sys.executable,axion_path_str('tools', 'governance', 'emit_release_gate_inventory.py')],
 [os.sys.executable,axion_path_str('tools', 'governance', 'emit_integrity_coverage_map.py')],
 [os.sys.executable,axion_path_str('tools', 'governance', 'emit_governance_drift_check.py')],
 [os.sys.executable,axion_path_str('tools', 'governance', 'emit_governance_baseline_drift.py')]
]
res=[]
for c in cmds:
    p=subprocess.run(c,cwd=ROOT)
    res.append({'cmd':' '.join(c),'exit':p.returncode})
def sha(p):
    return hashlib.sha256(open(p,'rb').read()).hexdigest() if os.path.exists(p) else None
chk=os.path.join(ROOT, "out", "governance", f"AXIONOS_INTEGRITY_CHECKPOINT_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_POST_PARALLEL_RAILS.json")
obj={'timestamp_utc':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),'hashes':{
'gate_registry':sha(axion_path_str('config', 'release_critical_gates.json')),
'gate_script':sha(axion_path_str('ci', 'pipeline_contracts_gate.ps1')),
'doctrine':sha(axion_path_str('design', 'ops', 'CONTRACT_FIRST_DEVELOPMENT_LOOP_V1.md')),
'exit_registry':sha(axion_path_str('contracts', 'registry', 'integrity_exit_registry.json')),
'inventory':sha(axion_path_str('out', 'contracts', 'release_critical_gates_inventory.json')),
'coverage':sha(axion_path_str('out', 'governance', 'integrity_coverage_map.json')),
'drift':sha(axion_path_str('out', 'contracts', 'governance_drift_check.json')),
'baseline':sha(axion_path_str('out', 'contracts', 'governance_baseline_drift.json'))}}
os.makedirs(os.path.dirname(chk),exist_ok=True)
json.dump(obj,open(chk,'w',encoding='utf-8'),indent=2)
out=axion_path_str('out', 'governance', 'rails', 'rail_C_results.json')
json.dump({'status':'PASS','commands':res,'checkpoint':chk},open(out,'w',encoding='utf-8'),indent=2)
print(out)

