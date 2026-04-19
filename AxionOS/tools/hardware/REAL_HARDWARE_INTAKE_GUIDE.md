# Real Hardware Intake Guide

## What you need to do

Run the inventory collector on one HP 9470m and one HP 9480m while they are booted into Windows.

## Commands

Set your repo root once for the session:

```powershell
$env:AXIONOS_ROOT = "<path-to-AxionOS>"
```

9470m:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "$env:AXIONOS_ROOT\tools\hardware\collect_windows_hardware_inventory.ps1" -OutputPath "$env:AXIONOS_ROOT\out\hardware_inventory\targets\hp_9470m_inventory.json"
```

9480m:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "$env:AXIONOS_ROOT\tools\hardware\collect_windows_hardware_inventory.ps1" -OutputPath "$env:AXIONOS_ROOT\out\hardware_inventory\targets\hp_9480m_inventory.json"
```

If `AXIONOS_ROOT` is not set, the scripts still try to discover your workspace automatically.

## What to bring back

Make sure these two files exist:

- `$env:AXIONOS_ROOT\out\hardware_inventory\targets\hp_9470m_inventory.json`
- `$env:AXIONOS_ROOT\out\hardware_inventory\targets\hp_9480m_inventory.json`

## Then generate the first matrix

```powershell
python "$env:AXIONOS_ROOT\tools\hardware\generate_first_laptop_bringup_matrix.py" "$env:AXIONOS_ROOT\out\hardware_inventory\targets\hp_9470m_inventory.json" "$env:AXIONOS_ROOT\out\hardware_inventory\targets\hp_9480m_inventory.json" --json-out "$env:AXIONOS_ROOT\out\hardware_inventory\first_laptop_family_bringup_matrix.json" --md-out "$env:AXIONOS_ROOT\out\hardware_inventory\first_laptop_family_bringup_matrix.md"
```

That will give us the first real storage/input/display/network target list for the HP bring-up slice.
