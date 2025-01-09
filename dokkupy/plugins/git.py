from functools import lru_cache
from pathlib import Path
from typing import List, Tuple

from ..models import App, Command, Git, SSHKey
from ..utils import clean_stderr, get_stdout_rows_parser, parse_bool, parse_timestamp
from .base import DokkuPlugin


class GitPlugin(DokkuPlugin):
    """
    dokku git plugin

    EXTRA features:
    - `known_hosts` method: read known hosts file (which is populated by `git:allow-host` subcommand)

    NOT implemented subcommands:
    - `git:status`: it always return "fatal: this operation must be run in a work tree", so not useful
    """

    name = "git"
    object_class = Git

    @lru_cache
    def _get_rows_parser(self):
        return get_stdout_rows_parser(
            normalize_keys=True,
            renames={
                "git_deploy_branch": "deploy_branch",
                "git_global_deploy_branch": "global_deploy_branch",
                "git_keep_git_dir": "keep_git_path",
                "git_rev_env_var": "rev_env_var",
                "git_sha": "sha",
                "git_source_image": "source_image",
                "git_last_updated_at": "last_updated_at",
            },
            parsers={
                "keep_git_path": parse_bool,
                "last_updated_at": parse_timestamp,
            },
        )

    def report(self, app_name: str = None) -> List[Git] | Git:
        _, stdout, stderr = self._evaluate("report", params=[] if app_name is None else [app_name], full_return=True)
        stderr = clean_stderr(stderr)
        if "You haven't deployed any applications yet" in stderr:
            return []
        elif stderr:
            raise RuntimeError(f"Error executing git:report: {stderr}")
        rows_parser = self._get_rows_parser()
        return [self.object_class(**row) for row in rows_parser(stdout)]

    def from_image(
        self,
        app_name: str,
        image: str,
        build_path: str | Path | None = None,
        git_username: str = None,
        git_email: str = None,
        execute: bool = True,
    ) -> str | Command:
        params = []
        if build_path is not None:
            params.extend(["--build-dir", str(Path(build_path).absolute())])
        params.extend([app_name, image])
        if git_username is not None:
            params.append(git_username)
            if git_email is not None:
                params.append(git_email)
        elif git_email is not None:
            raise ValueError("`git_username` is required for using `git_email`")
        return self._evaluate("from-image", params=params, execute=execute)

    def initialize(self, app_name: str, execute: bool = True) -> str | Command:
        return self._evaluate("initialize", params=[app_name], execute=execute)

    def public_key(self) -> SSHKey:
        stdout = self._evaluate("public-key", execute=True)
        key = SSHKey(name="dokku-public-key", public_key=stdout.strip())
        key.calculate_fingerprint()
        return key

    def set(self, app_name: str | None, key: str, value: str | bool, execute: bool = True) -> str | Command:
        if isinstance(value, bool):
            value = str(value).lower()
        else:
            value = str(value)
        system = app_name is None
        app_parameter = app_name if not system else "--global"
        return self._evaluate("set", params=[app_parameter, key, value], execute=execute)

    def unset(self, app_name: str | None, key: str, execute: bool = True) -> str | Command:
        system = app_name is None
        app_parameter = app_name if not system else "--global"
        return self._evaluate("set", params=[app_parameter, key], execute=execute)

    def allow_host(self, host: str, execute: bool = True) -> str | Command:
        return self._evaluate("allow-host", params=[host], execute=execute)

    def known_hosts(self) -> str:
        """Read dokku's user SSH known hosts file"""
        if not self.dokku.can_execute_regular_commands:
            raise RuntimeError("Cannot execute regular commands")
        known_hosts_path = "/home/dokku/.ssh/known_hosts"
        command = Command(["touch", known_hosts_path], sudo=self.dokku.requires_sudo)  # ensure it exists
        self.dokku._execute(command)  # will execute using SSH connection, if configured to
        command = Command(["cat", known_hosts_path], sudo=self.dokku.requires_sudo)
        _, stdout, _ = self.dokku._execute(command)  # will execute using SSH connection, if configured to
        return stdout.strip()

    def _parse_generate_deploy_key(self, stdout: str) -> Tuple[str | None, str | None]:
        pubkey_str = "Your public key has been saved in "
        fingerprint_str = "The key fingerprint is:"
        last_line = fingerprint = pubkey_path = None
        for line in stdout.strip().splitlines():
            line = line.strip()
            if line.startswith(pubkey_str):
                pubkey_path = line[len(pubkey_str) :]
            elif last_line == fingerprint_str:
                fingerprint = line
            last_line = line
        return fingerprint, pubkey_path

    def generate_deploy_key(self, execute: bool = True) -> SSHKey | Command:
        result = self._evaluate("generate-deploy-key", params=[], execute=execute, full_return=True)
        if not execute:
            return result
        _, stdout, stderr = result
        if stderr:
            raise RuntimeError(f"Error while running git:generate-deploy-key: {clean_stderr(stderr)}")
        fingerprint, pubkey_path = self._parse_generate_deploy_key(stdout)
        public_key = None
        if self.dokku.can_execute_regular_commands:
            command = Command(["cat", pubkey_path], sudo=self.dokku.requires_sudo)
            _, stdout, _ = self.dokku._execute(command)  # will execute using SSH connection, if configured to
            public_key = stdout.strip()
        return SSHKey(
            name="dokku-public-key",
            fingerprint=fingerprint,
            public_key=public_key,
        )

    def dump_all(self, apps: List[App], system: bool = True) -> List[dict]:
        # TODO: implement (how?)
        return []

    def create_object(self, obj: Git, execute: bool = True) -> List[str] | List[Command]:
        # TODO: implement
        return []


# TODO: implement git:auth <host> [<username> <password>]           # Configures netrc authentication for a given git server
# TODO: implement git:from-archive [--archive-type ARCHIVE_TYPE] <app> <archive-url> [<git-username> <git-email>] # Updates an app's git repository with a given archive file
# TODO: implement git:load-image [--build-dir DIRECTORY] <app> <docker-image> [<git-username> <git-email>] # Updates an app's git repository with a docker image loaded from stdin
# TODO: implement git:sync [--build|build-if-changes] <app> <repository> [<git-ref>] # Clone or fetch an app from remote git repo
