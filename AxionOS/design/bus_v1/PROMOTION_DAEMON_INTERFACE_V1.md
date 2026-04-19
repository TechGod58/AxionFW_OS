# Promotion Daemon Interface v1

Purpose: deterministic save-down gate from sandbox staging to approved OS storage.

## 1) Process

- Name: `axion-promoted`
- Mode: local-only daemon/service
- Input: staged artifacts + metadata envelope
- Output: promote/quarantine decision + audit record

## 2) Directory Contract

- `<AXIONOS_ROOT>\data\staging\inbox` (untrusted inputs)
- `<AXIONOS_ROOT>\data\staging\processing` (in-flight)
- `<AXIONOS_ROOT>\data\staging\quarantine` (rejected)
- `<AXIONOS_ROOT>\data\audit\promotion.ndjson` (append-only audit)
- approved targets resolved via `safe://` mapping policy

## 3) Metadata Envelope (required)

```json
{
  "corr": "corr_<uuid>",
  "artifact_id": "art_<uuid>",
  "component_id": "comp_<uuid>",
  "source_vm": "vm_<uuid>",
  "safe_uri": "safe://projects/axionos/out/report.json",
  "sha256": "<hex>",
  "mimeType": "application/json",
  "sizeBytes": 1234,
  "ts": "2026-03-01T15:00:00Z"
}
```

## 4) CLI (v1)

```text
axion-promoted process-once
axion-promoted watch
axion-promoted verify --artifact <path> --meta <path>
axion-promoted replay --corr <id>
```

### Exit codes
- `0` success
- `10` schema error
- `11` hash mismatch
- `12` safe-uri policy fail
- `13` scanner fail
- `14` IG policy fail
- `20` internal error

## 5) Decision Model

Pipeline order:
1. envelope schema check
2. hash verification
3. safe:// mapping + zone/type/size policy
4. security scanner chain
5. IG verdict (optional in v1, required in v2)
6. promote or quarantine

Decision codes:
- `PROMOTE_OK`
- `REJECT_SCHEMA`
- `REJECT_HASH`
- `REJECT_POLICY`
- `REJECT_SCAN`
- `REJECT_IG`

## 6) Audit Record Format

```json
{
  "corr": "corr_123",
  "artifact_id": "art_123",
  "safe_uri": "safe://projects/axionos/out/report.json",
  "resolved_path": "C:\\AxionOS\\data\\projects\\axionos\\out\\report.json",
  "decision": "PROMOTE_OK",
  "stage_ms": {"schema":2,"hash":1,"policy":1,"scan":14,"ig":2},
  "ts": "2026-03-01T15:00:01Z"
}
```

## 7) Non-Goals

- network upload/download
- direct email/text export
- direct write to system zones

