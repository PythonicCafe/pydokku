from textwrap import dedent

from pydokku import Dokku
from pydokku.models import Port
from tests.utils import requires_dokku


def test_object_classes():
    dokku = Dokku()
    dokku._dokku_version = (0, 35, 15)
    assert dokku.ports.object_classes == (Port,)


def test_clear_command():
    app_name = "test-app-1"
    dokku = Dokku()
    dokku._dokku_version = (0, 35, 15)
    command = dokku.ports.clear(app_name=app_name, execute=False)
    assert command.command == ["dokku", "ports:clear", app_name]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False


def test_clear_command_old():
    app_name = "test-app-1"
    dokku = Dokku()
    dokku._dokku_version = (0, 30, 10)
    command = dokku.ports.clear(app_name=app_name, execute=False)
    assert command.command == ["dokku", "proxy:ports-clear", app_name]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False


def test_add_command():
    app_name_1 = "test-app-1"
    app_name_2 = "test-app-2"
    dokku = Dokku()
    dokku._dokku_version = (0, 35, 15)
    ports = [
        Port(app_name=app_name_1, scheme="http", host_port=80, container_port=5000),
        Port(app_name=app_name_1, scheme="https", host_port=443, container_port=None),
        Port(app_name=app_name_2, scheme="http", host_port=80, container_port=5000),
        Port(app_name=app_name_2, scheme="https", host_port=443, container_port=5000),
        Port(app_name=app_name_2, scheme="https", host_port=5001, container_port=5001),
    ]
    commands = dokku.ports.add(ports=ports, execute=False)
    assert len(commands) == 2  # 2 apps
    assert commands[0].command == ["dokku", "ports:add", app_name_1, "http:80:5000", "https:443"]
    assert commands[0].stdin is None
    assert commands[0].check is True
    assert commands[0].sudo is False
    assert commands[1].command == [
        "dokku",
        "ports:add",
        app_name_2,
        "http:80:5000",
        "https:443:5000",
        "https:5001:5001",
    ]
    assert commands[1].stdin is None
    assert commands[1].check is True
    assert commands[1].sudo is False


def test_add_command_old():
    app_name_1 = "test-app-1"
    app_name_2 = "test-app-2"
    dokku = Dokku()
    dokku._dokku_version = (0, 30, 10)
    ports = [
        Port(app_name=app_name_1, scheme="http", host_port=80, container_port=5000),
        Port(app_name=app_name_1, scheme="https", host_port=443, container_port=None),
        Port(app_name=app_name_2, scheme="http", host_port=80, container_port=5000),
        Port(app_name=app_name_2, scheme="https", host_port=443, container_port=5000),
        Port(app_name=app_name_2, scheme="https", host_port=5001, container_port=5001),
    ]
    commands = dokku.ports.add(ports=ports, execute=False)
    assert len(commands) == 2  # 2 apps
    assert commands[0].command == ["dokku", "proxy:ports-add", app_name_1, "http:80:5000", "https:443"]
    assert commands[0].stdin is None
    assert commands[0].check is True
    assert commands[0].sudo is False
    assert commands[1].command == [
        "dokku",
        "proxy:ports-add",
        app_name_2,
        "http:80:5000",
        "https:443:5000",
        "https:5001:5001",
    ]
    assert commands[1].stdin is None
    assert commands[1].check is True
    assert commands[1].sudo is False


def test_set_command():
    app_name_1 = "test-app-1"
    app_name_2 = "test-app-2"
    dokku = Dokku()
    dokku._dokku_version = (0, 35, 15)
    ports = [
        Port(app_name=app_name_1, scheme="http", host_port=80, container_port=5000),
        Port(app_name=app_name_1, scheme="https", host_port=443, container_port=None),
        Port(app_name=app_name_2, scheme="http", host_port=80, container_port=5000),
        Port(app_name=app_name_2, scheme="https", host_port=443, container_port=5000),
        Port(app_name=app_name_2, scheme="https", host_port=5001, container_port=5001),
    ]
    commands = dokku.ports.set(ports=ports, execute=False)
    assert len(commands) == 2  # 2 apps
    assert commands[0].command == ["dokku", "ports:set", app_name_1, "http:80:5000", "https:443"]
    assert commands[0].stdin is None
    assert commands[0].check is True
    assert commands[0].sudo is False
    assert commands[1].command == [
        "dokku",
        "ports:set",
        app_name_2,
        "http:80:5000",
        "https:443:5000",
        "https:5001:5001",
    ]
    assert commands[1].stdin is None
    assert commands[1].check is True
    assert commands[1].sudo is False


