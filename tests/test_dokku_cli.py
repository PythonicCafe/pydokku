import pytest

from pydokku import ssh
from pydokku.dokku_cli import Dokku
from pydokku.models import Command
from tests.utils import requires_dokku, requires_ssh_keygen


@requires_dokku
def test_version():
    dokku = Dokku()
    version = dokku.version()
    assert isinstance(version, tuple)
    assert len(version) == 3


@requires_ssh_keygen
def test_ssh_config_errors(temp_dir):
    key_without_password_path = temp_dir / "key_without_password"
    key_with_password_path = temp_dir / "key_with_password"
    ssh_key_password = "test123"
    ssh_host = "example.net"
    ssh_user = "dokku"
    ssh_port = 22

    ssh.key_create(filename=key_without_password_path, key_type="ed25519", password=None)
    ssh.key_create(filename=key_with_password_path, key_type="ed25519", password=ssh_key_password)

    # Happy path: key without password -- won't raise exception
    Dokku(
        ssh_host=ssh_host,
        ssh_user=ssh_user,
        ssh_port=ssh_port,
        ssh_private_key=key_without_password_path,
        ssh_key_password=None,
    )

    # Happy path: key with password (and the correct one is provided) -- won't raise exception
    Dokku(
        ssh_host=ssh_host,
        ssh_user=ssh_user,
        ssh_port=ssh_port,
        ssh_private_key=key_with_password_path,
        ssh_key_password=ssh_key_password,
    )

    with pytest.raises(ValueError, match="`ssh_private_key` must be provided.*"):
        Dokku(ssh_host="example.net")

    with pytest.raises(ValueError, match="`ssh_key_password` must be provided.*"):
        Dokku(
            ssh_host=ssh_host,
            ssh_user=ssh_user,
            ssh_port=ssh_port,
            ssh_private_key=key_with_password_path,
            ssh_key_password=None,
        )

    with pytest.raises(RuntimeError, match="Error unlocking SSH key: Failed to load key .*"):
        Dokku(
            ssh_host=ssh_host,
            ssh_user=ssh_user,
            ssh_port=ssh_port,
            ssh_private_key=key_with_password_path,
            ssh_key_password="wrong-password",
        )


def test_prepare_command_with_ssh():
    ssh_host = "example.net"
    ssh_port = 22
    ssh_private_key = "/tmp/key"
    ssh_command = ["ssh", "-i", ssh_private_key, "-p", str(ssh_port)]
    test_cases = [
        {
            "ssh_user": "dokku",
            "command": Command(command=["dokku", "ps:report"], sudo=False),
            "expected_command": ssh_command + [f"dokku@{ssh_host}", "--", "ps:report"],
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
            "expected_command": ssh_command + [f"root@{ssh_host}", "--", "dokku", "ps:report"],
            "should_raise": False,
            "expected_exception_msg": None,
        },
        {
            "ssh_user": "root",
            "command": Command(command=["dokku", "ps:report"], sudo=True),
            "expected_command": ssh_command + [f"root@{ssh_host}", "--", "dokku", "ps:report"],
            "should_raise": False,
            "expected_exception_msg": None,
        },
        {
            "ssh_user": "root",
            "command": Command(command=["non-dokku", "command"], sudo=False),
            "expected_command": ssh_command + [f"root@{ssh_host}", "--", "non-dokku", "command"],
            "should_raise": False,
            "expected_exception_msg": None,
        },
        {
            "ssh_user": "root",
            "command": Command(command=["non-dokku", "command"], sudo=True),
            "expected_command": ssh_command + [f"root@{ssh_host}", "--", "non-dokku", "command"],
            "should_raise": False,
            "expected_exception_msg": None,
        },
        {
            "ssh_user": "regular",
            "command": Command(command=["dokku", "ps:report"], sudo=False),
            "expected_command": ssh_command + [f"regular@{ssh_host}", "--", "dokku", "ps:report"],
            "should_raise": False,
            "expected_exception_msg": None,
        },
        {
            "ssh_user": "regular",
            "command": Command(command=["dokku", "ps:report"], sudo=True),
            "expected_command": ssh_command + [f"regular@{ssh_host}", "--", "sudo", "dokku", "ps:report"],
            "should_raise": False,
            "expected_exception_msg": None,
        },
        {
            "ssh_user": "regular",
            "command": Command(command=["non-dokku", "command"], sudo=False),
            "expected_command": ssh_command + [f"regular@{ssh_host}", "--", "non-dokku", "command"],
            "should_raise": False,
            "expected_exception_msg": None,
        },
        {
            "ssh_user": "regular",
            "command": Command(command=["non-dokku", "command"], sudo=True),
            "expected_command": ssh_command + [f"regular@{ssh_host}", "--", "sudo", "non-dokku", "command"],
            "should_raise": False,
            "expected_exception_msg": None,
        },
    ]

    for counter, test_case in enumerate(test_cases, start=1):
        dokku = Dokku()
        # Force SSH without passing an actual key
        dokku.via_ssh = True
        dokku.ssh_user = test_case["ssh_user"]
        dokku.ssh_host = ssh_host
        dokku.ssh_port = ssh_port
        dokku.ssh_private_key = ssh_private_key
        dokku._ssh_prefix = ssh_command + [f"{dokku.ssh_user}@{ssh_host}", "--"]

        if test_case["should_raise"]:
            with pytest.raises(RuntimeError, match=test_case["expected_exception_msg"]):
                dokku._prepare_command(test_case["command"])
        else:
            result = dokku._prepare_command(test_case["command"])
            assert result == test_case["expected_command"], f"Error in test case #{counter}"


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

    for counter, test_case in enumerate(test_cases, start=1):
        dokku = Dokku()
        dokku.local_user = test_case["local_user"]
        result = dokku._prepare_command(test_case["command"])
        assert result == test_case["expected_command"], f"Error in test case #{counter}"


# TODO: create tests which actuall *execute* Dokku SSH commands (use parameterized fixtures with a conditional one
# based on env vars)
