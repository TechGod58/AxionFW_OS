# Device Adaptation Fabric Runtime Scaffold

Modules:
- device_watcher.py
- driver_resolver.py
- driver_sandbox_runner.py
- driver_promoter.py
- shadow_profile_store.py
- rebind_service.py
- daf_cli.py
- smart_driver_fabric.py

Audit:
- $env:AXIONOS_ROOT\data\audit\device_fabric.ndjson

Example:

```powershell
python "$env:AXIONOS_ROOT\runtime\device_fabric\daf_cli.py" detect --bus usb --vendor 1234 --product 5678 --class storage
```

Smart Driver Fabric bootstrap:

```powershell
@'
from smart_driver_fabric import ensure_fabric_initialized
print(ensure_fabric_initialized(corr="corr_sdf_readme_001"))
'@ | py -3 -
```
