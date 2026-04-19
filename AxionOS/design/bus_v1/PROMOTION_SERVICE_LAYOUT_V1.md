# Promotion Service Layout v1 (AxionOS)

Goal: minimal implementation layout (not distro-level complexity).

## Proposed tree

```text
<AXIONOS_ROOT>\runtime\promotion\
  promoted.py                # main entry (watch/process-once/replay)
  config.py                  # policy + paths loader
  envelope.py                # envelope schema validation
  hasher.py                  # sha256 verification
  safe_uri.py                # safe:// resolver + policy checks
  scanner.py                 # scanner chain adapter
  ig_gate.py                 # IG verdict adapter (stub-ready)
  mover.py                   # atomic move promote/quarantine
  audit.py                   # ndjson append-only audit writer
  codes.py                   # decision codes / exit codes
  tests\
    test_safe_uri.py
    test_envelope.py
    test_decision_flow.py
```

## Runtime config files

```text
<AXIONOS_ROOT>\config\
  SAFE_URI_POLICY_V1.json
  PROMOTION_POLICY_V1.json
```

## Minimal command workflow

1) Drop payload + `.meta.json` into inbox.
2) Run `axion-promoted process-once`.
3) Artifact is promoted or quarantined.
4) Decision appended to `promotion.ndjson`.

## First implementation target

- Implement only `process-once` first.
- Keep scanner and IG as simple adapters (can start stubbed).
- Enforce safe:// mapping hard from day one.

## Acceptance criteria (v1)

- Valid payload to allowed safe:// zone => promoted.
- Traversal/zone violation => quarantined with correct code.
- Hash mismatch => quarantined.
- Every run emits audit record with correlation id.

