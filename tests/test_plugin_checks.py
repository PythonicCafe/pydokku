from pydokku.dokku_cli import Dokku
from pydokku.models import Check
from tests.utils import requires_dokku


def test_object_classes():
    dokku = Dokku()
    assert dokku.checks.object_classes == (Check,)


def test_check_wait_to_retire_property():
    app_name = "test-app-1"
    check_1 = Check(
        app_name=app_name, process="web", status="disabled", app_wait_to_retire=None, global_wait_to_retire=60
    )
    check_2 = Check(
        app_name=app_name, process="web", status="disabled", app_wait_to_retire=30, global_wait_to_retire=60
    )
    assert check_1.wait_to_retire == 60  # Global `wait_to_retire`, since app's is None
    assert check_2.wait_to_retire == 30  # App's own `wait_to_retire`


def test_set_command():
    dokku = Dokku()
    app_name = "test-app-1"
    wait = 30
    command = dokku.checks.set(app_name, key="wait-to-retire", value=wait, execute=False)
    assert command.command == ["dokku", "checks:set", app_name, "wait-to-retire", str(wait)]


def test_unset_command():
    dokku = Dokku()
    app_name = "test-app-1"
    command = dokku.checks.unset(app_name, key="wait-to-retire", execute=False)
    assert command.command == ["dokku", "checks:set", app_name, "wait-to-retire"]


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


def test_parse_report():
    stdout = """
        =====> test-app-7 checks information
            Checks disabled list:          none
            Checks skipped list:           none
            Checks computed wait to retire: 60
            Checks global wait to retire:  60
            Checks wait to retire:
        =====> test-app-8 checks information
            Checks disabled list:          none
            Checks skipped list:           none
            Checks computed wait to retire: 30
            Checks global wait to retire:  60
            Checks wait to retire:         30
        =====> test-app-9 checks information
            Checks disabled list:          web,worker
            Checks skipped list:           another-worker
            Checks computed wait to retire: 60
            Checks global wait to retire:  60
            Checks wait to retire:
    """
    expected = [
        {
            "app_name": "test-app-7",
            "app_wait_to_retire": None,
            "global_wait_to_retire": 60,
            "disabled": [],
            "skipped": [],
        },
        {
            "app_name": "test-app-8",
            "app_wait_to_retire": 30,
            "global_wait_to_retire": 60,
            "disabled": [],
            "skipped": [],
        },
        {
            "app_name": "test-app-9",
            "app_wait_to_retire": None,
            "global_wait_to_retire": 60,
            "disabled": ["web", "worker"],
            "skipped": ["another-worker"],
        },
    ]
    dokku = Dokku()
    rows_parser = dokku.checks._get_rows_parser()
    result = rows_parser(stdout)
    assert result == expected


def test_convert_rows():
    input_rows = [
        {
            "app_name": "test-app-7",
            "app_wait_to_retire": None,
            "global_wait_to_retire": 60,
            "disabled": [],
            "skipped": [],
        },
        {
            "app_name": "test-app-8",
            "app_wait_to_retire": 30,
            "global_wait_to_retire": 60,
            "disabled": [],
            "skipped": [],
        },
        {
            "app_name": "test-app-9",
            "app_wait_to_retire": None,
            "global_wait_to_retire": 60,
            "disabled": ["web", "worker"],
            "skipped": ["another-worker"],
        },
    ]
    all_checks = [
        Check(
            app_name=None,
            process="_all_",
            status=None,
            global_wait_to_retire=60,
            app_wait_to_retire=None,
        ),
        Check(
            app_name="test-app-7",
            process="_all_",
            status="enabled",
            global_wait_to_retire=60,
            app_wait_to_retire=None,
        ),
        Check(
            app_name="test-app-8",
            process="_all_",
            status="enabled",
            global_wait_to_retire=60,
            app_wait_to_retire=30,
        ),
        Check(
            app_name="test-app-9",
            process="web",
            status="disabled",
            global_wait_to_retire=60,
            app_wait_to_retire=None,
        ),
        Check(
            app_name="test-app-9",
            process="worker",
            status="disabled",
            global_wait_to_retire=60,
            app_wait_to_retire=None,
        ),
        Check(
            app_name="test-app-9",
            process="another-worker",
            status="skipped",
            global_wait_to_retire=60,
            app_wait_to_retire=None,
        ),
    ]
    dokku = Dokku()
    result = dokku.checks._convert_rows([input_rows[0]], app_name="test-app-7")  # app 7 and no global
    assert result == [all_checks[1]]
    result = dokku.checks._convert_rows([input_rows[0]], app_name=None)  # app 7 + global
    assert result == all_checks[:2]
    result = dokku.checks._convert_rows([input_rows[2]], app_name="test-app-9")  # app 9 (more than one Check returned)
    assert result == all_checks[-3:]
    result = dokku.checks._convert_rows(input_rows, app_name=None)  # Everyting
    assert result == all_checks


@requires_dokku
def test_list_set_enable_disable_skip_run(create_apps):
    dokku, apps_names = create_apps

    # Default checks
    checks = {check.app_name: check for check in dokku.checks.list()}
    global_wait = checks[None].global_wait_to_retire
    for app_name in apps_names:
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
    dokku.checks.set(app_name=None, key="wait-to-retire", value=new_global_wait)
    dokku.checks.set(app_name=apps_names[0], key="wait-to-retire", value=wait_app_1)
    checks = {check.app_name: check for check in dokku.checks.list()}
    assert checks[None].global_wait_to_retire == new_global_wait
    assert checks[apps_names[0]].app_wait_to_retire == wait_app_1
    assert checks[apps_names[0]].global_wait_to_retire == new_global_wait
    assert checks[apps_names[0]].wait_to_retire == wait_app_1  # Custom value defined
    assert checks[apps_names[1]].app_wait_to_retire is None
    assert checks[apps_names[1]].global_wait_to_retire == new_global_wait
    assert checks[apps_names[1]].wait_to_retire == new_global_wait  # No custom value, so use the global setting

    dokku.checks.disable(apps_names[0], ["worker", "another-worker"])
    app_checks = dokku.checks.list(app_name=apps_names[0])
    assert len(app_checks) == 2  # The enabled ones won't be here, since Dokku does not provide this information
    app_checks.sort(key=lambda obj: obj.process)
    app_checks[0].app_name == apps_names[0]
    app_checks[0].process == "another-worker"
    app_checks[0].status == "disabled"
    app_checks[1].app_name == apps_names[0]
    app_checks[1].process == "worker"
    app_checks[1].status == "disabled"
    dokku.checks.enable(apps_names[0], ["another-worker"])
    app_checks = dokku.checks.list(app_name=apps_names[0])
    assert len(app_checks) == 1  # The enabled ones won't be here, since Dokku does not provide this information
    app_checks.sort(key=lambda obj: obj.process)
    app_checks[0].process == "worker"
    app_checks[0].status == "disabled"

    dokku.checks.skip(apps_names[1], ["web"])
    app_checks = dokku.checks.list(app_name=apps_names[1])
    assert len(app_checks) == 1  # The enabled ones won't be here, since Dokku does not provide this information
    app_checks[0].app_name == apps_names[1]
    app_checks[0].process == "web"
    app_checks[0].status == "skipped"
