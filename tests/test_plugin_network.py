import datetime
import random

from pydokku.dokku_cli import Dokku
from pydokku.models import AppNetwork, Network
from pydokku.utils import execute_command
from tests.utils import random_alphanum, requires_dokku


def test_object_classes():
    dokku = Dokku()
    assert dokku.network.object_classes == (Network, AppNetwork)


def test_create_command():
    dokku = Dokku()
    network_name = "test-network"
    command = dokku.network.create(name=network_name, execute=False)
    assert command.command == ["dokku", "network:create", network_name]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False


def test_destroy_command():
    dokku = Dokku()
    network_name = "test-network"
    command = dokku.network.destroy(name=network_name, execute=False)
    assert command.command == ["dokku", "network:destroy", network_name]
    assert command.stdin == network_name
    assert command.check is True
    assert command.sudo is False
    command = dokku.network.destroy(name=network_name, force=True, execute=False)
    assert command.command == ["dokku", "network:destroy", "--force", network_name]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False


def test_list_parser():
    json_data = """
        [
          {
            "CreatedAt": "2024-02-25T01:55:24.275184461Z",
            "Driver": "null",
            "ID": "377f68874a6b",
            "Internal": false,
            "IPv6": false,
            "Labels": {},
            "Name": "none",
            "Scope": "local"
          },
          {
            "CreatedAt": "2024-02-25T01:55:24.275184461Z",
            "Driver": "bridge",
            "ID": "f7dd41949939",
            "Internal": false,
            "IPv6": false,
            "Labels": {
              "com.dokku.network-name": "test-net-1"
            },
            "Name": "test-net-1",
            "Scope": "local"
          },
          {
            "CreatedAt": "2024-02-25T01:55:24.275184461Z",
            "Driver": "bridge",
            "ID": "6dce7688f1c3",
            "Internal": false,
            "IPv6": false,
            "Labels": {
              "com.dokku.network-name": "test-net-2"
            },
            "Name": "test-net-2",
            "Scope": "local"
          },
          {
            "CreatedAt": "2024-02-25T01:55:24.275184461Z",
            "Driver": "bridge",
            "ID": "c088cebd250e",
            "Internal": false,
            "IPv6": false,
            "Labels": {},
            "Name": "bridge",
            "Scope": "local"
          },
          {
            "CreatedAt": "2024-02-25T01:55:24.275184461Z",
            "Driver": "host",
            "ID": "b3cc5764fa3f",
            "Internal": false,
            "IPv6": false,
            "Labels": {},
            "Name": "host",
            "Scope": "local"
          }
        ]
    """
    expected = [
        Network(
            id="377f68874a6b",
            name="none",
            created_at=datetime.datetime(2024, 2, 25, 1, 55, 24, 275184, tzinfo=datetime.timezone.utc),
            driver="null",
            internal=False,
            ipv6=False,
            labels={},
            scope="local",
        ),
        Network(
            id="f7dd41949939",
            name="test-net-1",
            created_at=datetime.datetime(2024, 2, 25, 1, 55, 24, 275184, tzinfo=datetime.timezone.utc),
            driver="bridge",
            internal=False,
            ipv6=False,
            labels={"com.dokku.network-name": "test-net-1"},
            scope="local",
        ),
        Network(
            id="6dce7688f1c3",
            name="test-net-2",
            created_at=datetime.datetime(2024, 2, 25, 1, 55, 24, 275184, tzinfo=datetime.timezone.utc),
            driver="bridge",
            internal=False,
            ipv6=False,
            labels={"com.dokku.network-name": "test-net-2"},
            scope="local",
        ),
        Network(
            id="c088cebd250e",
            name="bridge",
            created_at=datetime.datetime(2024, 2, 25, 1, 55, 24, 275184, tzinfo=datetime.timezone.utc),
            driver="bridge",
            internal=False,
            ipv6=False,
            labels={},
            scope="local",
        ),
        Network(
            id="b3cc5764fa3f",
            name="host",
            created_at=datetime.datetime(2024, 2, 25, 1, 55, 24, 275184, tzinfo=datetime.timezone.utc),
            driver="host",
            internal=False,
            ipv6=False,
            labels={},
            scope="local",
        ),
    ]
    dokku = Dokku()
    result = dokku.network._parse_list_json(json_data)
    assert result == expected


