import datetime
from pathlib import Path

from dokkupy.dokku_cli import Dokku
from dokkupy.models import App
from tests.utils import requires_dokku


def test_create_command():
    app_name = "test-app"
    dokku = Dokku()
    command = dokku.apps.create(app_name, execute=False)
    assert command.command == ["dokku", "apps:create", app_name]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False


def test_destroy_command():
    app_name = "test-app"
    dokku = Dokku()
    command = dokku.apps.destroy(app_name, execute=False)
    assert command.command == ["dokku", "apps:destroy", app_name]
    assert command.stdin == app_name
    assert command.check is True
    assert command.sudo is False


def test_clone_command():
    app_name, new_app_name = "test-app", "test-app-new"
    dokku = Dokku()
    command = dokku.apps.clone(app_name, new_app_name, execute=False)
    assert command.command == ["dokku", "apps:clone", app_name, new_app_name]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False


def test_lock_command():
    app_name = "test-app"
    dokku = Dokku()
    command = dokku.apps.lock(app_name, execute=False)
    assert command.command == ["dokku", "apps:lock", app_name]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False


def test_unlock_command():
    app_name = "test-app"
    dokku = Dokku()
    command = dokku.apps.unlock(app_name, execute=False)
    assert command.command == ["dokku", "apps:unlock", app_name]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False


def test_rename_command():
    app_name, new_app_name = "test-app", "test-app-new"
    dokku = Dokku()
    command = dokku.apps.rename(app_name, new_app_name, execute=False)
    assert command.command == ["dokku", "apps:rename", app_name, new_app_name]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False


def test_create_object_command():
    app_name = "test-app"
    created_at = datetime.datetime.now()
    app_path = Path(f"/tmp/{app_name}")
    unlocked_app = App(name=app_name, created_at=created_at, path=app_path, locked=False)
    locked_app = App(name=app_name, created_at=created_at, path=app_path, locked=True)
    dokku = Dokku()
    command1 = dokku.apps.create(app_name, execute=False)
    command2 = dokku.apps.lock(app_name, execute=False)

    assert dokku.apps.create_object(obj=unlocked_app, execute=False) == [command1]
    assert dokku.apps.create_object(obj=locked_app, execute=False) == [command1, command2]


@requires_dokku
def test_list_create_destroy():
    app_name = "test-app"
    dokku = Dokku()
    apps_before = dokku.apps.list()
    dokku.apps.create(app_name)
    apps_after = dokku.apps.list()
    assert len(apps_before) + 1 == len(apps_after)
    apps_after_by_name = {app.name: app for app in apps_after}
    assert app_name in apps_after_by_name
    dokku.apps.destroy(app_name)
    assert len(dokku.apps.list()) == len(apps_before)


@requires_dokku
def test_create_lock_unlock():
    app_name = "test-app"
    dokku = Dokku()
    dokku.apps.create(app_name)
    apps_before = {app.name: app for app in dokku.apps.list()}
    assert apps_before[app_name].locked is False
    assert dokku.apps.locked(app_name) is False

    dokku.apps.lock(app_name)
    apps_after = {app.name: app for app in dokku.apps.list()}
    assert apps_after[app_name].locked is True
    assert dokku.apps.locked(app_name) is True

    # XXX: won't test/try to unlock, since the app is not deployed and Dokku does not allow unlocking (!)

    dokku.apps.destroy(app_name)


@requires_dokku
def test_create_clone():
    app_name, clone_app_name = "test-app", "test-app-clone"
    dokku = Dokku()
    dokku.apps.create(app_name)
    apps_before = {app.name: app for app in dokku.apps.list()}

    dokku.apps.clone(app_name, clone_app_name)
    apps_after = {app.name: app for app in dokku.apps.list()}
    assert len(apps_before) + 1 == len(apps_after)
    assert clone_app_name in apps_after
    assert app_name in apps_after

    dokku.apps.destroy(app_name)
    dokku.apps.destroy(clone_app_name)


@requires_dokku
def test_create_rename():
    app_name, renamed_app_name = "test-app", "test-app-renamed"
    dokku = Dokku()
    dokku.apps.create(app_name)
    apps_before = {app.name: app for app in dokku.apps.list()}

    dokku.apps.rename(app_name, renamed_app_name)
    apps_after = {app.name: app for app in dokku.apps.list()}
    assert len(apps_before) == len(apps_after)
    assert renamed_app_name in apps_after
    assert app_name not in apps_after

    dokku.apps.destroy(renamed_app_name)
