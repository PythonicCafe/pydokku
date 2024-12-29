from pathlib import Path

import pytest

from dokkupy.dokku_cli import Dokku
from dokkupy.models import Storage
from tests.utils import requires_dokku


def test_ensure_directory_command():
    dir_name = "test-app-data"
    chown = "heroku"
    dokku = Dokku()
    command = dokku.storage.ensure_directory(dir_name, chown=chown, execute=False)
    assert command.command == ["dokku", "storage:ensure-directory", "--chown", chown, dir_name]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False

    command = dokku.storage.ensure_directory(dir_name, execute=False)
    assert command.command == ["dokku", "storage:ensure-directory", dir_name]
    with pytest.raises(
        ValueError, match=r"Invalid value for chown: 'non-ecxiste' \(expected: herokuish, heroku, packeto, root\)"
    ):
        dokku.storage.ensure_directory(dir_name, chown="non-ecxiste", execute=False)


def test_mount_command():
    app_name = "test-app"
    host_path = Path("/var/lib/dokku/data/storage/test-app-data")
    container_path = Path("/data")
    storage = Storage(app_name=app_name, host_path=host_path, container_path=container_path)
    dokku = Dokku()
    command = dokku.storage.mount(storage, execute=False)
    assert command.command == ["dokku", "storage:mount", app_name, f"{host_path}:{container_path}"]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False

    with pytest.raises(ValueError, match=r"`host_path` must be an absolute path \(got: host-data\)"):
        wrong_storage = Storage(app_name=app_name, host_path=Path("host-data"), container_path=container_path)
        dokku.storage.mount(wrong_storage, execute=False)
    with pytest.raises(ValueError, match=r"`container_path` must be an absolute path \(got: container-data\)"):
        wrong_storage = Storage(app_name=app_name, host_path=host_path, container_path=Path("container-data"))
        dokku.storage.mount(wrong_storage, execute=False)


def test_unmount_command():
    app_name = "test-app"
    host_path = Path("/var/lib/dokku/data/storage/test-app-data")
    container_path = Path("/data")
    storage = Storage(app_name=app_name, host_path=host_path, container_path=container_path)
    dokku = Dokku()
    command = dokku.storage.unmount(storage, execute=False)
    assert command.command == ["dokku", "storage:unmount", app_name, f"{host_path}:{container_path}"]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False


@requires_dokku
def test_ensure_mount_list_unmount():
    app_name = "test-app"
    host_path = Path("/var/lib/dokku/data/storage/test-app-data")
    container_path = Path("/data")
    storage = Storage(app_name=app_name, host_path=host_path, container_path=container_path)
    dokku = Dokku()

    dokku.apps.create(app_name)
    path, (user_id, group_id) = dokku.storage.ensure_directory(host_path.name)
    assert path == host_path
    assert path.exists()

    storage_before = dokku.storage.list(app_name)
    dokku.storage.mount(storage)
    storage_after = dokku.storage.list(app_name)
    assert len(storage_before) + 1 == len(storage_after)
    result = storage_after[0]
    assert result.app_name == storage.app_name
    assert result.host_path == storage.host_path
    assert result.container_path == storage.container_path
    assert result.user_id == 32767  # Default chown is `herokuish`
    assert result.group_id == 32767  # Default chown is `herokuish`

    dokku.storage.unmount(storage)
    assert len(dokku.storage.list(app_name)) == 0
    # XXX: won't try to delete the `path` here since the test won't be running as the `dokku` user
    dokku.apps.destroy(app_name)

# TODO: test dump
# TODO: test create_object
