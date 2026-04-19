# Bus v1 Fixtures

Quick validation pack for `AXIONOS_BUS_CONTRACT_V1.schema.json`.

## Run

From workspace root:

```powershell
python .\fixtures\bus_v1\validate_fixtures.py
```

## Expected

- `pass_*.json` => schema PASS
- `fail_*.json` => schema FAIL

This validates contract envelope and selected payload rules before live integration.
