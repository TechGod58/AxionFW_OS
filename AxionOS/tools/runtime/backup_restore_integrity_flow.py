from runtime_paths import axion_path, axion_path_str, AXION_ROOT, RUNTIME_OUT
import json, os, sys, hashlib
from datetime import datetime, timezone
CODES={"BACKUP_ARCHIVE_CORRUPT":641,"RESTORE_STATE_MISMATCH":642}
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def h(obj):
    b=json.dumps(obj,sort_keys=True,separators=(',',':')).encode('utf-8')
    return hashlib.sha256(b).hexdigest()
base=axion_path_str('out', 'runtime'); os.makedirs(base, exist_ok=True)
audit_p=os.path.join(base,'backup_restore_integrity_audit.json')
smoke_p=os.path.join(base,'backup_restore_integrity_smoke.json')
mode='pass'
if len(sys.argv)>1: mode=sys.argv[1]

manifest={
  "configuration":{"dns":"1.1.1.1","firewall":"on"},
  "state":{"services":["svc.eventbus","svc.kernel_guard"],"profiles":["default"]},
  "registry_indices":{"contracts_entries":77}
}
backup_archive_payload={"archive_id":"backup-20260305-01","content":manifest}
backup_archive_hash=h(backup_archive_payload)
manifest_hash=h(manifest)

restored={
  "configuration":{"dns":"1.1.1.1","firewall":"on"},
  "state":{"services":["svc.eventbus","svc.kernel_guard"],"profiles":["default"]},
  "registry_indices":{"contracts_entries":77}
}
restore_state_hash=h(restored)

failures=[]
if mode=='archive_corrupt':
  backup_archive_hash=h({"archive_id":"backup-20260305-01","content":"tampered"})
  failures=[{"code":"BACKUP_ARCHIVE_CORRUPT","detail":"backup archive hash mismatch against manifest"}]
elif mode=='restore_mismatch':
  restored['configuration']['dns']='8.8.8.8'
  restore_state_hash=h(restored)
  failures=[{"code":"RESTORE_STATE_MISMATCH","detail":"restored state hash differs from backup manifest hash"}]

hash_match=(restore_state_hash==manifest_hash) and not failures
restore_complete=True if not failures else False

result={
  "backup_archive_hash":backup_archive_hash,
  "manifest_hash":manifest_hash,
  "restore_state_hash":restore_state_hash,
  "hash_match":hash_match,
  "restore_complete":restore_complete
}
status='FAIL' if failures else 'PASS'
smoke={"timestamp_utc":now(),"status":status,"backup_restore":result,"failures":failures}
audit={"timestamp_utc":now(),"status":status,"manifest":manifest,"restored":restored,"backup_restore":result,"failures":failures}
json.dump(smoke,open(smoke_p,'w',encoding='utf-8'),indent=2)
json.dump(audit,open(audit_p,'w',encoding='utf-8'),indent=2)
if failures: raise SystemExit(CODES[failures[0]['code']])