def test_set_command():
    dokku = Dokku()
    app_name = "test-app-1"
    network_name = "test-net-1"
    command = dokku.network.set(app_name=app_name, key="attach-post-create", value=network_name, execute=False)
    assert command.command == ["dokku", "network:set", app_name, "attach-post-create", network_name]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False
    command = dokku.network.set(app_name=None, key="attach-post-create", value=network_name, execute=False)
    assert command.command == ["dokku", "network:set", "--global", "attach-post-create", network_name]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False


def test_set_many_command():
    dokku = Dokku()
    app_name = "test-app-1"
    network_names = ["test-net-1", "test-net-2"]
    command = dokku.network.set_many(app_name=app_name, key="attach-post-create", values=network_names, execute=False)
    assert command.command == ["dokku", "network:set", app_name, "attach-post-create"] + network_names
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False
    command = dokku.network.set_many(app_name=None, key="attach-post-create", values=network_names, execute=False)
    assert command.command == ["dokku", "network:set", "--global", "attach-post-create"] + network_names
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False


def test_unset_command():
    dokku = Dokku()
    app_name = "test-app-1"
    command = dokku.network.unset(app_name=app_name, key="attach-post-create", execute=False)
    assert command.command == ["dokku", "network:set", app_name, "attach-post-create"]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False
    command = dokku.network.unset(app_name=None, key="attach-post-create", execute=False)
    assert command.command == ["dokku", "network:set", "--global", "attach-post-create"]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False


def test_rebuild_commands():
    dokku = Dokku()
    app_name = "test-app-1"
    command = dokku.network.rebuild(app_name=app_name, execute=False)
    assert command.command == ["dokku", "network:rebuild", app_name]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False
    command = dokku.network.rebuild(app_name=None, execute=False)
    assert command.command == ["dokku", "network:rebuildall"]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False


def test_parse_report():
    stdout = """
        =====> test-app-8 network information
            Network attach post create:           test-net-3,test-net-4
            Network attach post deploy:
            Network bind all interfaces:          false
            Network computed attach post create:  test-net-3,test-net-4
            Network computed attach post deploy:
            Network computed bind all interfaces: false
            Network computed initial network:     global-network
            Network computed tld:
            Network global attach post create:
            Network global attach post deploy:
            Network global bind all interfaces:   false
            Network global initial network:       global-network
            Network global tld:
            Network initial network:
            Network static web listener:          127.0.0.1:5000
            Network tld:
            Network web listeners:
        =====> test-app-9 network information
            Network attach post create:           test-net-2
            Network attach post deploy:
            Network bind all interfaces:          true
            Network computed attach post create:  test-net-2
            Network computed attach post deploy:
            Network computed bind all interfaces: true
            Network computed initial network:     test-net-3
            Network computed tld:
            Network global attach post create:
            Network global attach post deploy:
            Network global bind all interfaces:   false
            Network global initial network:       global-network
            Network global tld:
            Network initial network:              test-net-3
            Network static web listener:
            Network tld:                          svc.cluster.local
            Network web listeners:
    """
    expected = [
        {
            "app_name": "test-app-8",
            "attach_post_create": ["test-net-3", "test-net-4"],
            "attach_post_deploy": [],
            "bind_all_interfaces": False,
            "global_attach_post_create": [],
            "global_attach_post_deploy": [],
            "global_bind_all_interfaces": False,
            "global_initial_network": "global-network",
            "global_tld": None,
            "initial_network": None,
            "static_web_listener": "127.0.0.1:5000",
            "tld": None,
        },
        {
            "app_name": "test-app-9",
            "attach_post_create": ["test-net-2"],
            "attach_post_deploy": [],
            "bind_all_interfaces": True,
            "global_attach_post_create": [],
            "global_attach_post_deploy": [],
            "global_bind_all_interfaces": False,
            "global_initial_network": "global-network",
            "global_tld": None,
            "initial_network": "test-net-3",
            "static_web_listener": None,
            "tld": "svc.cluster.local",
        },
    ]
    dokku = Dokku()
    rows_parser = dokku.network._get_rows_parser()
    result = rows_parser(stdout)
    assert result == expected


