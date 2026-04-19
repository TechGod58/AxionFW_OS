from pathlib import Path
from subprocess import run


def test_validate_third_party_bundle_compliance_runs():
    root = Path(__file__).resolve().parents[2]
    script = root / "tools" / "packaging" / "validate_third_party_bundle_compliance.py"
    proc = run(
        ["py", "-3", str(script), "--os-root", str(root)],
        cwd=str(root),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + "\n" + proc.stderr
    latest = root / "out" / "packaging" / "third_party_bundle_compliance_latest.json"
    assert latest.exists()
