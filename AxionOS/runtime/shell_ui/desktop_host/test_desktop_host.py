from desktop_host import (
    apply_defaults,
    snapshot,
    open_default_link,
    get_browser_first_boot_prompt,
    choose_default_browser,
    list_default_browser_choices,
)


def test_defaults_icons():
    apply_defaults()
    s = snapshot()
    assert s['surface']['displayName'] == 'Workspace'
    assert s['icons']['profileFolder'] is True
    assert s['icons']['mainDrive'] is True
    assert s['icons']['recycleBin'] is True


def test_workspace_has_chrome_download_link():
    apply_defaults()
    s = snapshot()
    links = {link['id'] for link in s['defaultLinks']}
    assert 'google_chrome_download' in links
    assert 'microsoft_edge_download' in links
    assert 'mozilla_firefox_download' in links


def test_default_link_routes_browser_install():
    apply_defaults()
    out = open_default_link('google_chrome_download', corr='corr_desktop_link_test_001')
    assert out['ok'] is True
    assert out['dispatch']['runtime_result']['code'] == 'LAUNCH_INSTALLER_EXECUTED'


def test_first_boot_browser_choice_flow():
    prompt = get_browser_first_boot_prompt(corr='corr_desktop_browser_prompt_test_001')
    assert prompt['ok'] is True
    choices = list_default_browser_choices(corr='corr_desktop_browser_choices_test_001')
    assert choices['ok'] is True
    assert any(c['browser_id'] == 'brave' for c in choices['choices'])
    selected = choose_default_browser('brave', corr='corr_desktop_browser_choose_test_001')
    assert selected['ok'] is True
    assert selected['default_browser']['app_id'] == 'brave_browser'
