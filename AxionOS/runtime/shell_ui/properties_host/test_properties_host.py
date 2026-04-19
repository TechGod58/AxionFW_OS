from properties_host import describe_target


def test_profile_folder_properties():
    out = describe_target('profile_folder', 'Videos')
    assert out['ok']
    assert out['properties']['sandbox_kind'] == 'persistent_profile_sandbox'


def test_control_panel_properties():
    out = describe_target('control_panel_item', 'Registry Editor')
    assert out['ok']
    assert out['properties']['supports_properties']


def test_profile_folder_properties_legacy_alias():
    out = describe_target('profile_folder', 'Connectios')
    assert out['ok']
    assert out['properties']['display_name'] == 'Connections'
