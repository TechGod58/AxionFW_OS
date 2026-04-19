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
import argparse
import json
import subprocess
from pathlib import Path
from hashlib import sha256

ALLOCATOR = axion_path_str('runtime', 'allocator', 'allocator_cli.py')
PROMOTED = axion_path_str('runtime', 'promotion', 'promoted.py')

STAGING = Path(axion_path_str('data', 'staging', 'inbox'))
QUAR = Path(axion_path_str('data', 'staging', 'quarantine'))
AUDIT_PROMO = Path(axion_path_str('data', 'audit', 'promotion.ndjson'))


def run_allocator(corr: str, vm_class: str, workload_class: str, cpu_used: float, mem_used: float):
    cmd = [
        "python", ALLOCATOR,
        "--vm-class", vm_class,
        "--workload-class", workload_class,
        "--cpu-used", str(cpu_used),
        "--mem-used", str(mem_used),
        "--corr", corr,
    ]
    p = subprocess.run(cmd, capture_output=True, text=True)
    parsed = None
    if p.stdout.strip():
        try:
            parsed = json.loads(p.stdout.strip())
        except json.JSONDecodeError:
            parsed = {"raw": p.stdout.strip()}
    return {"exit": p.returncode, "out": parsed, "err": p.stderr.strip()}


def run_allocate_with_promotion(corr: str):
    STAGING.mkdir(parents=True, exist_ok=True)
    QUAR.mkdir(parents=True, exist_ok=True)

    alloc = run_allocator(corr, "small", "stability_critical", 0.35, 0.45)

    art = STAGING / f"{corr}_report.json"
    art.write_text('{"status":"ok","pipeline":"e2e"}', encoding='utf-8')
    digest = sha256(art.read_bytes()).hexdigest()

    meta = STAGING / f"{corr}_report.meta.json"
    meta_obj = {
        "corr": corr,
        "artifact_id": f"art_{corr}",
        "component_id": "comp_vm_demo",
        "source_vm": "vm_demo_001",
        "safe_uri": f"safe://projects/axionos/e2e/{corr}_report.json",
        "sha256": digest,
        "mimeType": "application/json",
        "sizeBytes": art.stat().st_size,
        "ts": "2026-03-01T16:30:00Z"
    }
    meta.write_text(json.dumps(meta_obj, indent=2), encoding='utf-8')

    promo_cmd = [
        "python", PROMOTED, "process-once",
        "--artifact", str(art),
        "--meta", str(meta),
        "--quarantine", str(QUAR),
        "--audit", str(AUDIT_PROMO),
    ]
    promo = subprocess.run(promo_cmd, capture_output=True, text=True)

    return {
        "mode": "allocate",
        "corr": corr,
        "allocator": alloc,
        "promotion": {
            "exit": promo.returncode,
            "out": promo.stdout.strip(),
            "err": promo.stderr.strip(),
        }
    }


def run_queue_demo(corr: str):
    alloc = run_allocator(corr, "small", "throughput_heavy", 0.92, 0.40)
    return {"mode": "queue", "corr": corr, "allocator": alloc}


def run_deny_demo(corr: str):
    alloc = run_allocator(corr, "ultra", "latency_sensitive", 0.20, 0.30)
    return {"mode": "deny", "corr": corr, "allocator": alloc}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["all", "allocate", "queue", "deny"], default="all")
    ap.add_argument("--corr-base", default="corr_e2e")
    args = ap.parse_args()

    out = []
    if args.mode in ("all", "allocate"):
        out.append(run_allocate_with_promotion(f"{args.corr_base}_alloc_001"))
    if args.mode in ("all", "queue"):
        out.append(run_queue_demo(f"{args.corr_base}_queue_001"))
    if args.mode in ("all", "deny"):
        out.append(run_deny_demo(f"{args.corr_base}_deny_001"))

    print(json.dumps(out, indent=2))


if __name__ == '__main__':
    main()

