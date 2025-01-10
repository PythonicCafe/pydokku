import subprocess
from copy import deepcopy
from pathlib import Path

from pydokku import Dokku
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
    subprocess.run([cleanup_script], capture_output=True)
    subprocess.run([create_test_env_script], capture_output=True)
    data_1 = dokku_dump()
    subprocess.run([cleanup_script], capture_output=True)
    dokku_load(deepcopy(data_1))
    data_2 = dokku_dump()
    subprocess.run([cleanup_script], capture_output=True)
    for app in data_1["apps"] + data_2["apps"]:
        app["created_at"] = None
    assert data_1 == data_2
