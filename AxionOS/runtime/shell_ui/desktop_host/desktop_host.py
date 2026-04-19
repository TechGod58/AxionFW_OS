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

CFG = Path(axion_path_str('config', 'SHELL_DESKTOP_DEFAULTS_V1.json'))
FOLDERS_CFG = Path(axion_path_str('config', 'PROFILE_SHELL_FOLDERS_V1.json'))
APPS_HOST_DIR = Path(axion_path_str('runtime', 'shell_ui', 'apps_host'))
if str(APPS_HOST_DIR) not in sys.path:
    sys.path.append(str(APPS_HOST_DIR))

from apps_host import (
    route_browser_install_link,
    get_first_boot_browser_prompt,
    choose_default_browser as choose_apps_default_browser,
    list_browser_choices,
)

STATE = {
    "surface": {
        "displayName": "Desktop",
        "legacyAlias": "Desktop"
    },
    "icons": {
        "profileFolder": False,
        "mainDrive": False,
        "recycleBin": False
    },
    "defaultLinks": [],
    "folderOptions": {},
    "graphics": {}
}


def load_defaults():
    return json.loads(CFG.read_text(encoding='utf-8-sig'))


def _load_profile_folders():
    if not FOLDERS_CFG.exists():
        return {}
    try:
        obj = json.loads(FOLDERS_CFG.read_text(encoding='utf-8-sig'))
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def _workspace_default_links():
    profile = _load_profile_folders()
    workspace = dict(profile.get('workspaceSurface') or {})
    links = workspace.get('defaultLinks') or []
    return [dict(x) for x in links if isinstance(x, dict)]


def _merge_links(primary: list[dict], secondary: list[dict]) -> list[dict]:
    merged: list[dict] = []
    seen: set[str] = set()
    for source in (primary, secondary):
        for item in source:
            link_id = str(item.get('id', '')).strip().lower()
            key = link_id or json.dumps(item, sort_keys=True)
            if key in seen:
                continue
            seen.add(key)
            merged.append(dict(item))
    return merged


def apply_defaults():
    d = load_defaults()
    desktop = d.get("desktop", {})
    profile_links = _workspace_default_links()
    desktop_links = [dict(x) for x in (desktop.get("defaultLinks", []) or []) if isinstance(x, dict)]
    STATE["surface"] = desktop.get("surface", {})
    STATE["icons"] = desktop.get("defaultIcons", {})
    STATE["defaultLinks"] = _merge_links(desktop_links, profile_links)
    STATE["folderOptions"] = desktop.get("folders", {})
    STATE["graphics"] = d.get("graphics", {})
    return {"ok": True, "code": "DESKTOP_DEFAULTS_APPLIED", "state": snapshot()}


def set_folder_option(key: str, value):
    if key not in STATE["folderOptions"]:
        return {"ok": False, "code": "DESKTOP_FOLDER_OPTION_UNKNOWN"}
    STATE["folderOptions"][key] = value
    return {"ok": True, "code": "DESKTOP_FOLDER_OPTION_SET", "key": key, "value": value}


def set_graphics(key: str, value):
    if key not in STATE["graphics"]:
        return {"ok": False, "code": "DESKTOP_GRAPHICS_OPTION_UNKNOWN"}
    STATE["graphics"][key] = value
    return {"ok": True, "code": "DESKTOP_GRAPHICS_OPTION_SET", "key": key, "value": value}


def snapshot():
    return json.loads(json.dumps(STATE))


def open_default_link(link_id: str, corr='corr_desktop_link_open_001'):
    link_key = str(link_id or '').strip().lower()
    selected = None
    for link in STATE.get('defaultLinks', []):
        if str(link.get('id', '')).strip().lower() == link_key:
            selected = dict(link)
            break
    if not selected:
        return {'ok': False, 'code': 'DESKTOP_LINK_NOT_FOUND', 'link_id': link_id}
    link_type = str(selected.get('linkType') or '').strip().lower()
    if link_type == 'web_download':
        routed = route_browser_install_link(
            link_id=str(selected.get('id')),
            target=str(selected.get('target') or ''),
            installer_artifact=str(selected.get('installerArtifact') or ''),
            preferred_family=str(selected.get('preferredFamily') or 'windows'),
            preferred_profile=str(selected.get('preferredProfile') or 'win11'),
            corr=corr,
        )
        return {
            'ok': bool(routed.get('ok')),
            'code': 'DESKTOP_LINK_OPENED' if bool(routed.get('ok')) else str(routed.get('code')),
            'link': selected,
            'dispatch': routed,
        }
    return {'ok': False, 'code': 'DESKTOP_LINK_TYPE_UNSUPPORTED', 'link_id': link_id, 'link_type': link_type}


def get_browser_first_boot_prompt(corr='corr_desktop_browser_prompt_001'):
    return get_first_boot_browser_prompt(corr=corr)


def choose_default_browser(browser_id: str, corr='corr_desktop_browser_choose_001'):
    return choose_apps_default_browser(browser_id=browser_id, corr=corr, complete_first_boot=True)


def list_default_browser_choices(corr='corr_desktop_browser_choices_001'):
    return list_browser_choices(corr=corr)


if __name__ == '__main__':
    print(json.dumps(apply_defaults(), indent=2))

