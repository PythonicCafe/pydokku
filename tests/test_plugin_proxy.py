from pydokku import Dokku
from pydokku.models import Proxy
from tests.utils import requires_dokku


def test_object_classes():
    dokku = Dokku()
    assert dokku.proxy.object_classes == (Proxy,)


def test_proxy_type_property():
    app_name = "test-app-1"
    proxy_1 = Proxy(app_name=app_name, enabled=True, app_type=None, global_type="nginx")
    proxy_2 = Proxy(app_name=app_name, enabled=True, app_type="caddy", global_type="nginx")
    assert proxy_1.type == "nginx"  # Global `type`, since app's is None
    assert proxy_2.type == "caddy"  # App's own `type`


def test_parse_list():
    stdout = """
        =====> test-app-7 proxy information
               Proxy computed type:           nginx
               Proxy enabled:                 true
               Proxy global type:             nginx
               Proxy type:
        =====> test-app-8 proxy information
               Proxy computed type:           nginx
               Proxy enabled:                 true
               Proxy global type:             nginx
               Proxy type:                    xxx
        =====> test-app-9 proxy information
               Proxy computed type:           nginx
               Proxy enabled:                 false
               Proxy global type:             nginx
               Proxy type:
    """
    expected = [
        {
            "app_name": "test-app-7",
            "enabled": True,
            "app_type": None,
            "global_type": "nginx",
        },
        {
            "app_name": "test-app-8",
            "enabled": True,
            "app_type": "xxx",
            "global_type": "nginx",
        },
        {
            "app_name": "test-app-9",
            "enabled": False,
            "app_type": None,
            "global_type": "nginx",
        },
    ]
    dokku = Dokku()
    rows_parser = dokku.proxy._get_rows_parser()
    result = rows_parser(stdout)
    assert result == expected


def test_enable_command():
    app_name = "test-app-1"
    dokku = Dokku()
    command = dokku.proxy.enable(app_name=app_name, execute=False)
    assert command.command == ["dokku", "proxy:enable", app_name]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False


def test_disable_command():
    app_name = "test-app-1"
    dokku = Dokku()
    command = dokku.proxy.disable(app_name=app_name, execute=False)
    assert command.command == ["dokku", "proxy:disable", app_name]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False


def test_set_command():
    app_name = "test-app-1"
    new_proxy = "caddy"
    dokku = Dokku()
    command = dokku.proxy.set(app_name=app_name, proxy_type=new_proxy, execute=False)
    assert command.command == ["dokku", "proxy:set", app_name, new_proxy]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False


def test_clear_config_command():
    app_name = "test-app-1"
    dokku = Dokku()
    command = dokku.proxy.clear_config(app_name=app_name, execute=False)
    assert command.command == ["dokku", "proxy:clear-config", app_name]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False

    command = dokku.proxy.clear_config(app_name=None, execute=False)
    assert command.command == ["dokku", "proxy:clear-config", "--all"]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False


def test_build_config_command():
    app_name = "test-app-1"
    dokku = Dokku()
    command = dokku.proxy.build_config(app_name=app_name, execute=False)
    assert command.command == ["dokku", "proxy:build-config", app_name]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False

    command = dokku.proxy.build_config(app_name=None, parallel=4, execute=False)
    assert command.command == ["dokku", "proxy:build-config", "--parallel", "4", "--all"]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False


@requires_dokku
def test_list_set_disable_enable(create_apps):
    def sort_proxy(obj):
        return (obj.app_name, obj.global_type, obj.app_type)

    dokku, apps_names = create_apps

    # Default behavior
    after_app_creation = dokku.proxy.list()
    old_proxy = after_app_creation[0].global_type
    if dokku.version() >= (0, 31, 0):
        expected_default = [
            Proxy(app_name=app_name, enabled=True, app_type=None, global_type=old_proxy) for app_name in apps_names
        ]
    else:
        # Old versions will have the default app type shown
        expected_default = [
            Proxy(app_name=app_name, enabled=True, app_type="nginx", global_type=old_proxy) for app_name in apps_names
        ]
    result = [proxy for proxy in after_app_creation if proxy.app_name in apps_names]
    assert sorted(result, key=sort_proxy) == sorted(expected_default, key=sort_proxy)

    if dokku.version() >= (0, 31, 0):  # Old versions don't allow changing global
        # Changing global will impact new apps
        new_proxy = "caddy" if old_proxy == "nginx" else "nginx"
        dokku.proxy.set(app_name=None, proxy_type=new_proxy)
        for proxy in expected_default:
            proxy.global_type = new_proxy
        new_app_name = "test-app-4"
        dokku.apps.create(new_app_name)
        try:
            after_changing_global = dokku.proxy.list()
            result = [proxy for proxy in after_changing_global if proxy.app_name in apps_names + [new_app_name]]
            expected_proxy = Proxy(app_name=new_app_name, enabled=True, app_type=None, global_type=new_proxy)
            assert sorted(result, key=sort_proxy) == sorted(expected_default + [expected_proxy], key=sort_proxy)

            # Enable/disable
            dokku.proxy.disable(app_name=new_app_name)
            after_disabling_app = dokku.proxy.list()
            result = [proxy for proxy in after_disabling_app if proxy.app_name in apps_names + [new_app_name]]
            new_expected_proxy = Proxy(app_name=new_app_name, enabled=False, app_type=None, global_type=new_proxy)
            assert sorted(result, key=sort_proxy) == sorted(expected_default + [new_expected_proxy], key=sort_proxy)
            dokku.proxy.enable(app_name=new_app_name)
            final = dokku.proxy.list()
            result = [proxy for proxy in final if proxy.app_name in apps_names + [new_app_name]]
            new_expected_proxy = Proxy(app_name=new_app_name, enabled=True, app_type=None, global_type=new_proxy)
            assert sorted(result, key=sort_proxy) == sorted(expected_default + [new_expected_proxy], key=sort_proxy)
        finally:
            dokku.apps.destroy(new_app_name)


# TODO: test object_create (checks if it calls build-config and `skip_system` behavior)
