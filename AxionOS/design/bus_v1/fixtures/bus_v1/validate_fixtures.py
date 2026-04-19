import json
from pathlib import Path

try:
    import jsonschema
except ImportError:
    raise SystemExit("Install dependency: pip install jsonschema")

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "AXIONOS_BUS_CONTRACT_V1.schema.json"
FIXTURES_DIR = Path(__file__).resolve().parent

with SCHEMA_PATH.open("r", encoding="utf-8") as f:
    schema = json.load(f)

expected = {
    "pass_component_register.json": True,
    "pass_route_request.json": True,
    "pass_ig_verdict_fail.json": True,
    "fail_missing_corr.json": False,
    "fail_bad_type.json": False,
    "fail_bad_workload_class.json": False,
}

all_ok = True
for name, should_pass in expected.items():
    p = FIXTURES_DIR / name
    doc = json.loads(p.read_text(encoding="utf-8"))
    ok = True
    try:
        jsonschema.validate(instance=doc, schema=schema)
    except jsonschema.ValidationError:
        ok = False

    verdict = "PASS" if ok else "FAIL"
    exp = "PASS" if should_pass else "FAIL"
    status = "OK" if ok == should_pass else "MISMATCH"
    print(f"{name}: got={verdict} expected={exp} => {status}")
    if ok != should_pass:
        all_ok = False

raise SystemExit(0 if all_ok else 1)
