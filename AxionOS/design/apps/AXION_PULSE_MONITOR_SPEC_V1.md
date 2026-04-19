# AXION Pulse Monitor (Task Manager) Spec v1

## Product
- Name: **Pulse Monitor**
- ID: `axion-pulse-monitor`

## Goal
Windows-familiar task/resource manager with Axion capsule awareness.

## Tabs (v1)
1. Processes
2. Performance
3. Startup
4. Services
5. Users/Sessions
6. Details (advanced)

## Core features
- End task / end process tree
- Capsule-aware kill (terminate app VM and overlays safely)
- CPU/RAM/Disk/Network/GPU charts
- Per-process impact scoring
- Startup impact and enable/disable controls
- Service start/stop/restart

## Axion-specific additions
- corr id column
- launch mode column (host/capsule)
- policy badge (allowed/queued/denied)
- quick link to trace timeline

## v1 done
- all core tabs functional
- process controls stable
- capsule process handling integrated
