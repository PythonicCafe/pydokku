import re

import pytest

from dokkupy.dokku_cli import Dokku
from dokkupy.models import Command
from tests.utils import requires_dokku


@requires_dokku
def test_version():
    dokku = Dokku()
    version = dokku.version()
    assert re.match(r"[0-9]+\.[0-9]+\.[0-9]+", version) is not None


# TODO: implement tests for SSH key errors on Dokku.__init__ (key without passphrase, key with no passphrase)


def test_prepare_command_with_ssh():
    ssh_host = "example.net"
    ssh_port = 22
    ssh_private_key = "/tmp/key"
    ssh_command = ["ssh", "-i", ssh_private_key, "-p", str(ssh_port)]
    test_cases = [
        {
            "ssh_user": "dokku",
            "command": Command(command=["dokku", "ps:report"], sudo=False),
            "expected_command": ssh_command + [f"dokku@{ssh_host}", "ps:report"],
            "should_raise": False,
            "expected_exception_msg": None,
        },
        {
            "ssh_user": "dokku",
            "command": Command(command=["dokku", "ps:report"], sudo=True),
            "expected_command": None,
            "should_raise": True,
            "expected_exception_msg": "Cannot execute a sudo-needing dokku command via SSH with user `dokku`",
        },
        {
            "ssh_user": "dokku",
            "command": Command(command=["non-dokku", "command"], sudo=False),
            "expected_command": None,
            "should_raise": True,
            "expected_exception_msg": "Cannot execute non-dokku command via SSH for user `dokku`",
        },
        {
            "ssh_user": "root",
            "command": Command(command=["dokku", "ps:report"], sudo=False),
            "expected_command": ssh_command + [f"root@{ssh_host}", "dokku", "ps:report"],
            "should_raise": False,
            "expected_exception_msg": None,
        },
        {
            "ssh_user": "root",
            "command": Command(command=["dokku", "ps:report"], sudo=True),
            "expected_command": ssh_command + [f"root@{ssh_host}", "dokku", "ps:report"],
            "should_raise": False,
            "expected_exception_msg": None,
        },
        {
            "ssh_user": "root",
            "command": Command(command=["non-dokku", "command"], sudo=False),
            "expected_command": ssh_command + [f"root@{ssh_host}", "non-dokku", "command"],
            "should_raise": False,
            "expected_exception_msg": None,
        },
        {
            "ssh_user": "root",
            "command": Command(command=["non-dokku", "command"], sudo=True),
            "expected_command": ssh_command + [f"root@{ssh_host}", "non-dokku", "command"],
            "should_raise": False,
            "expected_exception_msg": None,
        },
        {
            "ssh_user": "regular",
            "command": Command(command=["dokku", "ps:report"], sudo=False),
            "expected_command": ssh_command + [f"regular@{ssh_host}", "dokku", "ps:report"],
            "should_raise": False,
            "expected_exception_msg": None,
        },
        {
            "ssh_user": "regular",
            "command": Command(command=["dokku", "ps:report"], sudo=True),
            "expected_command": ssh_command + [f"regular@{ssh_host}", "sudo", "dokku", "ps:report"],
            "should_raise": False,
            "expected_exception_msg": None,
        },
        {
            "ssh_user": "regular",
            "command": Command(command=["non-dokku", "command"], sudo=False),
            "expected_command": ssh_command + [f"regular@{ssh_host}", "non-dokku", "command"],
            "should_raise": False,
            "expected_exception_msg": None,
        },
        {
            "ssh_user": "regular",
            "command": Command(command=["non-dokku", "command"], sudo=True),
            "expected_command": ssh_command + [f"regular@{ssh_host}", "sudo", "non-dokku", "command"],
            "should_raise": False,
            "expected_exception_msg": None,
        },
    ]

    for test_case in test_cases:
        dokku = Dokku()
        # Force SSH without passing an actual key
        dokku.ssh_user = test_case["ssh_user"]
        dokku.ssh_host = ssh_host
        dokku.ssh_port = ssh_port
        dokku.ssh_private_key = ssh_private_key
        dokku._ssh_prefix = ssh_command + [f"{dokku.ssh_user}@{ssh_host}"]

        if test_case["should_raise"]:
            with pytest.raises(RuntimeError, match=test_case["expected_exception_msg"]):
                dokku._prepare_command(test_case["command"])
        else:
            result = dokku._prepare_command(test_case["command"])
            assert result == test_case["expected_command"]


def test_prepare_command_local():
    test_cases = [
        {
            "local_user": "root",
            "command": Command(command=["dokku", "ps:report"], sudo=False),
            "expected_command": ["dokku", "ps:report"],
        },
        {
            "local_user": "root",
            "command": Command(command=["dokku", "ps:report"], sudo=True),
            "expected_command": ["dokku", "ps:report"],
        },
        {
            "local_user": "root",
            "command": Command(command=["non-dokku", "command"], sudo=False),
            "expected_command": ["non-dokku", "command"],
        },
        {
            "local_user": "root",
            "command": Command(command=["non-dokku", "command"], sudo=True),
            "expected_command": ["non-dokku", "command"],
        },
        {
            "local_user": "regular",
            "command": Command(command=["dokku", "ps:report"], sudo=False),
            "expected_command": ["dokku", "ps:report"],
        },
        {
            "local_user": "regular",
            "command": Command(command=["dokku", "ps:report"], sudo=True),
            "expected_command": ["sudo", "dokku", "ps:report"],
        },
        {
            "local_user": "regular",
            "command": Command(command=["non-dokku", "command"], sudo=False),
            "expected_command": ["non-dokku", "command"],
        },
        {
            "local_user": "regular",
            "command": Command(command=["non-dokku", "command"], sudo=True),
            "expected_command": ["sudo", "non-dokku", "command"],
        },
    ]

    for test_case in test_cases:
        dokku = Dokku()
        dokku._local_user = test_case["local_user"]
        result = dokku._prepare_command(test_case["command"])
        assert result == test_case["expected_command"]