def test_set_command_old():
    app_name_1 = "test-app-1"
    app_name_2 = "test-app-2"
    dokku = Dokku()
    dokku._dokku_version = (0, 30, 10)
    ports = [
        Port(app_name=app_name_1, scheme="http", host_port=80, container_port=5000),
        Port(app_name=app_name_1, scheme="https", host_port=443, container_port=None),
        Port(app_name=app_name_2, scheme="http", host_port=80, container_port=5000),
        Port(app_name=app_name_2, scheme="https", host_port=443, container_port=5000),
        Port(app_name=app_name_2, scheme="https", host_port=5001, container_port=5001),
    ]
    commands = dokku.ports.set(ports=ports, execute=False)
    assert len(commands) == 2  # 2 apps
    assert commands[0].command == ["dokku", "proxy:ports-set", app_name_1, "http:80:5000", "https:443"]
    assert commands[0].stdin is None
    assert commands[0].check is True
    assert commands[0].sudo is False
    assert commands[1].command == [
        "dokku",
        "proxy:ports-set",
        app_name_2,
        "http:80:5000",
        "https:443:5000",
        "https:5001:5001",
    ]
    assert commands[1].stdin is None
    assert commands[1].check is True
    assert commands[1].sudo is False


def test_remove_command():
    app_name_1 = "test-app-1"
    app_name_2 = "test-app-2"
    dokku = Dokku()
    dokku._dokku_version = (0, 35, 15)
    ports = [
        Port(app_name=app_name_1, scheme="http", host_port=80, container_port=5000),
        Port(app_name=app_name_1, scheme="https", host_port=443, container_port=None),
        Port(app_name=app_name_2, scheme="http", host_port=80, container_port=5000),
        Port(app_name=app_name_2, scheme="https", host_port=443, container_port=5000),
        Port(app_name=app_name_2, scheme="https", host_port=5001, container_port=5001),
    ]
    commands = dokku.ports.remove(ports=ports, execute=False)
    assert len(commands) == 2  # 2 apps
    assert commands[0].command == ["dokku", "ports:remove", app_name_1, "http:80:5000", "https:443"]
    assert commands[0].stdin is None
    assert commands[0].check is True
    assert commands[0].sudo is False
    assert commands[1].command == [
        "dokku",
        "ports:remove",
        app_name_2,
        "http:80:5000",
        "https:443:5000",
        "https:5001:5001",
    ]
    assert commands[1].stdin is None
    assert commands[1].check is True
    assert commands[1].sudo is False


def test_remove_command_old():
    app_name_1 = "test-app-1"
    app_name_2 = "test-app-2"
    dokku = Dokku()
    dokku._dokku_version = (0, 30, 10)
    ports = [
        Port(app_name=app_name_1, scheme="http", host_port=80, container_port=5000),
        Port(app_name=app_name_1, scheme="https", host_port=443, container_port=None),
        Port(app_name=app_name_2, scheme="http", host_port=80, container_port=5000),
        Port(app_name=app_name_2, scheme="https", host_port=443, container_port=5000),
        Port(app_name=app_name_2, scheme="https", host_port=5001, container_port=5001),
    ]
    commands = dokku.ports.remove(ports=ports, execute=False)
    assert len(commands) == 2  # 2 apps
    assert commands[0].command == ["dokku", "proxy:ports-remove", app_name_1, "http:80:5000", "https:443"]
    assert commands[0].stdin is None
    assert commands[0].check is True
    assert commands[0].sudo is False
    assert commands[1].command == [
        "dokku",
        "proxy:ports-remove",
        app_name_2,
        "http:80:5000",
        "https:443:5000",
        "https:5001:5001",
    ]
    assert commands[1].stdin is None
    assert commands[1].check is True
    assert commands[1].sudo is False


def test_parse_list():
    stdout = dedent(
        """
        =====> test-app-1 ports information
            Ports map:                     http:80:5001 https:443:5001
            Ports map detected:            http:80:5000
        =====> test-app-2 ports information
            Ports map:
            Ports map detected:            http:80:5000
        =====> test-app-3 ports information
            Ports map:
            Ports map detected:            http:80:5000
    """
    ).strip()
    dokku = Dokku()
    dokku._dokku_version = (0, 35, 15)
    rows_parser = dokku.ports._get_rows_parser()
    result = rows_parser(stdout)
    expected = [
        {
            "app_name": "test-app-1",
            "app_map": ["http:80:5001", "https:443:5001"],
            "global_map": ["http:80:5000"],
        },
        {
            "app_name": "test-app-2",
            "app_map": [],
            "global_map": ["http:80:5000"],
        },
        {
            "app_name": "test-app-3",
            "app_map": [],
            "global_map": ["http:80:5000"],
        },
    ]
    assert result == expected


