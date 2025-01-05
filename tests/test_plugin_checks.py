from dokkupy.dokku_cli import Dokku
from tests.utils import requires_dokku


def test_set_wait_to_retire_command():
    dokku = Dokku()
    app_name = "test-app-1"
    wait = 30

    command = dokku.checks.set_wait_to_retire(app_name, wait, execute=False)
    assert command.command == ["dokku", "checks:set", app_name, "wait-to-retire", str(wait)]


def test_enable_command():
    dokku = Dokku()
    app_name = "test-app-1"
    processes = ["web", "worker"]

    command = dokku.checks.enable(app_name, execute=False)
    assert command.command == ["dokku", "checks:enable", app_name]

    command = dokku.checks.enable(app_name, processes, execute=False)
    assert command.command == ["dokku", "checks:enable", app_name, ",".join(processes)]


def test_disable_command():
    dokku = Dokku()
    app_name = "test-app-1"
    processes = ["web", "worker"]

    command = dokku.checks.disable(app_name, execute=False)
    assert command.command == ["dokku", "checks:disable", app_name]

    command = dokku.checks.disable(app_name, processes, execute=False)
    assert command.command == ["dokku", "checks:disable", app_name, ",".join(processes)]


def test_skip_command():
    dokku = Dokku()
    app_name = "test-app-1"
    processes = ["web", "worker"]

    command = dokku.checks.skip(app_name, execute=False)
    assert command.command == ["dokku", "checks:skip", app_name]

    command = dokku.checks.skip(app_name, processes, execute=False)
    assert command.command == ["dokku", "checks:skip", app_name, ",".join(processes)]


def test_run_command():
    dokku = Dokku()
    app_name = "test-app-1"

    command = dokku.checks.run(app_name, execute=False)
    assert command.command == ["dokku", "checks:run", app_name]


@requires_dokku
def test_list_set_enable_disable_skip_run():
    dokku = Dokku()
    app_name_1 = "test-app-checks-1"
    app_name_2 = "test-app-checks-2"

    dokku.apps.create(app_name_1)
    dokku.apps.create(app_name_2)

    # Default checks
    checks = {check.app_name: check for check in dokku.checks.list()}
    global_wait = checks[None].global_wait_to_retire
    for app_name in (app_name_1, app_name_2):
        check = checks[app_name]
        assert check.app_name == app_name
        assert check.process == "_all_"
        assert check.status == "enabled"
        assert check.app_wait_to_retire is None
        assert check.global_wait_to_retire == global_wait
        assert check.wait_to_retire == global_wait

    # Change global wait to retire
    new_global_wait = global_wait * 2
    wait_app_1 = global_wait * 3
    dokku.checks.set_wait_to_retire(app_name=None, value=new_global_wait)
    dokku.checks.set_wait_to_retire(app_name=app_name_1, value=wait_app_1)
    checks = {check.app_name: check for check in dokku.checks.list()}
    assert checks[None].global_wait_to_retire == new_global_wait
    assert checks[app_name_1].app_wait_to_retire == wait_app_1
    assert checks[app_name_1].global_wait_to_retire == new_global_wait
    assert checks[app_name_1].wait_to_retire == wait_app_1  # Custom value defined
    assert checks[app_name_2].app_wait_to_retire is None
    assert checks[app_name_2].global_wait_to_retire == new_global_wait
    assert checks[app_name_2].wait_to_retire == new_global_wait  # No custom value, so use the global setting

    dokku.checks.disable(app_name_1, ["worker", "another-worker"])
    app_checks = dokku.checks.list(app_name=app_name_1)
    assert len(app_checks) == 2  # The enabled ones won't be here, since Dokku does not provide this information
    app_checks.sort(key=lambda obj: obj.process)
    app_checks[0].app_name == app_name_1
    app_checks[0].process == "another-worker"
    app_checks[0].status == "disabled"
    app_checks[1].app_name == app_name_1
    app_checks[1].process == "worker"
    app_checks[1].status == "disabled"
    dokku.checks.enable(app_name_1, ["another-worker"])
    app_checks = dokku.checks.list(app_name=app_name_1)
    assert len(app_checks) == 1  # The enabled ones won't be here, since Dokku does not provide this information
    app_checks.sort(key=lambda obj: obj.process)
    app_checks[0].process == "worker"
    app_checks[0].status == "disabled"

    dokku.checks.skip(app_name_2, ["web"])
    app_checks = dokku.checks.list(app_name=app_name_2)
    assert len(app_checks) == 1  # The enabled ones won't be here, since Dokku does not provide this information
    app_checks[0].app_name == app_name_2
    app_checks[0].process == "web"
    app_checks[0].status == "skipped"

    dokku.apps.destroy(app_name_1)
    dokku.apps.destroy(app_name_2)
