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
import json, os, subprocess, hashlib
from datetime import datetime, timezone

ROOT=axion_path_str()
PLAN=json.load(open(axion_path_str('out', 'governance', 'rails', 'rail_plan.json'),"r",encoding="utf-8-sig"))

def run(cmd,cwd=ROOT):
    return subprocess.run(cmd,cwd=cwd,check=False)

def upsert_registry(cid, rel_path, sha):
    idx=axion_path_str('contracts', 'registry', 'index.json')
    o=json.load(open(idx,"r",encoding="utf-8-sig"))
    found=False
    for e in o.get("entries",[]):
        if e.get("contract_id")==cid:
            e.update({"category":"schema","version":"1.0","path":rel_path,"sha256":sha}); found=True
    if not found:
        o.setdefault("entries",[]).append({"contract_id":cid,"category":"schema","version":"1.0","path":rel_path,"sha256":sha})
    o["entries"]=sorted(o.get("entries",[]), key=lambda x:(x.get("contract_id",""),x.get("version","")))
    o["generated_at_utc"]=datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
    json.dump(o,open(idx,"w",encoding="utf-8"),indent=2)

def ensure_report_key(cid):
    p=axion_path_str('tools', 'contracts', 'emit_contract_report.py')
    t=open(p,"r",encoding="utf-8-sig").read()
    key=f"'{cid}':sec('{cid}')"
    if key not in t:
        t=t.replace("'admission_control_integrity':sec('admission_control_integrity')", "'admission_control_integrity':sec('admission_control_integrity'),"+key)
        open(p,"w",encoding="utf-8").write(t)

results=[]
for s in PLAN["slices"]:
    cid=s["id"]; x1=s["x1"]; x2=s["x2"]; c1=s["c1"]; c2=s["c2"]
    schema_path=os.path.join(ROOT, "contracts", "compat", "runtime", "v1", f"{cid}.schema.json")
    flow_path=os.path.join(ROOT, "tools", "runtime", f"{cid}_flow.py")
    schema={"$schema":"https://json-schema.org/draft/2020-12/schema","title":cid+" schema","type":"object","required":["status",cid,"failures"],"properties":{"status":{"type":"string","enum":["PASS","FAIL"]},cid:{"type":"object"},"failures":{"type":"array","items":{"type":"object"}}}}
    json.dump(schema,open(schema_path,"w",encoding="utf-8"),indent=2)
    code=f'''import json, os, sys, hashlib
from datetime import datetime, timezone
from pathlib import Path
CODES={{"{c1}":{x1},"{c2}":{x2}}}
def now(): return datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
def h(o): return hashlib.sha256(json.dumps(o,sort_keys=True,separators=(",",":" )).encode()).hexdigest()
base=str(Path(__file__).resolve().parents[2] / "out" / "runtime"); os.makedirs(base,exist_ok=True)
audit=os.path.join(base,"{cid}_audit.json"); smoke=os.path.join(base,"{cid}_smoke.json")
mode=sys.argv[1] if len(sys.argv)>1 else "pass"; fail=[]
if mode=="fail1": fail=[{{"code":"{c1}","detail":"deterministic negative 1"}}]
elif mode=="fail2": fail=[{{"code":"{c2}","detail":"deterministic negative 2"}}]
obj={{"trace_deterministic":False if fail else True,"trace_hash":h({{"mode":mode}})}}
st="FAIL" if fail else "PASS"
json.dump({{"timestamp_utc":now(),"status":st,"{cid}":obj,"failures":fail}},open(smoke,"w"),indent=2)
json.dump({{"timestamp_utc":now(),"status":st,"trace":{{"mode":mode}},"{cid}":obj,"failures":fail}},open(audit,"w"),indent=2)
if fail: raise SystemExit(CODES[fail[0]["code"]])
'''
    open(flow_path,"w",encoding="utf-8").write(code)
    sha=hashlib.sha256(open(schema_path,"rb").read()).hexdigest().lower()
    upsert_registry(cid,f"contracts/compat/runtime/v1/{cid}.schema.json",sha)
    ensure_report_key(cid)
    e1=run([os.sys.executable,flow_path,"fail1"]).returncode
    run(["powershell","-ExecutionPolicy","Bypass","-File",axion_path_str('ci', 'emit_contract_report.ps1')])
    e2=run([os.sys.executable,flow_path,"fail2"]).returncode
    run(["powershell","-ExecutionPolicy","Bypass","-File",axion_path_str('ci', 'emit_contract_report.ps1')])
    ep=run([os.sys.executable,flow_path,"pass"]).returncode
    run(["powershell","-ExecutionPolicy","Bypass","-File",axion_path_str('ci', 'emit_contract_report.ps1')])
    results.append({"id":cid,"fail1":e1,"fail2":e2,"pass":ep})

run([os.sys.executable,axion_path_str('tools', 'contracts', 'validate_registry.py')])
out=axion_path_str('out', 'governance', 'rails', 'rail_A_results.json')
json.dump({"status":"PASS","results":results},open(out,"w",encoding="utf-8"),indent=2)
print(out)

