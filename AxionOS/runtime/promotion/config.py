from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / 'config' / 'SAFE_URI_POLICY_V1.json'


def load_policy(path: Path = POLICY_PATH):
    return json.loads(path.read_text(encoding='utf-8'))
