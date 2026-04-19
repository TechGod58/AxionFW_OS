# Next Execution Queue (AxionOS bus_v1)

1. Scaffold `<AXIONOS_ROOT>\runtime\promotion\` module files.
2. Implement `safe_uri.py` policy resolver using `SAFE_URI_POLICY_V1.json`.
3. Implement `envelope.py` validator for promotion metadata.
4. Implement `promoted.py process-once` happy path + quarantine path.
5. Add 3 smoke tests:
   - pass allowed projects target
   - fail traversal target
   - fail hash mismatch
6. Run local smoke + capture first `promotion.ndjson` sample.