def test_parse_list_old():
    stdout = dedent(
        """
        -----> Port mappings for test-app-7
            -----> scheme  host port  container port
            http           80         5000
            https          443        5000
    """
    ).strip()
    dokku = Dokku()
    dokku._dokku_version = (0, 30, 10)
    result = dokku.ports._parse_old_row(stdout)
    expected = {
        "app_name": "test-app-7",
        "app_map": ["http:80:5000", "https:443:5000"],
        "global_map": None,
    }
    assert result == expected


def test_convert_rows():
    input_data = [
        {
            "app_name": "test-app-1",
            "app_map": ["http:80:5001", "https:443:5001"],
            "global_map": ["http:80:5000", "https:443:5000"],
        },
        {
            "app_name": "test-app-2",
            "app_map": [],
            "global_map": ["http:80:5000"],
        },
        {
            "app_name": "test-app-3",
            "app_map": [],
            "global_map": ["http:80:5000"],
        },
    ]
    expected = [
        Port(
            app_name=None,
            scheme="http",
            host_port=80,
            container_port=5000,
        ),
        Port(
            app_name=None,
            scheme="https",
            host_port=443,
            container_port=5000,
        ),
        Port(
            app_name="test-app-1",
            scheme="http",
            host_port=80,
            container_port=5001,
        ),
        Port(
            app_name="test-app-1",
            scheme="https",
            host_port=443,
            container_port=5001,
        ),
    ]
    dokku = Dokku()
    dokku._dokku_version = (0, 35, 15)
    result = dokku.ports._convert_rows(input_data)
    assert result == expected


@requires_dokku
def test_list_add_remove_set_clear(create_apps):
    def sort_ports(obj):
        return (obj.app_name or "", obj.scheme, obj.host_port)

    dokku, apps_names = create_apps

    # Default behavior
    after_app_creation = [obj for obj in dokku.ports.list() if obj.app_name in [None] + apps_names]
    if dokku.version() >= (0, 31, 0):
        expected_global = Port(app_name=None, scheme="http", host_port=80, container_port=5000)
        assert [expected_global] == after_app_creation
    else:  # "Global" port object doesn't exist prior to 0.31.0
        assert [] == after_app_creation

    # add/set/remove/clear
    new_ports = [
        Port(
            app_name="test-app-1",
            scheme="http",
            host_port=80,
            container_port=3000,
        ),
        Port(
            app_name="test-app-1",
            scheme="https",
            host_port=443,
            container_port=3000,
        ),
        Port(
            app_name="test-app-3",
            scheme="http",
            host_port=8080,
            container_port=3000,
        ),
        Port(
            app_name="test-app-3",
            scheme="https",
            host_port=8081,
            container_port=3000,
        ),
    ]
    dokku.ports.add(new_ports, execute=True)
    only_first_app = [obj for obj in dokku.ports.list(app_name="test-app-1") if obj.app_name in [None] + apps_names]
    assert only_first_app == new_ports[:2]
    after_new_ports = [obj for obj in dokku.ports.list() if obj.app_name in [None] + apps_names]
    assert sorted(after_app_creation + new_ports, key=sort_ports) == sorted(after_new_ports, key=sort_ports)
    dokku.ports.remove(ports=[new_ports[-1]], execute=True)
    after_remove = [obj for obj in dokku.ports.list() if obj.app_name in [None] + apps_names]
    assert sorted(after_app_creation + new_ports[:-1], key=sort_ports) == sorted(after_remove, key=sort_ports)
    dokku.ports.set(ports=[new_ports[0]], execute=True)
    after_set = [obj for obj in dokku.ports.list() if obj.app_name in [None] + apps_names]
    assert sorted(after_app_creation + [new_ports[0], new_ports[2]], key=sort_ports) == sorted(
        after_set, key=sort_ports
    )
    dokku.ports.clear(app_name="test-app-1", execute=True)
    after_clear = [obj for obj in dokku.ports.list() if obj.app_name in [None] + apps_names]
    if dokku.version() >= (0, 31, 0):
        assert sorted(after_app_creation + [new_ports[2]], key=sort_ports) == sorted(after_clear, key=sort_ports)
    else:  # proxy:ports-clear will add `http:80:5000` to app
        default_port = Port(
            app_name="test-app-1",
            scheme="http",
            host_port=80,
            container_port=5000,
        )
        assert sorted(after_app_creation + [new_ports[2], default_port], key=sort_ports) == sorted(after_clear, key=sort_ports)


# TODO: test object_create
