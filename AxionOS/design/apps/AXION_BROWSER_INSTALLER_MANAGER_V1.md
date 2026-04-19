# AXION Browser Installer Manager Spec v1

Purpose: provide optional first-party installer manager for popular browsers.

## Scope (v1)
Supported optional installers:
- Microsoft Edge
- Google Chrome
- Mozilla Firefox
- Brave
- DuckDuckGo Browser (where desktop package is available/supported)

## Principles
- User choice first (none preinstalled unless selected)
- Official vendor source endpoints only
- Signature/hash verification before install
- Install/update through sandbox test -> promotion flow

## Workflow
1. User selects browser in "Browser Manager"
2. Fetch installer metadata from trusted source catalog
3. Download to staging (`safe://imports/browser_installers/...`)
4. Verify signature/hash
5. Execute installer in capsule test environment
6. Behavior/policy scan
7. If pass, promote/install to OS

## Update handling
- periodic metadata refresh
- notify user of updates
- optional auto-update per-browser policy (off by default)

## Security
- no silent installs
- no unsigned installer execution
- all installs corr-traced

## UI
- install buttons per browser
- source + signature status badge
- installed version + update status
- uninstall/manage links

## v1 done
- user can install any supported browser safely from one screen
- install logs + audit trail available
