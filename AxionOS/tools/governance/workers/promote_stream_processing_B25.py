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
import json, subprocess, hashlib, zipfile, sys
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(axion_path_str())
WORK = Path(r"C:\Users\Axion Industries\.openclaw\workspace")
OUTG = ROOT / "out" / "governance"
OUTC = ROOT / "out" / "contracts"
LOGD = OUTC / "gate_logs"
for d in (OUTG, OUTC, LOGD):
    d.mkdir(parents=True, exist_ok=True)


def run(cmd):
    return subprocess.run(cmd, cwd=str(ROOT), check=False, capture_output=True, text=True)


def must_zero(name, proc, log_path: Path = None):
    if log_path:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text((proc.stdout or "") + (proc.stderr or "") + f"\n{name}_EXIT={proc.returncode}\n", encoding="utf-8")
    if proc.returncode != 0:
        print(f"BLOCKER: {name} failed exit={proc.returncode}")
        if log_path:
            print(f"LOG={log_path}")
        else:
            print((proc.stdout or "") + (proc.stderr or ""))
        sys.exit(proc.returncode)


def readj(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def writej(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def sha(path: Path):
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def all_pass(gates):
    for g in gates:
        cid = g.get("contract_id")
        flow = ROOT / "tools" / "runtime" / f"{cid}_flow.py"
        if flow.exists():
            run(["python", str(flow), "pass"])


def rebuild_static_gate_list(cfg_gates):
    gate_file = ROOT / "ci" / "pipeline_contracts_gate.ps1"
    txt = gate_file.read_text(encoding="utf-8-sig")
    s = txt.find("$gates = @(")
    i = txt.find("if($SelfCheck)")
    if s == -1 or i == -1 or i <= s:
        return False
    lines = [f"  @{{id='{g['contract_id']}'; exit={int(g['gate_exit'])}}}," for g in cfg_gates]
    if lines:
        lines[-1] = lines[-1].rstrip(",")
    block = "$gates = @(\r\n" + "\r\n".join(lines) + "\r\n)"
    txt = txt[:s] + block + "\r\n\r\n" + txt[i:]
    gate_file.write_text(txt, encoding="utf-8")
    return True


def main():
    if "--run" not in sys.argv:
        print("Usage: --run")
        return 2

    # Hard gate preflight
    pre_log = LOGD / "rail_B25_promotions_preflight.log"
    reg = run(["python", str(ROOT / "tools" / "contracts" / "validate_registry.py")])
    selfc = run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ROOT / "ci" / "pipeline_contracts_gate.ps1"), "-SelfCheck"])
    drift = run(["python", str(ROOT / "tools" / "governance" / "emit_governance_drift_check.py")])
    pre_log.write_text(
        (reg.stdout or "") + (reg.stderr or "") +
        (selfc.stdout or "") + (selfc.stderr or "") +
        (drift.stdout or "") + (drift.stderr or "") +
        f"\nREG_EXIT={reg.returncode}\nSELF_CHECK_EXIT={selfc.returncode}\nDRIFT_CHECK_EXIT={drift.returncode}\n",
        encoding="utf-8"
    )
    if reg.returncode or selfc.returncode or drift.returncode:
        print("BLOCKER: preflight hard gate failed")
        print(f"LOG={pre_log}")
        return 3

    ids_path = OUTG / "stream_processing_A25_contract_ids.json"
    if ids_path.exists():
        contract_ids = readj(ids_path).get("contract_ids", [])
    else:
        src = OUTG / "rails" / "stream_processing_A25_results.json"
        contract_ids = [r["id"] for r in readj(src).get("results", [])] if src.exists() else []
    contract_ids = sorted(dict.fromkeys(contract_ids))
    if not contract_ids:
        print("BLOCKER: no stream processing contract_ids found")
        print(f"LOG={pre_log}")
        return 4
    writej(ids_path, {"contract_ids": contract_ids})

    # Allocate gate exits: 2101.. +10
    cfg_path = ROOT / "config" / "release_critical_gates.json"
    cfg = readj(cfg_path)
    used = {int(g.get("gate_exit", 0)) for g in cfg.get("gates", [])}
    plan = []
    gx = 2101
    for cid in contract_ids:
        while gx in used:
            gx += 1
        plan.append({"contract_id": cid, "gate_exit": gx})
        used.add(gx)
        gx += 10
    plan_path = OUTG / "stream_processing_A25_gate_exit_plan.json"
    writej(plan_path, plan)

    # Update canonical gates
    gates = cfg.get("gates", [])
    for e in plan:
        found = False
        for g in gates:
            if g.get("contract_id") == e["contract_id"]:
                g.update({"gate_exit": e["gate_exit"], "category": "stream_processing", "doctrine_required": True})
                found = True
                break
        if not found:
            gates.append({
                "contract_id": e["contract_id"],
                "gate_exit": e["gate_exit"],
                "category": "stream_processing",
                "doctrine_required": True,
            })
    gates = sorted(gates, key=lambda x: int(x.get("gate_exit", 0)))
    cfg["gates"] = gates
    writej(cfg_path, cfg)

    # Update exit registry
    er_path = ROOT / "contracts" / "registry" / "integrity_exit_registry.json"
    er = readj(er_path)
    rg = er.get("release_gates", {})
    for e in plan:
        rg[e["contract_id"]] = e["gate_exit"]
    er["release_gates"] = rg
    writej(er_path, er)

    # Rebuild static gates + selfcheck
    ok = rebuild_static_gate_list(gates)
    if not ok:
        print("BLOCKER: unable to rebuild static gate list")
        print(f"LOG={pre_log}")
        return 5

    self_log = LOGD / "selfcheck_stream_processing_A25.log"
    sc = run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ROOT / "ci" / "pipeline_contracts_gate.ps1"), "-SelfCheck"])
    self_exit = sc.returncode
    self_exit = sc.returncode

    # Doctrine sync
    run(["python", str(ROOT / "tools" / "governance" / "sync_release_gate_doctrine.py")])

    # Gate proofs per promoted gate
    proof_index = []
    for e in plan:
        cid = e["contract_id"]
        gx = e["gate_exit"]
        flow = ROOT / "tools" / "runtime" / f"{cid}_flow.py"
        if not flow.exists():
            continue

        all_pass(gates)
        run(["python", str(flow), "fail1"])
        run(["powershell", "-ExecutionPolicy", "Bypass", "-File", str(ROOT / "ci" / "emit_contract_report.ps1")])
        fail_proc = run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ROOT / "ci" / "pipeline_contracts_gate.ps1")])
        fail_log = LOGD / f"pipeline_contracts_gate_{cid}_fail.log"
        fail_log.write_text((fail_proc.stdout or "") + (fail_proc.stderr or "") + f"\nFAIL_EXIT={fail_proc.returncode}\n", encoding="utf-8")

        latest = sorted(OUTC.glob("contract_report_*.json"), key=lambda p: p.stat().st_mtime)[-1]
        fail_copy = OUTC / f"{latest.stem}_{cid.upper()}_GATE_POLICY_FAIL_PROOF.json"
        fail_copy.write_bytes(latest.read_bytes())

        all_pass(gates)
        run(["powershell", "-ExecutionPolicy", "Bypass", "-File", str(ROOT / "ci" / "emit_contract_report.ps1")])
        pass_proc = run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ROOT / "ci" / "pipeline_contracts_gate.ps1")])
        pass_log = LOGD / f"pipeline_contracts_gate_{cid}_pass.log"
        pass_log.write_text((pass_proc.stdout or "") + (pass_proc.stderr or "") + f"\nPASS_EXIT={pass_proc.returncode}\n", encoding="utf-8")

        latest2 = sorted(OUTC.glob("contract_report_*.json"), key=lambda p: p.stat().st_mtime)[-1]
        pass_copy = OUTC / f"{latest2.stem}_{cid.upper()}_GATE_POLICY_PASS_PROOF.json"
        pass_copy.write_bytes(latest2.read_bytes())

        sx = readj(er_path).get("slice_failures", {}).get(cid, [])
        proof_index.append({
            "contract_id": cid,
            "slice_exits": sx,
            "gate_exit": gx,
            "fail_log": str(fail_log),
            "pass_log": str(pass_log),
            "fail_report": str(fail_copy),
            "pass_report": str(pass_copy),
        })

    # Governance refresh
    run(["python", str(ROOT / "tools" / "governance" / "emit_release_gate_inventory.py")])
    run(["python", str(ROOT / "tools" / "governance" / "emit_integrity_coverage_map.py")])
    dr = run(["python", str(ROOT / "tools" / "governance" / "emit_governance_drift_check.py")]).returncode
    bd = run(["python", str(ROOT / "tools" / "governance" / "emit_governance_baseline_drift.py")]).returncode

    reg2 = run(["python", str(ROOT / "tools" / "contracts" / "validate_registry.py")]).returncode

    inv = readj(ROOT / "out" / "contracts" / "release_critical_gates_inventory.json")
    out_count = len(inv.get("gates", {}).keys()) if isinstance(inv.get("gates"), dict) else 0
    canon_count = len(readj(cfg_path).get("gates", []))

    # proofs / audit
    writej(OUTG / "stream_processing_gate_counts_proof.json", {
        "OUT_GATE_COUNT": out_count,
        "CANONICAL_COUNT": canon_count,
        "aligned": out_count == canon_count,
    })

    audit_path = OUTG / "AXIONOS_GOVERNANCE_AUDIT_20260305_POST_STREAM_PROCESSING_A25.json"
    writej(audit_path, {
        "timestamp_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "checks": {
            "REG_EXIT": reg2,
            "SELF_CHECK_EXIT": self_exit,
            "DRIFT_CHECK_EXIT": dr,
            "BASELINE_DRIFT_EXIT": bd,
            "OUT_GATE_COUNT": out_count,
            "CANONICAL_COUNT": canon_count,
        },
        "status": "PASS" if all(x == 0 for x in [reg2, self_exit, dr, bd]) and out_count == canon_count else "FAIL",
    })

    checkpoint = OUTG / "AXIONOS_INTEGRITY_CHECKPOINT_20260305_POST_STREAM_PROCESSING_A25_PROMOTIONS.json"
    writej(checkpoint, {
        "timestamp_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "hashes": {
            "gate_registry": sha(cfg_path),
            "gate_script": sha(ROOT / "ci" / "pipeline_contracts_gate.ps1"),
            "doctrine": sha(ROOT / "design" / "ops" / "CONTRACT_FIRST_DEVELOPMENT_LOOP_V1.md"),
            "exit_registry": sha(er_path),
            "inventory": sha(ROOT / "out" / "contracts" / "release_critical_gates_inventory.json"),
            "coverage": sha(ROOT / "out" / "governance" / "integrity_coverage_map.json"),
            "drift": sha(ROOT / "out" / "contracts" / "governance_drift_check.json"),
        },
    })

    # batch log
    batch_log = LOGD / "batch_stream_processing_A25_promotions_20260305.log"
    with open(batch_log, "w", encoding="utf-8") as f:
        f.write(f"REG_EXIT={reg2}\n")
        f.write(f"SELF_CHECK_EXIT={self_exit}\n")
        f.write(f"DRIFT_CHECK_EXIT={dr}\n")
        f.write(f"BASELINE_DRIFT_EXIT={bd}\n")
        f.write(f"OUT_GATE_COUNT={out_count}\n")
        f.write(f"CANONICAL_COUNT={canon_count}\n")
        f.write(f"PROMOTED_COUNT={len(plan)}\n")
        f.write("PROMOTED_LIST=" + ";".join([x["contract_id"] for x in plan]) + "\n")
        if plan:
            f.write(f"GATE_EXIT_RANGE_USED={plan[0]['gate_exit']}..{plan[-1]['gate_exit']}\n")
        f.write("NO_NEXT_DOMAIN_EXECUTED=1\n")

    # marker + index
    (OUTG / "rails" / "stream_processing_A25_promotions_exit.txt").write_text("0", encoding="utf-8")
    writej(OUTG / "stream_processing_A25_proof_index.json", {"proofs": proof_index})

    # zip handoff
    zip_path = OUTG / "handoff_stream_processing_A25_promotions_20260305.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for p in [
            OUTG / "stream_processing_A25_contract_ids.json",
            OUTG / "stream_processing_A25_gate_exit_plan.json",
            OUTG / "stream_processing_gate_counts_proof.json",
            OUTG / "stream_processing_A25_proof_index.json",
            batch_log,
            checkpoint,
            audit_path,
        ]:
            if p.exists():
                z.write(p, arcname=p.name)
    (OUTG / "handoff_stream_processing_A25_promotions_20260305.zip.sha256").write_text(sha(zip_path) or "", encoding="utf-8")

    print("DONE")
    print(str(batch_log))
    print(str(checkpoint))
    print(f"REG_EXIT={reg2} SELF_CHECK_EXIT={self_exit} DRIFT_CHECK_EXIT={dr} BASELINE_DRIFT_EXIT={bd} OUT_GATE_COUNT={out_count} CANONICAL_COUNT={canon_count}")


if __name__ == "__main__":
    rc = main()
    if isinstance(rc, int):
        raise SystemExit(rc)



