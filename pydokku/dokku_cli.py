import getpass
import hashlib
import tempfile
from functools import cached_property
from pathlib import Path

from . import ssh
from .models import Command
from .utils import execute_command

# TODO: add docstrings to all the functions


class Dokku:
    """Interfaces with Dokku using the `dokku` command"""

    def __init__(
        self,
        ssh_host: str | None = None,
        ssh_port: int = 22,
        ssh_private_key: Path | str | None = None,
        ssh_user: str = "dokku",
        ssh_key_password: str | None = None,
        ssh_mux: bool = True,
    ):
        self._ssh_prefix = []
        self.__files_to_delete = []
        self.local_user = getpass.getuser()
        self.ssh_host, self.ssh_port, self.ssh_user = None, None, None
        if ssh_host:
            self.ssh_host, self.ssh_port, self.ssh_user = ssh_host, ssh_port, ssh_user
            self.ssh_private_key = (
                Path(ssh_private_key).expanduser().absolute() if ssh_private_key is not None else None
            )
            if ssh_private_key is None:
                raise ValueError("`ssh_private_key` must be provided to ensure the execution is non-interactive")
            elif ssh.key_requires_password(self.ssh_private_key):
                if ssh_key_password is None:
                    raise ValueError("`ssh_key_password` must be provided so the execution is non-interactive")
                self.ssh_private_key = ssh.key_unlock(self.ssh_private_key, ssh_key_password)
                self.__files_to_delete.append(self.ssh_private_key)
            mux_filename = None
            if ssh_mux:
                # TODO: create temp file hash (ssh host, ssh port, ssh user, ssh key path) and add to _files_to_delete
                hash_key = [self.ssh_host, str(self.ssh_port), self.ssh_user, str(self.ssh_private_key)]
                mux_hash = hashlib.sha1("|".join(hash_key).encode("utf-8")).hexdigest()
                mux_filename = Path(tempfile.NamedTemporaryFile(delete=False, prefix=f"pydokku-ssh-{mux_hash}-").name)
                self.__files_to_delete.append(mux_filename)
            self._ssh_prefix = ssh.command(
                user=self.ssh_user,
                host=self.ssh_host,
                port=self.ssh_port,
                private_key=self.ssh_private_key,
                mux=ssh_mux,
                mux_filename=mux_filename,
            ) + ["--"]

        # Instantiate default plugins
        # TODO: autodiscover based on `DokkuPlugin` subclasses?
        from .plugins import (  # noqa
            AppsPlugin,
            ChecksPlugin,
            ConfigPlugin,
            DomainsPlugin,
            GitPlugin,
            PortsPlugin,
            ProxyPlugin,
            PsPlugin,
            SSHKeysPlugin,
            StoragePlugin,
        )

        available_plugins = {
            "apps": AppsPlugin,
            "checks": ChecksPlugin,
            "config": ConfigPlugin,
            "domains": DomainsPlugin,
            "git": GitPlugin,
            "ports": PortsPlugin,
            "proxy": ProxyPlugin,
            "ps": PsPlugin,
            "ssh_keys": SSHKeysPlugin,
            "storage": StoragePlugin,
        }
        self.plugins = {}
        for name, klass in available_plugins.items():
            instance = klass(dokku=self)
            setattr(self, name, instance)
            self.plugins[name] = instance

    @cached_property
    def via_ssh(self):
        return len(self._ssh_prefix) > 0

    @cached_property
    def requires_sudo(self):
        """Check whether the current user requires `sudo` to execute a command locally or remotely"""
        remote_skip_sudo = ("root",)
        local_skip_sudo = ("dokku", "root")
        return (self.via_ssh and self.ssh_user not in remote_skip_sudo) or (
            not self.via_ssh and self.local_user not in local_skip_sudo
        )

    @cached_property
    def can_execute_regular_commands(self):
        # If running locally, we assume the current user has permissions to execute non-Dokku commands. If running via
        # SSH, the `dokku` user won't have shell access, so we assume that only if it's running as root or as another
        # sudoer we can actually execute non-Dokku commands.
        return not self.via_ssh or self.ssh_user != "dokku"

    def __del__(self):
        if hasattr(self, "_Dokku__files_to_delete"):
            for filename in self.__files_to_delete:
                if filename.exists():
                    filename.unlink()

    def _prepare_command(self, command: Command) -> tuple[str]:
        """Prepare the final command to be executed, considering sudo, local/remote user and the command itself"""
        cmd = list(command.command)
        use_sudo = command.sudo
        is_dokku_command = cmd[0] == "dokku"

        if self.via_ssh:  # May consider: self.ssh_user, use_sudo, is_dokku_command. Don't care: self.local_user
            if self.ssh_user == "dokku":
                # If running via SSH and the remote user is `dokku`, the only commands we can execute are Dokku
                # commands
                if not is_dokku_command:
                    raise RuntimeError("Cannot execute non-dokku command via SSH for user `dokku`")
                elif use_sudo:
                    raise RuntimeError("Cannot execute a sudo-needing dokku command via SSH with user `dokku`")
                else:
                    cmd = cmd[1:]  # The `dokku` command is not passed via SSH
            elif self.ssh_user == "root":
                use_sudo = False  # If running via SSH and the remote user is `root`, `sudo` is not needed
        else:  # May consider: self.local_user, use_sudo, is_dokku_command. Don't care: self.ssh_user
            if self.local_user == "root":
                use_sudo = False  # If executing locally and the local user is `root`, `sudo` is not needed
        return self._ssh_prefix + (["sudo"] if use_sudo else []) + cmd

    def _execute(self, command: Command) -> tuple[int, str, str]:
        cmd = self._prepare_command(command)
        # TODO: may add a debugging log call here with the full command to be executed
        return execute_command(command=cmd, stdin=command.stdin, check=command.check)

    def version(self) -> str:
        _, stdout, _ = self._execute(Command(["dokku", "version"]))
        return stdout.strip().split()[2]
