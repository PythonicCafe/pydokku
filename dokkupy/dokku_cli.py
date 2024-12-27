from pathlib import Path

from . import ssh
from .plugins import AppsPlugin, ConfigPlugin, SSHKeysPlugin, StoragePlugin
from .utils import execute_command

# TODO: add docstrings to all the functions


class Dokku:
    """Interfaces with Dokku using the `dokku` command"""

    def __init__(
        self,
        ssh_host: str = None,
        ssh_port: int = 22,
        ssh_private_key: Path | str = None,
        ssh_user: str = "dokku",
        ssh_key_password: str = None,
    ):
        self._ssh_prefix = []
        self.__files_to_delete = []
        if ssh_host:
            self.ssh_host, self.ssh_port, self.ssh_user = ssh_host, ssh_port, ssh_user
            self.ssh_private_key = (
                Path(ssh_private_key).expanduser().absolute() if ssh_private_key is not None else None
            )
            if ssh_private_key is None:
                raise ValueError("ssh_private_key must be provided to ensure the execution is non-interactive")
            elif ssh.key_requires_password(self.ssh_private_key):
                if ssh_key_password is None:
                    raise ValueError("The SSH key password must be provided so the execution is non-interactive")
                self.ssh_private_key = ssh.key_unlock(self.ssh_private_key, ssh_key_password)
                self.__files_to_delete.append(self.ssh_private_key)
            self._ssh_prefix = ssh.command(
                user=self.ssh_user,
                host=self.ssh_host,
                port=self.ssh_port,
                private_key=self.ssh_private_key,
            )

        # Instantiate default plugins
        # TODO: autodiscover based on `DokkuPlugin` subclasses?
        available_plugins = {
            "apps": AppsPlugin,
            "config": ConfigPlugin,
            "ssh_keys": SSHKeysPlugin,
            "storage": StoragePlugin,
        }
        self.plugins = {}
        for name, klass in available_plugins.items():
            instance = klass(dokku=self)
            setattr(self, name, instance)
            self.plugins[name] = instance

    def __del__(self):
        for filename in self.__files_to_delete:
            if filename.exists():
                filename.unlink()

    def _execute(self, command: list[str], stdin: str = None, check=True, sudo=False) -> str:
        add_ssh_prefix = self._ssh_prefix and command[0] == "dokku"
        if add_ssh_prefix and sudo and self.ssh_user != "root":
            raise ValueError(
                "Executing `sudo` via SSH is not currently supported - you must log-in as root on remote machine and execute the command"
            )
        elif add_ssh_prefix:
            command = self._ssh_prefix + command[1:]
        elif sudo:
            command = ["sudo"] + command
        return execute_command(command=command, stdin=stdin, check=check)

    def version(self) -> str:
        _, stdout, _ = self._execute(["dokku", "--version"])
        return stdout.strip().split()[2]
