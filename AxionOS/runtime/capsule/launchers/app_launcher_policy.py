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
import json
import argparse
from pathlib import Path

POLICY_PATH = Path(axion_path_str('config', 'APP_VM_ENFORCEMENT_V1.json'))
DOMAIN_PATH = Path(axion_path_str('config', 'PARALLEL_CUBED_SANDBOX_DOMAINS_V1.json'))


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def load_policy():
    return load_json(POLICY_PATH)


def load_domains():
    return load_json(DOMAIN_PATH)


def resolve_mode(app_id: str):
    policy = load_policy()
    return policy.get("apps", {}).get(app_id, policy.get("defaultMode", "capsule"))


def resolve_domain(app_id: str):
    domains = load_domains()
    for region_id, meta in domains.get("regions", {}).items():
        if app_id in meta.get("apps", []):
            return {
                "parallel_cubed_region": region_id,
                "sandbox_domain": meta.get("sandbox_domain"),
                "rails": meta.get("rail_bindings", []),
                "allowed_modes": meta.get("allowed_modes", []),
            }
    return {
        "parallel_cubed_region": None,
        "sandbox_domain": None,
        "rails": domains.get("defaultRailBindings", []),
        "allowed_modes": [],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--app", required=True)
    args = ap.parse_args()
    mode = resolve_mode(args.app)
    domain = resolve_domain(args.app)
    print(json.dumps({
        "app": args.app,
        "launch_mode": mode,
        "parallel_cubed_region": domain["parallel_cubed_region"],
        "sandbox_domain": domain["sandbox_domain"],
        "rails": domain["rails"],
        "decision": "LAUNCH_POLICY_OK"
    }))


if __name__ == "__main__":
    main()

