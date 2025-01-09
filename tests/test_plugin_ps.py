from pathlib import Path

import pytest

from dokkupy import Dokku
from dokkupy.models import Process, ProcessInfo


def test_object_class():
    dokku = Dokku()
    assert dokku.ps.object_class is ProcessInfo


def test_start_command():
    app_name = "test-app-1"
    dokku = Dokku()
    command = dokku.ps.start(app_name=app_name, execute=False)
    assert command.command == ["dokku", "ps:start", app_name]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False

    command = dokku.ps.start(app_name=None, execute=False)
    assert command.command == ["dokku", "ps:start", "--all"]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False

    command = dokku.ps.start(app_name=None, parallel=4, execute=False)
    assert command.command == ["dokku", "ps:start", "--parallel", "4", "--all"]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False


def test_stop_command():
    app_name = "test-app-1"
    dokku = Dokku()
    command = dokku.ps.stop(app_name=app_name, execute=False)
    assert command.command == ["dokku", "ps:stop", app_name]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False

    command = dokku.ps.stop(app_name=None, execute=False)
    assert command.command == ["dokku", "ps:stop", "--all"]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False

    command = dokku.ps.stop(app_name=None, parallel=4, execute=False)
    assert command.command == ["dokku", "ps:stop", "--parallel", "4", "--all"]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False


def test_restart_command():
    app_name = "test-app-1"
    dokku = Dokku()
    command = dokku.ps.restart(app_name=app_name, execute=False)
    assert command.command == ["dokku", "ps:restart", app_name]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False

    command = dokku.ps.restart(app_name=None, execute=False)
    assert command.command == ["dokku", "ps:restart", "--all"]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False

    command = dokku.ps.restart(app_name=None, parallel=4, execute=False)
    assert command.command == ["dokku", "ps:restart", "--parallel", "4", "--all"]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False

    with pytest.raises(ValueError, match="Cannot restart a specific process type for all apps"):
        dokku.ps.restart(app_name=None, process="worker", parallel=4, execute=False)

    command = dokku.ps.restart(app_name=app_name, process="worker", parallel=2, execute=False)
    assert command.command == ["dokku", "ps:restart", "--parallel", "2", app_name, "worker"]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False


def test_rebuild_command():
    app_name = "test-app-1"
    dokku = Dokku()
    command = dokku.ps.rebuild(app_name=app_name, execute=False)
    assert command.command == ["dokku", "ps:rebuild", app_name]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False

    command = dokku.ps.rebuild(app_name=None, execute=False)
    assert command.command == ["dokku", "ps:rebuild", "--all"]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False

    command = dokku.ps.rebuild(app_name=None, parallel=4, execute=False)
    assert command.command == ["dokku", "ps:rebuild", "--parallel", "4", "--all"]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False


def test_restore_command():
    app_name = "test-app-1"
    dokku = Dokku()
    command = dokku.ps.restore(app_name=app_name, execute=False)
    assert command.command == ["dokku", "ps:restore", app_name]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False

    command = dokku.ps.restore(app_name=None, execute=False)
    assert command.command == ["dokku", "ps:restore", "--all"]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False

    command = dokku.ps.restore(app_name=None, parallel=4, execute=False)
    assert command.command == ["dokku", "ps:restore", "--parallel", "4", "--all"]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False


def test_set_command():
    dokku = Dokku()
    app_name = "test-app-1"
    new_path = "Procfile.dokku"
    new_restart_policy = "unless-stopped"
    command = dokku.ps.set(app_name, key="procfile-path", value=new_path, execute=False)
    assert command.command == ["dokku", "ps:set", app_name, "procfile-path", new_path]
    command = dokku.ps.set(app_name, key="restart-policy", value=new_restart_policy, execute=False)
    assert command.command == ["dokku", "ps:set", app_name, "restart-policy", new_restart_policy]


def test_unset_command():
    dokku = Dokku()
    app_name = "test-app-1"
    command = dokku.ps.unset(app_name, key="procfile-path", execute=False)
    assert command.command == ["dokku", "ps:set", app_name, "procfile-path"]
    command = dokku.ps.unset(app_name, key="restart-policy", execute=False)
    assert command.command == ["dokku", "ps:set", app_name, "restart-policy"]


def test_parse_scale():
    stdout = """
        -----> Scaling for test-app-9
        proctype: qty
        --------: ---
        another-worker: 1
        web:  2
        worker: 3
    """
    expected = {
        "another-worker": 1,
        "web": 2,
        "worker": 3,
    }
    dokku = Dokku()
    result = dokku.ps._parse_scale(stdout)
    assert result == expected


def test_set_scale_command():
    app_name = "test-app-3"
    ps = {"web": 3, "worker": 2}
    dokku = Dokku()
    command = dokku.ps.set_scale(app_name=app_name, process_counts=ps, skip_deploy=True, execute=False)
    assert command.command == ["dokku", "ps:scale", "--skip-deploy", app_name, "web=3", "worker=2"]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False


