from event_bus import subscribe, publish, snapshot_subscribers
from state_bridge import save_state


def wire_default_subscriptions():
    subscribe('shell.startmenu.opened', 'taskbar_host')
    subscribe('shell.settings.changed', 'tray_host')
    subscribe('shell.notifications.push', 'tray_host')
    subscribe('shell.taskbar.pin', 'start_menu_host')


def demo_flow(corr='corr_shell_bus_001'):
    wire_default_subscriptions()
    publish('shell.startmenu.opened', {'user': 'default'}, corr=corr, source='start_menu_host')
    publish('shell.settings.changed', {'key': 'taskbar_alignment', 'value': 'center'}, corr=corr, source='settings_host')
    publish('shell.notifications.push', {'title': 'Axion', 'body': 'Bridge online'}, corr=corr, source='event_bus_demo')
    save_state('event_bus', {'subscribers': snapshot_subscribers()}, corr=corr)


if __name__ == '__main__':
    demo_flow()
    print('SHELL_EVENT_BUS_DEMO_OK')
