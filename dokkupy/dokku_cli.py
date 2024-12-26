import subprocess
from pathlib import Path

from . import ssh
from .plugins import AppsPlugin, ConfigPlugin, SSHKeysPlugin, StoragePlugin


# TODO: transform each plugin into an attribute of Dokku class, so specific commands will be inside the plugin object
# TODO: add docstrings in all the functions
# TODO: implement CLI `dump` command (inspect the whole system and export a JSON). add options for filters
# TODO: implement CLI `commands` command (read a JSON from `dump` and print commands to execute to reproduce)


def execute_command(command: list[str], stdin: str = None, check=True) -> str:
    process = subprocess.Popen(
        command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8",
    )
    if stdin is not None:
        process.stdin.write(stdin)
        process.stdin.close()
    result = process.wait()
    if check:
        assert result == 0, (
            f"Command {command} exited with status {result} "
            f"(stdout: {repr(process.stdout.read())}, stderr: {repr(process.stderr.read())})"
        )
    return result, process.stdout.read(), process.stderr.read()


class Dokku:
    """Interfaces with Dokku using the `dokku` command"""

    def __init__(self,
        ssh_host: str = None, ssh_port: int = 22, ssh_private_key: Path | str = None, ssh_user: str = "dokku",
        ssh_key_password: str = None,
    ):
        self._cmd_prefix = []
        self.__files_to_delete = []
        if ssh_host:
            self.ssh_host, self.ssh_port, self.ssh_user = ssh_host, ssh_port, ssh_user
            self.ssh_private_key = Path(ssh_private_key).expanduser().absolute() if ssh_private_key is not None else None
            if ssh_private_key is None:
                raise ValueError(f"ssh_private_key must be provided to ensure the execution is non-interactive")
            elif ssh.key_requires_password(self.ssh_private_key):
                if ssh_key_password is None:
                    raise ValueError(f"The SSH key password must be provided so the execution is non-interactive")
                self.ssh_private_key = ssh.key_unlock(self.ssh_private_key, ssh_key_password)
                self.__files_to_delete.append(self.ssh_private_key)
            self._cmd_prefix = [
                "ssh",
                "-i",
                str(self.ssh_private_key),
                "-p",
                str(self.ssh_port),
                f"{self.ssh_user}@{self.ssh_host}",
            ]

        # Instantiate default plugins
        self.apps = AppsPlugin(dokku=self)
        self.config = ConfigPlugin(dokku=self)
        self.ssh_keys = SSHKeysPlugin(dokku=self)
        self.storage = StoragePlugin(dokku=self)
        # TODO: autodiscover based on `DokkuPlugin` subclasses?

    def __del__(self):
        for filename in self.__files_to_delete:
            if filename.exists():
                filename.unlink()

    def _execute(self, command: list[str], stdin: str = None, check=True) -> str:
        if self._cmd_prefix and command[0] == "dokku":
            command = self._cmd_prefix + command[1:]
        return execute_command(command=command, stdin=stdin, check=check)

    def version(self) -> str:
        _, stdout, _ = self._execute(["dokku", "--version"])
        return stdout.strip().split()[2]
