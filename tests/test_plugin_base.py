from pathlib import Path

from pydokku import Dokku
from pydokku.cli import dokku_apply, dokku_export
from pydokku.plugins.base import PluginScheduler
from pydokku.utils import execute_command
from tests.utils import requires_dokku


def test_PluginScheduler():
    class PluginA:
        name = "a"
        requires = ()

    class PluginB:
        name = "b"
        requires = ("a",)

    class PluginC:
        name = "c"
        requires = ("a",)

    class PluginD:
        name = "d"
        requires = ("c",)

    class PluginE:
        name = "e"
        requires = ("b", "d")

    class PluginF:
        name = "f"
        requires = ("c",)

    plugins = [PluginA, PluginB, PluginC, PluginD, PluginE, PluginF]
    scheduler = PluginScheduler(plugins)
    result = list(scheduler)
    expected = [
        ["a"],
        ["b", "c"],
        ["d", "f"],
        ["e"],
    ]
    assert result == expected


@requires_dokku
def test_export_apply():
    current_path = Path(__file__).parent
    scripts_path = current_path.parent / "scripts"
    cleanup_script = str((scripts_path / "cleanup.sh").absolute())
    create_test_env_script = str((scripts_path / "create-test-env.sh").absolute())
    dokku = Dokku()
    implemented_plugins = set(dokku.plugins.keys())

    execute_command([cleanup_script], check=True)
    execute_command([create_test_env_script], check=True)
    data_1 = dokku_export(ssh_config={}, quiet=True)
    # Since it requires a real domain name/IP to execute some letsencrypt commands, it's completely skipped here
    data_1["letsencrypt"] = []
    exported_plugins_1 = set(key for key in data_1.keys() if key not in ("pydokku", "dokku"))
    assert exported_plugins_1 == implemented_plugins
    execute_command([cleanup_script], check=True)
    dokku_apply(data=data_1, ssh_config={}, force=True, quiet=True, execute=True)
    data_2 = dokku_export(ssh_config={}, quiet=True)
    data_2["letsencrypt"] = []
    exported_plugins_2 = set(key for key in data_2.keys() if key not in ("pydokku", "dokku"))
    assert exported_plugins_2 == implemented_plugins
    execute_command([cleanup_script], check=True)

    # Since we run cleanup, some information will not be exactly the same, like `App.created_at` and
    # `Process.container_id`, so we need to set them to the same value so the `assert` works as expected.
    # The `create_test_env_script` will setup as follows:
    # - test-app-7 is not deployed, but git image is set
    # - test-app-8 is deployed and git commit changes
    # - test-app-9 is not deployed and git image is not set
    for app in data_1["apps"] + data_2["apps"]:
        app["created_at"] = None
    for process_info in data_1["ps"] + data_2["ps"]:
        for process in process_info["processes"]:
            process["container_id"] = None
    for config in data_1["config"] + data_2["config"]:
        if config["app_name"] == "test-app-8" and config["key"] == "GIT_REV":
            config["value"] = None
    for git in data_1["git"] + data_2["git"]:
        for key in ("last_updated_at", "sha"):
            if key in git:
                git[key] = None
    # Created public key is exported but won't be created again
    data_1["git"] = [git for git in data_1["git"] if git.get("name") != "dokku-public-key"]
    for nginx in data_1["nginx"] + data_2["nginx"]:
        nginx["last_visited_at"] = None  # For some reason, nginx adds it after a while

    def sort_network(obj):
        if "name" in obj:  # Network
            return (0, obj["name"])
        else:  # AppNetwork
            return (
                1,
                obj.get("app_name") or "",
                obj.get("initial_network") or "",
                obj["attach_post_create"],
                obj["attach_post_deploy"],
            )

    # Order of returned networks could be different between the extractions, so it's forced
    data_1["network"].sort(key=sort_network)
    data_2["network"].sort(key=sort_network)
    for network in data_1["network"] + data_2["network"]:
        if "labels" in network and "com.dokku.network-name" in network["labels"]:
            network["id"] = network["created_at"] = None

    assert data_1 == data_2
