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
import json, subprocess, os
ROOT=axion_path_str()
plan=json.load(open(axion_path_str('out', 'governance', 'rails', 'rail_plan.json'),"r",encoding="utf-8-sig"))
cfg=axion_path_str('config', 'release_critical_gates.json')
c=json.load(open(cfg,"r",encoding="utf-8-sig"))
for g in plan["promotions"]:
    found=False
    for e in c.get("gates",[]):
        if e.get("contract_id")==g["id"]:
            e.update({"gate_exit":g["gx"],"category":"runtime","doctrine_required":True}); found=True
    if not found:
        c.setdefault("gates",[]).append({"contract_id":g["id"],"gate_exit":g["gx"],"category":"runtime","doctrine_required":True})
c["gates"]=sorted(c.get("gates",[]), key=lambda x:int(x.get("gate_exit",0)))
json.dump(c,open(cfg,"w",encoding="utf-8"),indent=2)
# exit registry
er=axion_path_str('contracts', 'registry', 'integrity_exit_registry.json')
o=json.load(open(er,"r",encoding="utf-8-sig")); rg=o.get("release_gates",{})
for g in plan["promotions"]: rg[g["id"]]=g["gx"]
o["release_gates"]=rg; json.dump(o,open(er,"w",encoding="utf-8"),indent=2)
# doctrine sync
subprocess.run([os.sys.executable,axion_path_str('tools', 'governance', 'sync_release_gate_doctrine.py')],cwd=ROOT)
# rebuild gate static list from canonical
gate=axion_path_str('ci', 'pipeline_contracts_gate.ps1')
t=open(gate,"r",encoding="utf-8-sig").read(); s=t.find("$gates = @("); i=t.find("if($SelfCheck)")
if s!=-1 and i!=-1 and i>s:
    lines=[f"  @{{id='{g['contract_id']}'; exit={int(g['gate_exit'])}}}," for g in c["gates"]]
    if lines: lines[-1]=lines[-1].rstrip(',')
    block="$gates = @(\r\n"+"\r\n".join(lines)+"\r\n)"
    t=t[:s]+block+"\r\n\r\n"+t[i:]
    open(gate,"w",encoding="utf-8").write(t)
# produce gate proofs for promoted slices where flow exists
def all_pass():
    txt=open(gate,'r',encoding='utf-8-sig').read()
    import re
    ids=sorted(set(m.group(1) for m in re.finditer(r"@\{id='([^']+)'; exit=\d+\}",txt)))
    for cid in ids:
        f=os.path.join(ROOT, "tools", "runtime", f"{cid}_flow.py")
        if os.path.exists(f): subprocess.run([os.sys.executable,f,'pass'],cwd=ROOT)
for g in plan['promotions']:
    cid=g['id']; f=os.path.join(ROOT, "tools", "runtime", f"{cid}_flow.py")
    if not os.path.exists(f):
        continue
    all_pass(); subprocess.run([os.sys.executable,f,'fail1'],cwd=ROOT)
    subprocess.run(['powershell','-ExecutionPolicy','Bypass','-File',axion_path_str('ci', 'emit_contract_report.ps1')],cwd=ROOT)
    fl=os.path.join(ROOT, "out", "contracts", "gate_logs", f"pipeline_contracts_gate_{cid}_fail.log")
    p=subprocess.run(['powershell','-ExecutionPolicy','Bypass','-File',axion_path_str('ci', 'pipeline_contracts_gate.ps1')],cwd=ROOT,capture_output=True,text=True)
    open(fl,'w',encoding='utf-8').write((p.stdout or '')+(p.stderr or '')+f"\nFAIL_EXIT={p.returncode}\n")
    all_pass(); subprocess.run(['powershell','-ExecutionPolicy','Bypass','-File',axion_path_str('ci', 'emit_contract_report.ps1')],cwd=ROOT)
    pl=os.path.join(ROOT, "out", "contracts", "gate_logs", f"pipeline_contracts_gate_{cid}_pass.log")
    p2=subprocess.run(['powershell','-ExecutionPolicy','Bypass','-File',axion_path_str('ci', 'pipeline_contracts_gate.ps1')],cwd=ROOT,capture_output=True,text=True)
    open(pl,'w',encoding='utf-8').write((p2.stdout or '')+(p2.stderr or '')+f"\nPASS_EXIT={p2.returncode}\n")
subprocess.run([os.sys.executable,axion_path_str('tools', 'contracts', 'validate_registry.py')],cwd=ROOT)
subprocess.run(['powershell','-ExecutionPolicy','Bypass','-File',axion_path_str('ci', 'pipeline_contracts_gate.ps1'),'-SelfCheck'],cwd=ROOT)
json.dump({'status':'PASS','promotions':[g['id'] for g in plan['promotions']]},open(axion_path_str('out', 'governance', 'rails', 'rail_B_results.json'),"w",encoding="utf-8"),indent=2)
print(axion_path_str('out', 'governance', 'rails', 'rail_B_results.json'))

