import json

REQUIRED = {'corr','artifact_id','component_id','source_vm','safe_uri','sha256','mimeType','sizeBytes','ts'}


def validate_envelope(meta_path):
    data = json.loads(open(meta_path, 'r', encoding='utf-8-sig').read())
    missing = sorted(REQUIRED - set(data.keys()))
    if missing:
        return False, {'missing': missing}
    return True, data
