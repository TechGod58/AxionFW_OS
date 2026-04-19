import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
POLICY = json.loads((ROOT / "SAFE_URI_POLICY_V1.json").read_text(encoding="utf-8"))
FIX_DIR = Path(__file__).resolve().parent

TRAVERSAL_PAT = re.compile(r"(^|[\\/])\.\.([\\/]|$)")
DRIVE_PAT = re.compile(r"^[a-zA-Z]:")
UNC_PAT = re.compile(r"^\\\\")


def decide(uri: str):
    if not uri.startswith("safe://"):
        return "MAP_FAIL_SCHEME"

    rest = uri[len("safe://"):]
    if not rest or "/" not in rest:
        return "MAP_FAIL_PATH_EMPTY"

    zone, rel = rest.split("/", 1)
    if zone in POLICY.get("disallowedZones", []):
        return "MAP_FAIL_ZONE"

    zones = POLICY.get("zones", {})
    z = zones.get(zone)
    if not z or not z.get("enabled", False):
        return "MAP_FAIL_ZONE"

    if not rel:
        return "MAP_FAIL_PATH_EMPTY"

    if TRAVERSAL_PAT.search(rel):
        return "MAP_FAIL_TRAVERSAL"
    if DRIVE_PAT.search(rel):
        return "MAP_FAIL_TRAVERSAL"
    if UNC_PAT.search(rel):
        return "MAP_FAIL_TRAVERSAL"
    if rel.startswith("/") or rel.startswith("\\"):
        return "MAP_FAIL_TRAVERSAL"

    return "MAP_OK"


def main():
    expected_files = sorted(FIX_DIR.glob("*.json"))
    ok_all = True
    for p in expected_files:
        data = json.loads(p.read_text(encoding="utf-8"))
        got = decide(data["uri"])
        exp = data["expected"]
        status = "OK" if got == exp else "MISMATCH"
        print(f"{p.name}: got={got} expected={exp} => {status}")
        if got != exp:
            ok_all = False

    raise SystemExit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
