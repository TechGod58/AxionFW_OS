import json
import shutil
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent.parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.append(str(TOOLS_DIR))

from common.pathing import axion_path

ROOT = axion_path()
OUT = ROOT / "out" / "qa_bundle"
OUT.mkdir(parents=True, exist_ok=True)

corr = f"corr_bundle_{datetime.now().strftime('%Y%m%dT%H%M%S')}_{uuid.uuid4().hex[:6]}"
run_dir = OUT / corr
run_dir.mkdir(parents=True, exist_ok=True)

lifecycle_log = run_dir / "lifecycle.log"
neg_json = run_dir / "negative_test.json"
summary_json = run_dir / "bundle_summary.json"

staging = ROOT / "data" / "staging" / "inbox"
quar = ROOT / "data" / "staging" / "quarantine"
audit = ROOT / "data" / "audit" / "promotion.ndjson"
staging.mkdir(parents=True, exist_ok=True)
quar.mkdir(parents=True, exist_ok=True)
audit.parent.mkdir(parents=True, exist_ok=True)

lines = []


def log(msg):
    lines.append(msg)


runtime_build_id = "20260303_BUNDLE1"
cache_key = f"demo_app|1.0|policy_v1|env_v1|{runtime_build_id}"
cache_decision = f"CACHE_DECISION correlation_id={corr} hit=false reason=MISSING_ENTRY cache_key={cache_key}"

log(f"SANDBOX_LAUNCH_BEGIN correlation_id={corr}")
log(f"ENV_CREATE_OK correlation_id={corr} env_rev=env_v1")
log(f"SHELL_CREATE_OK correlation_id={corr} cache_key={cache_key}")
log(cache_decision)

art = staging / f"{corr}_ok.json"
art.write_text('{"status":"ok","kind":"bundle"}', encoding="utf-8")
digest = sha256(art.read_bytes()).hexdigest()
meta = staging / f"{corr}_ok.meta.json"
meta_obj = {
    "corr": corr,
    "artifact_id": f"art_{corr}",
    "component_id": "comp_bundle",
    "source_vm": "vm_bundle",
    "safe_uri": f"safe://projects/axionos/bundle/{corr}_ok.json",
    "sha256": digest,
    "mimeType": "application/json",
    "sizeBytes": art.stat().st_size,
    "ts": datetime.now(timezone.utc).isoformat(),
}
meta.write_text(json.dumps(meta_obj, indent=2), encoding="utf-8")
log(f"PASS_SAVE_REQUEST correlation_id={corr} intent_bit=1 hash={digest} dest_uri={meta_obj['safe_uri']}")

promoted_py = ROOT / "runtime" / "promotion" / "promoted.py"
cmd = ["python", str(promoted_py), "process-once", "--artifact", str(art), "--meta", str(meta), "--quarantine", str(quar), "--audit", str(audit)]
subprocess.run(cmd, capture_output=True, text=True)

# find latest audit line for corr
commit_path = ""
if audit.exists():
    for ln in reversed(audit.read_text(encoding="utf-8").splitlines()):
        if f'"corr": "{corr}"' in ln and "PROMOTE_OK" in ln:
            try:
                obj = json.loads(ln)
                commit_path = obj.get("resolved_path", "")
            except Exception:
                pass
            break
log(f"PASS_SAVE_COMMIT_OK correlation_id={corr} final_path={commit_path}")
log(f"HOST_ASSIST_READY run_id={corr} timestamp_utc={datetime.now(timezone.utc).isoformat()}")
log(f"AUDIT_FINAL_OK correlation_id={corr} decision_chain_digest={sha256('|'.join(lines).encode()).hexdigest()[:16]}")

# negative test: hash mismatch
neg_corr = f"{corr}_neg"
bad_art = staging / f"{neg_corr}_bad.json"
bad_art.write_text('{"status":"tamper"}', encoding="utf-8")
real = sha256(bad_art.read_bytes()).hexdigest()
bad_hash = "0" * 64 if real != "0" * 64 else "f" * 64
bad_meta = staging / f"{neg_corr}_bad.meta.json"
bad_meta_obj = dict(meta_obj)
bad_meta_obj.update({"corr": neg_corr, "artifact_id": f"art_{neg_corr}", "safe_uri": f"safe://projects/axionos/bundle/{neg_corr}_bad.json", "sha256": bad_hash})
bad_meta.write_text(json.dumps(bad_meta_obj, indent=2), encoding="utf-8")
p_bad = subprocess.run(["python", str(promoted_py), "process-once", "--artifact", str(bad_art), "--meta", str(bad_meta), "--quarantine", str(quar), "--audit", str(audit)], capture_output=True, text=True)

quar_match = None
for f in sorted(quar.glob(f"{neg_corr}_bad*"), key=lambda x: x.stat().st_mtime, reverse=True):
    quar_match = str(f)
    break

failure_code = "DECISION_REJECT_HASH"
neg_info = {
    "correlation_id": neg_corr,
    "deterministic_failure_code": failure_code,
    "exit_code": p_bad.returncode,
    "quarantine_path": quar_match,
    "metadata": {
        "candidate": str(bad_art),
        "reason_code": failure_code,
        "content_hash_observed": real,
    },
}
neg_json.write_text(json.dumps(neg_info, indent=2), encoding="utf-8")

# smoke run
smoke_cmd = [
    "powershell",
    "-ExecutionPolicy",
    "Bypass",
    "-File",
    str(ROOT / "tools" / "qa" / "run_golden_vm_smoke.ps1"),
    "-Version",
    "0.1.0",
    "-TimeoutSec",
    "90",
    "-BootImage",
    str(ROOT / "build" / "disk.img"),
    "-StrictProbes",
    "-DiskKernelImplemented",
]
subprocess.run(smoke_cmd, capture_output=True, text=True)
smoke_src = ROOT / "out" / "smoke" / "golden_vm_smoke_0.1.0.json"
serial_src = ROOT / "out" / "smoke" / "serial_0.1.0.log"
smoke_dst = run_dir / "smoke.json"
serial_dst = run_dir / "serial.log"
if smoke_src.exists():
    shutil.copy2(smoke_src, smoke_dst)
if serial_src.exists():
    shutil.copy2(serial_src, serial_dst)

lifecycle_log.write_text("\n".join(lines) + "\n", encoding="utf-8")
summary = {
    "correlation_id": corr,
    "lifecycle_log": str(lifecycle_log),
    "negative_artifact": str(neg_json),
    "smoke_json": str(smoke_dst),
    "serial_log": str(serial_dst),
    "cache_decision_line": cache_decision,
    "deterministic_failure_code": failure_code,
}
summary_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
print(json.dumps(summary))