def test_convert_report_rows():
    input_data = [
        {
            "app_name": "test-app-8",
            "attach_post_create": ["test-net-3", "test-net-4"],
            "attach_post_deploy": [],
            "bind_all_interfaces": False,
            "global_attach_post_create": [],
            "global_attach_post_deploy": [],
            "global_bind_all_interfaces": False,
            "global_initial_network": "global-network",
            "global_tld": None,
            "initial_network": None,
            "static_web_listener": "127.0.0.1:5000",
            "tld": None,
        },
        {
            "app_name": "test-app-9",
            "attach_post_create": ["test-net-2"],
            "attach_post_deploy": [],
            "bind_all_interfaces": True,
            "global_attach_post_create": [],
            "global_attach_post_deploy": [],
            "global_bind_all_interfaces": False,
            "global_initial_network": "test-net-1",  # Only the first global is considered (this one must be equal)
            "global_tld": None,
            "initial_network": "test-net-3",
            "static_web_listener": None,
            "tld": "svc.cluster.local",
        },
    ]
    expected = [
        AppNetwork(
            app_name=None,
            attach_post_create=[],
            attach_post_deploy=[],
            bind_all_interfaces=False,
            initial_network="global-network",
            tld=None,
        ),
        AppNetwork(
            app_name="test-app-8",
            attach_post_create=["test-net-3", "test-net-4"],
            attach_post_deploy=[],
            bind_all_interfaces=False,
            initial_network=None,
            static_web_listener="127.0.0.1:5000",
            tld=None,
        ),
        AppNetwork(
            app_name="test-app-9",
            attach_post_create=["test-net-2"],
            attach_post_deploy=[],
            bind_all_interfaces=True,
            initial_network="test-net-3",
            static_web_listener=None,
            tld="svc.cluster.local",
        ),
    ]
    dokku = Dokku()
    result = dokku.network._convert_rows(input_data, skip_system=False)
    assert result == expected
    result_2 = dokku.network._convert_rows(input_data, skip_system=True)
    assert result_2 == expected[1:]


@requires_dokku
def test_create_list_destroy():
    # Ensure none of the networks and apps exist. Removing apps before networks is important because if a network is
    # attached to an app it will be impossible to remove the network.
    dokku = Dokku()
    for app in dokku.apps.list():
        dokku.apps.destroy(app.name)
    network_names = ["test-net-1", "test-net-2"]
    for name in network_names:
        # Since we're testing Dokku's network implementation, I prefer to delete them using Docker instead of the Dokku
        # network command.
        execute_command(["sudo", "docker", "network", "remove", name], check=False)

    before = dokku.network.list()
    returned_names = [network.name for network in before]
    for name in network_names:
        assert name not in returned_names

    for name in network_names:
        dokku.network.create(name=name)
    after = dokku.network.list()
    assert len(after) == len(before) + 2
    returned_names = [network.name for network in after]
    for name in network_names:
        assert name in returned_names

    for name in network_names:
        dokku.network.destroy(name=name)
    final = dokku.network.list()
    returned_names = [network.name for network in final]
    for name in network_names:
        assert name not in returned_names