def test_parse_report():
    stdout = """
        =====> some-app ps information
            Deployed:                      true
            Processes:                     2
            Ps can scale:                  true
            Ps computed procfile path:     Procfile
            Ps global procfile path:       Procfile
            Ps procfile path:
            Ps restart policy:             on-failure:10
            Restore:                       true
            Running:                       true
            Status web 1:                  running (CID: c6a5533b5f9)
            Status worker 1:               running (CID: 9222e65ea5d)
        =====> test-app-9 ps information
            Deployed:                      true
            Processes:                     2
            Ps can scale:                  true
            Ps computed procfile path:     Procfile
            Ps global procfile path:       Procfile
            Ps procfile path:
            Ps restart policy:             on-failure:10
            Restore:                       true
            Running:                       true
            Status web 1:                  running (CID: 704f8260c68)
            Status web 2:                  running (CID: 5c174a30013)
        =====> test-app-5 ps information
            Deployed:                      false
            Processes:                     0
            Ps can scale:                  true
            Ps computed procfile path:     Procfile
            Ps global procfile path:       Procfile
            Ps procfile path:
            Ps restart policy:             on-failure:10
            Restore:                       true
            Running:                       false
    """
    dokku = Dokku()
    rows_parser = dokku.ps._get_rows_parser()
    result = rows_parser(stdout)
    expected = [
        {
            "app_name": "some-app",
            "deployed": True,
            "can_scale": True,
            "global_procfile_path": Path("Procfile"),
            "app_procfile_path": None,
            "restart_policy": "on-failure:10",
            "restore": True,
            "running": True,
            "Status web 1": "running (CID: c6a5533b5f9)",
            "Status worker 1": "running (CID: 9222e65ea5d)",
        },
        {
            "app_name": "test-app-9",
            "deployed": True,
            "can_scale": True,
            "global_procfile_path": Path("Procfile"),
            "app_procfile_path": None,
            "restart_policy": "on-failure:10",
            "restore": True,
            "running": True,
            "Status web 1": "running (CID: 704f8260c68)",
            "Status web 2": "running (CID: 5c174a30013)",
        },
        {
            "app_name": "test-app-5",
            "deployed": False,
            "can_scale": True,
            "global_procfile_path": Path("Procfile"),
            "app_procfile_path": None,
            "restart_policy": "on-failure:10",
            "restore": True,
            "running": False,
        },
    ]
    assert result == expected


def test_convert_rows():
    input_rows = [
        {
            "app_name": "some-app",
            "deployed": True,
            "can_scale": True,
            "global_procfile_path": Path("Procfile"),
            "app_procfile_path": None,
            "restart_policy": "on-failure:10",
            "restore": True,
            "running": True,
            "Status web 1": "running (CID: c6a5533b5f9)",
            "Status worker 1": "running (CID: 9222e65ea5d)",
        },
        {
            "app_name": "test-app-9",
            "deployed": True,
            "can_scale": True,
            "global_procfile_path": Path("Procfile"),
            "app_procfile_path": None,
            "restart_policy": "on-failure:10",
            "restore": True,
            "running": True,
            "Status web 1": "running (CID: 704f8260c68)",
            "Status web 2": "running (CID: 5c174a30013)",
        },
        {
            "app_name": "test-app-5",
            "deployed": False,
            "can_scale": True,
            "global_procfile_path": Path("Procfile"),
            "app_procfile_path": None,
            "restart_policy": "on-failure:10",
            "restore": True,
            "running": False,
        },
    ]
    all_processes = [
        ProcessInfo(
            app_name="some-app",
            deployed=True,
            can_scale=True,
            global_procfile_path=Path("Procfile"),
            app_procfile_path=None,
            restart_policy="on-failure:10",
            restore=True,
            running=True,
            processes=[
                Process(
                    type="web",
                    id=1,
                    status="running",
                    container_id="c6a5533b5f9",
                ),
                Process(
                    type="worker",
                    id=1,
                    status="running",
                    container_id="9222e65ea5d",
                ),
            ],
        ),
        ProcessInfo(
            app_name="test-app-9",
            deployed=True,
            can_scale=True,
            global_procfile_path=Path("Procfile"),
            app_procfile_path=None,
            restart_policy="on-failure:10",
            restore=True,
            running=True,
            processes=[
                Process(
                    type="web",
                    id=1,
                    status="running",
                    container_id="704f8260c68",
                ),
                Process(
                    type="web",
                    id=2,
                    status="running",
                    container_id="5c174a30013",
                ),
            ],
        ),
        ProcessInfo(
            app_name="test-app-5",
            deployed=False,
            can_scale=True,
            global_procfile_path=Path("Procfile"),
            app_procfile_path=None,
            restart_policy="on-failure:10",
            restore=True,
            running=False,
            processes=[],
        ),
    ]
    dokku = Dokku()
    result = dokku.ps._convert_rows(input_rows)
    assert result == all_processes
