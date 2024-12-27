from pathlib import Path

import pytest

from dokkupy.dokku_cli import Dokku
from dokkupy.plugins.storage import Storage


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
        ValueError, match=r"Invalid value for chown: 'non-ecxiste' \(expected: heroku, herokuish, packeto, root\)"
    ):
        dokku.storage.ensure_directory(dir_name, chown="non-ecxiste", execute=False)


def test_mount_command():
    app_name = "test-app"
    host_path = Path("/var/lib/dokku/data/storage/test-app-data")
    container_path = Path("/data")
    storage = Storage(host_path=host_path, container_path=container_path)
    dokku = Dokku()
    command = dokku.storage.mount(app_name, storage=storage, execute=False)
    assert command.command == ["dokku", "storage:mount", app_name, f"{host_path}:{container_path}"]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False

    with pytest.raises(ValueError, match=r"`host_path` must be an absolute path \(got: host-data\)"):
        wrong_storage = Storage(host_path=Path("host-data"), container_path=container_path)
        dokku.storage.mount(app_name, storage=wrong_storage, execute=False)
    with pytest.raises(ValueError, match=r"`container_path` must be an absolute path \(got: container-data\)"):
        wrong_storage = Storage(host_path=host_path, container_path=Path("container-data"))
        dokku.storage.mount(app_name, storage=wrong_storage, execute=False)


def test_unmount_command():
    app_name = "test-app"
    host_path = Path("/var/lib/dokku/data/storage/test-app-data")
    container_path = Path("/data")
    storage = Storage(host_path=host_path, container_path=container_path)
    dokku = Dokku()
    command = dokku.storage.unmount(app_name, storage=storage, execute=False)
    assert command.command == ["dokku", "storage:unmount", app_name, f"{host_path}:{container_path}"]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False


def test_ensure_mount_list_unmount():
    app_name = "test-app"
    host_path = Path("/var/lib/dokku/data/storage/test-app-data")
    container_path = Path("/data")
    storage = Storage(host_path=host_path, container_path=container_path, options="")
    dokku = Dokku()

    dokku.apps.create(app_name)
    path, (user_id, group_id) = dokku.storage.ensure_directory(host_path.name)
    assert path == host_path
    assert path.exists()

    storage_before = dokku.storage.list(app_name)
    dokku.storage.mount(app_name, storage=storage)
    storage_after = dokku.storage.list(app_name)
    assert len(storage_before) + 1 == len(storage_after)
    assert storage_after[0] == storage

    dokku.storage.unmount(app_name, storage=storage)
    assert len(dokku.storage.list(app_name)) == 0
    # XXX: won't try to delete the `path` here since the test won't be running as the `dokku` user
    dokku.apps.destroy(app_name)
