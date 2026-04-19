from user_tools_host import snapshot, open_tool


def test_user_tools_items():
    snap = snapshot('corr_ut_test_001')
    assert snap['title'] == "User's Tools"
    assert 'computer_management' in [item['tool_id'] for item in snap['items']]
    out = open_tool('disk_cleanup')
    assert out['ok']


def test_user_tools_management_items():
    out = open_tool('advanced_system')
    assert out['ok']
    assert out['target'] == 'advanced_system'