@requires_dokku
def test_set_unset_report(create_apps):
    # Ensure none of the networks and apps exist. Removing apps before networks is important because if a network is
    # attached to an app it will be impossible to remove the network.
    dokku, apps_names = create_apps
    for app in dokku.apps.list():
        if app.name not in apps_names:
            dokku.apps.destroy(app.name)
    network_names = [f"test-net-{x}" for x in range(10)]
    for name in network_names:
        # Since we're testing Dokku's network implementation, I prefer to delete them using Docker instead of the Dokku
        # network command.
        execute_command(["sudo", "docker", "network", "remove", name], check=False)

    for name in network_names:
        dokku.network.create(name=name)

    before = {appnet.app_name: appnet for appnet in dokku.network.report()}
    global_initial = before[None].initial_network
    new_global_initial = str(global_initial or "test-net") + "-new"
    dokku.network.set(app_name=None, key="initial-network", value=new_global_initial)
    after_new_global = {appnet.app_name: appnet for appnet in dokku.network.report()}
    assert after_new_global[None].initial_network == new_global_initial

    apps_nets = {}
    for app_name in [None] + apps_names:
        apps_nets[app_name] = {}
        # TODO: remove other nets of the same app
        if app_name is None:  # Global network
            app_nets = list(random.sample(network_names, random.randint(1, len(network_names) // 3)))
        else:  # Should not add networks already set as global
            global_networks = apps_nets[None]["attach-post-create"] + apps_nets[None]["attach-post-deploy"]
            possible_networks = [name for name in network_names if name not in global_networks]
            app_nets = list(random.sample(possible_networks, random.randint(3, len(possible_networks))))
        apps_nets[app_name]["attach-post-create"] = app_nets[:2]
        dokku.network.set_many(
            app_name=app_name, key="attach-post-create", values=apps_nets[app_name]["attach-post-create"]
        )
        apps_nets[app_name]["attach-post-deploy"] = app_nets[2:]
        dokku.network.set_many(
            app_name=app_name, key="attach-post-deploy", values=apps_nets[app_name]["attach-post-deploy"]
        )
        apps_nets[app_name]["tld"] = f"test-{random_alphanum(16)}.example.net"
        dokku.network.set(app_name=app_name, key="tld", value=apps_nets[app_name]["tld"])
        apps_nets[app_name]["bind-all-interfaces"] = random.choice([True, False])
        dokku.network.set(
            app_name=app_name, key="bind-all-interfaces", value=apps_nets[app_name]["bind-all-interfaces"]
        )
        apps_nets[app_name]["initial-network"] = random.choice(["bridge", "none", "global-network"])
        dokku.network.set(app_name=app_name, key="initial-network", value=apps_nets[app_name]["initial-network"])
        if app_name is not None:
            apps_nets[app_name]["static-web-listener"] = f"127.0.0.1:{random.randint(20_000, 80_000)}"
            dokku.network.set(
                app_name=app_name, key="static-web-listener", value=apps_nets[app_name]["static-web-listener"]
            )
        else:
            apps_nets[app_name]["static-web-listener"] = None

    after = {appnet.app_name: appnet for appnet in dokku.network.report()}
    assert set(apps_nets.keys()).issubset(set(after.keys()))
    for app_name, keys_values in apps_nets.items():
        result_appnet = after[app_name]
        for key, value in keys_values.items():
            result_value = getattr(result_appnet, key.replace("-", "_"))
            assert result_value == value

    # Reset values
    for name in network_names:
        dokku.network.destroy(name=name)
    dokku.network.set_many(app_name=None, key="attach-post-create", values=before[None].attach_post_create)
    dokku.network.set_many(app_name=None, key="attach-post-deploy", values=before[None].attach_post_deploy)
    dokku.network.set(app_name=None, key="tld", value=before[None].tld)
    dokku.network.set(app_name=None, key="bind-all-interfaces", value=before[None].bind_all_interfaces)
    dokku.network.set(app_name=None, key="initial-network", value=before[None].initial_network)


# TODO: test object_create
# TODO: test object_list
