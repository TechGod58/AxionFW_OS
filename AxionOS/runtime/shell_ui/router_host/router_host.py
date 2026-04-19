import sys
from pathlib import Path

_TOOLS_DIR = None
for _parent in Path(__file__).resolve().parents:
    if (_parent / "tools" / "common" / "pathing.py").exists():
        _TOOLS_DIR = _parent / "tools"
        break
if _TOOLS_DIR and str(_TOOLS_DIR) not in sys.path:
    sys.path.append(str(_TOOLS_DIR))

from common.pathing import axion_path


def axion_path_str(*parts):
    return str(axion_path(*parts))
import json
import sys
from pathlib import Path

BUS = Path(axion_path_str('runtime', 'shell_ui', 'event_bus'))
if str(BUS) not in sys.path:
    sys.path.append(str(BUS))

from event_bus import publish

ROUTES = {
    '/home': 'home_host',
    '/system': 'system_host',
    '/bluetooth-devices': 'devices_host',
    '/network-internet': 'network_host',
    '/personalization': 'personalization_host',
    '/apps': 'apps_host',
    '/accounts': 'accounts_host',
    '/time-language': 'language_host',
    '/accessibility': 'accessibility_host',
    '/privacy-security': 'privacy_security_host',
    '/updates': 'updates_host',
    '/control-panel': 'control_panel_host',
    '/windows-tools': 'windows_tools_host',
    '/services': 'services_host',
    '/users-tools': 'user_tools_host',
    '/properties': 'properties_host',
    '/computer-management': 'computer_management_host',
    '/advanced': 'advanced_system_host',
    '/preboot-auth': 'preboot_auth_host',
    '/repair': 'repair_portal_host',
    '/hardware-diagnostics': 'hardware_diagnostics_host',
    '/account-creation': 'account_creation_host'
}


def resolve(route: str, corr: str = 'corr_route_001'):
    host = ROUTES.get(route)
    if not host:
        out = {'ok': False, 'code': 'ROUTE_NOT_FOUND', 'route': route}
        publish('shell.router.route.failed', out, corr=corr, source='router_host')
        return out
    out = {'ok': True, 'code': 'ROUTE_OK', 'route': route, 'host': host}
    publish('shell.router.route.changed', out, corr=corr, source='router_host')
    return out


def list_routes():
    return [{'route': r, 'host': h} for r, h in sorted(ROUTES.items())]


if __name__ == '__main__':
    print(json.dumps({'routes': list_routes()}, indent=2))

