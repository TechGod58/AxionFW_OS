# AxionQM Clean

`AxionQM_Clean` is the canonical QM layer for the current Axion stack.

It owns telemetry normalization, health estimation, recovery policy, and the
engine-facing plugin surface used by `AxionE`.

## Responsibilities

- normalize engine telemetry into QM-friendly state
- estimate degradation and risk
- choose `continue`, `checkpoint`, `rollback`, or `halt`
- optionally consume advisory bias from `AxionEM`

## Key Files

- `axionqm_clean/types.py`
- `axionqm_clean/estimator.py`
- `axionqm_clean/policy.py`
- `axionqm_clean/controller.py`
- `axionqm_clean/plugin.py`
- `qm_plugin.py`

## Verification

```powershell
python -m unittest -v
python -m axionqm_clean.release
```
