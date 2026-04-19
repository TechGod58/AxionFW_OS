# Shell Orchestrator

Bridges shell module events into coordinated state updates.

Current sync paths:
- settings.changed -> taskbar/tray/desktop live updates
- startmenu.opened -> taskbar launcher running state
- notifications.push -> orchestrator sync event

Run demo:

```powershell
python "$env:AXIONOS_ROOT\runtime\shell_ui\orchestrator\shell_orchestrator.py"
```
