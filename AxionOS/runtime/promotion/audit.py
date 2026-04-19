import json
from pathlib import Path
from datetime import datetime, timezone


def append_audit(record, audit_path):
    p = Path(audit_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    if 'ts' not in record:
        record['ts'] = datetime.now(timezone.utc).isoformat()
    with p.open('a', encoding='utf-8') as f:
        f.write(json.dumps(record) + '\n')
