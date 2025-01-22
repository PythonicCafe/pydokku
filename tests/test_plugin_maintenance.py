from pydokku.dokku_cli import Dokku
from pydokku.models import Command, Maintenance
from tests.utils import requires_dokku


def test_object_classes():
    dokku = Dokku()
    assert dokku.maintenance.object_classes == (Maintenance,)


def test_parse_list():
    stdout = """
        =====> test-app-1 maintenance information
            Maintenance enabled:           false
        =====> test-app-2 maintenance information
            Maintenance enabled:           true
        =====> test-app-3 maintenance information
            Maintenance enabled:           false
        =====> test-app-4 maintenance information
            Maintenance enabled:           false
    """
    expected = [
        {
            "app_name": "test-app-1",
            "enabled": False,
        },
        {
            "app_name": "test-app-2",
            "enabled": True,
        },
        {
            "app_name": "test-app-3",
            "enabled": False,
        },
        {
            "app_name": "test-app-4",
            "enabled": False,
        },
    ]
    dokku = Dokku()
    rows_parser = dokku.maintenance._get_rows_parser()
    result = rows_parser(stdout)
    assert result == expected


def test_enable_command():
    dokku = Dokku()
    app_name = "test-app-maintenance"
    command = dokku.maintenance.enable(app_name=app_name, execute=False)
    assert command.command == ["dokku", "maintenance:enable", app_name]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False


def test_disable_command():
    dokku = Dokku()
    app_name = "test-app-maintenance"
    command = dokku.maintenance.disable(app_name=app_name, execute=False)
    assert command.command == ["dokku", "maintenance:disable", app_name]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False


@requires_dokku
def test_enable_disable_list_set_unset(create_apps):
    dokku, apps_names = create_apps
    plugin_name = "maintenance"
    # TODO: create util function `ensure_plugin`
    dokku._execute(Command(["dokku", "plugin:install", f"file:///var/lib/dokku/tmp/dokku-copy-{plugin_name}/.git", "--name", plugin_name], sudo=True, check=False))

    before = {obj.app_name: obj for obj in dokku.maintenance.list() if obj.app_name in apps_names}
    assert len(before) == len(apps_names)
    assert [obj.enabled for obj in before.values()] == [False for _ in apps_names]

    dokku.maintenance.enable(apps_names[0])
    after = {obj.app_name: obj for obj in dokku.maintenance.list() if obj.app_name in apps_names}
    assert after[apps_names[0]].enabled
