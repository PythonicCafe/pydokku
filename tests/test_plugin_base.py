import subprocess
from copy import deepcopy
from pathlib import Path

from pydokku import Dokku
from pydokku.utils import execute_command
from tests.utils import requires_dokku


def dokku_dump():
    # TODO: unify with pydokku/cli.py (without the logging)
    dokku = Dokku()
    data = {
        "dokku": {"version": dokku.version()},
    }
    apps = dokku.apps.list()
    for name, plugin in dokku.plugins.items():
        data[name] = []
        for obj in plugin.object_list(apps, system=True):
            data[name].append(obj.serialize())
    return data


def dokku_load(data):
    # TODO: unify with pydokku/cli.py (without the logging)
    dokku = Dokku()
    for key, values in sorted(data.items()):
        if key == "dokku":
            continue
        plugin = getattr(dokku, key)
        objects = [plugin.object_deserialize(row) for row in values]
        for result in plugin.object_create_many(objects, execute=True):
            continue


@requires_dokku
def test_dump_load():
    current_path = Path(__file__).parent
    scripts_path = current_path.parent / "scripts"
    cleanup_script = str((scripts_path / "cleanup.sh").absolute())
    create_test_env_script = str((scripts_path / "create-test-env.sh").absolute())

    execute_command([cleanup_script], check=True)
    execute_command([create_test_env_script], check=True)
    data_1 = dokku_dump()
    execute_command([cleanup_script], check=True)
    dokku_load(deepcopy(data_1))
    data_2 = dokku_dump()
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
                obj["app_name"] if obj["app_name"] is not None else "",
                obj["initial_network"] if obj["initial_network"] is not None else "",
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
