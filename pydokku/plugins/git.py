import netrc
import tempfile
from functools import lru_cache
from pathlib import Path
from typing import List, Tuple, Union

from ..models import App, Auth, Command, Git, SSHKey
from ..utils import clean_stderr, get_stdout_rows_parser, parse_bool, parse_timestamp
from .base import DokkuPlugin


def parse_netrc_file(contents: str) -> List[Auth]:
    """Parse contents of a `~/.netrc` file and return the important data to Dokku (hostname, username and password)"""
    # netrc Python library requires a filename to parse, so we need to create a file and put the contents there
    with tempfile.NamedTemporaryFile() as temp:
        with open(temp.name, mode="w") as fobj:
            fobj.write(contents)
        data = netrc.netrc(temp.name)
    return [
        Auth(hostname=hostname, username=host_data[0], password=host_data[2])
        for hostname, host_data in data.hosts.items()
    ]


class GitPlugin(DokkuPlugin):
    """
    dokku core git plugin

    WARNING: if you have a deploy key (created via `git:generate-deploy-key`) it WON'T be exported by this plugin,
    since it would require reading the PRIVATE key. The PUBLIC key is exported since it can be useful.

    EXTRA features:
    - `host_list` method: read known hosts file (which is populated by `git:allow-host` subcommand)
    - `auth_list` method: read netrc file (which is populated by `git:auth` subcommand)

    Subcommands NOT implemented:
    - `git:status`: it always return "fatal: this operation must be run in a work tree", so not useful
    - `git:load-image`: huge stdin input is currently not a priority
    - `git:set`: was split in `set()` and `unset()` methods
    """

    name = "git"
    subcommand = "git"
    plugin_name = "git"
    object_classes = (SSHKey, Auth, Git)
    requires = ("apps",)

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

    def list(self, app_name: Union[str, None] = None) -> Union[List[Git], Git]:
        # Dokku won't return error in this `report` command, but `check=False` is used in all `:report/list` because of
        # this inconsistent behavior <https://github.com/dokku/dokku/issues/7454>
        system = app_name is None
        _, stdout, stderr = self._evaluate(
            "report",
            params=[] if system else [app_name],
            check=False,
            full_return=True,
            execute=True,
        )
        stderr = clean_stderr(stderr)
        if "You haven't deployed any applications yet" in stderr:
            return []
        elif stderr:
            raise RuntimeError(f"Error executing git:report: {stderr}")
        rows_parser = self._get_rows_parser()
        return [Git(**row) for row in rows_parser(stdout)]

    def from_archive(
        self,
        app_name: str,
        archive_url: str,
        git_username: Union[str, None] = None,
        git_email: Union[str, None] = None,
        execute: bool = True,
    ) -> Union[str, Command]:
        params = [app_name, archive_url]
        if git_username is not None:
            params.append(git_username)
            if git_email is not None:
                params.append(git_email)
        elif git_email is not None:
            raise ValueError("`git_username` is required for using `git_email`")
        return self._evaluate("from-archive", params=params, execute=execute)

    def from_image(
        self,
        app_name: str,
        image: str,
        build_path: Union[str, Path, None] = None,
        git_username: Union[str, None] = None,
        git_email: Union[str, None] = None,
        execute: bool = True,
    ) -> Union[str, Command]:
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

    def initialize(self, app_name: str, execute: bool = True) -> Union[str, Command]:
        return self._evaluate("initialize", params=[app_name], execute=execute)

    def public_key(self) -> Union[SSHKey, None]:
        """Read dokku public SSH key (deploy key)"""
        _, stdout, stderr = self._evaluate("public-key", execute=True, check=False, full_return=True)
        if "There is no deploy key associated" in stderr:
            return None
        key = SSHKey(name="dokku-public-key", public_key=stdout.strip())
        key.calculate_fingerprint()
        return key

    def set(
        self, app_name: Union[str, None], key: str, value: Union[str, bool], execute: bool = True
    ) -> Union[str, Command]:
        if isinstance(value, bool):
            value = str(value).lower()
        else:
            value = str(value)
        system = app_name is None
        app_parameter = app_name if not system else "--global"
        return self._evaluate("set", params=[app_parameter, key, value], execute=execute)

    def unset(self, app_name: Union[str, None], key: str, execute: bool = True) -> Union[str, Command]:
        system = app_name is None
        app_parameter = app_name if not system else "--global"
        return self._evaluate("set", params=[app_parameter, key], execute=execute)

    def host_add(self, hostname: str, execute: bool = True) -> Union[str, Command]:
        """Add `hostname` to dokku's user known hosts (calls `dokku git:allow-host`, but with a better name)"""
        return self._evaluate("allow-host", params=[hostname], execute=execute)

    def host_list(self) -> List[SSHKey]:
        """Read dokku's user SSH known hosts file and parse it so we have all host's public keys

        The actual hostname will be in SSHKey's name field
        """
        if not self.dokku.can_execute_regular_commands:
            raise RuntimeError("Cannot execute regular commands")
        known_hosts_path = "/home/dokku/.ssh/known_hosts"
        command = Command(["touch", known_hosts_path], sudo=self.dokku.requires_sudo)  # ensure it exists
        self.dokku._execute(command)  # will execute using SSH connection, if configured to
        command = Command(["chmod", "600", known_hosts_path], sudo=self.dokku.requires_sudo)  # fix permissions
        self.dokku._execute(command)  # will execute using SSH connection, if configured to
        command = Command(["cat", known_hosts_path], sudo=self.dokku.requires_sudo)
        _, stdout, _ = self.dokku._execute(command)  # will execute using SSH connection, if configured to
        result = []
        for line in stdout.strip().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            hostname, public_key = line.split(" ", maxsplit=1)
            key = SSHKey(name=hostname, public_key=public_key)
            key.calculate_fingerprint()
            result.append(key)
        return result

    def _parse_generate_deploy_key(self, stdout: str) -> Tuple[Union[str, None], Union[str, None]]:
        pubkey_str = "Your public key has been saved in "
        fingerprint_str = "The key fingerprint is:"
        last_line = fingerprint = pubkey_path = None
        for line in stdout.strip().splitlines():
            line = line.strip()
            if line.startswith(pubkey_str):
                pubkey_path = line[len(pubkey_str) :]
            elif last_line == fingerprint_str:
                fingerprint = line.split()[0]
            last_line = line
        return fingerprint, pubkey_path

    def generate_deploy_key(self, execute: bool = True) -> Union[SSHKey, Command]:
        result = self._evaluate("generate-deploy-key", execute=execute, full_return=True)
        if not execute:
            return result
        _, stdout, stderr = result
        error_str = "A deploy key already exists for this host"
        if error_str in stdout or stderr:
            # YES, Dokku prints this error in stdout, not stderr. No consistency with other commands.
            error = clean_stderr(stderr or stdout)
            raise RuntimeError(f"Error while running git:generate-deploy-key: {error}")
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

    def auth_add(self, hostname: str, username: str, password: str, execute: bool = True) -> Union[str, Command]:
        return self._evaluate("auth", params=[hostname, username, password], execute=execute)

    def auth_remove(self, hostname: str, execute: bool = True) -> Union[str, Command]:
        return self._evaluate("auth", params=[hostname], execute=execute)

    def auth_list(self) -> List[Auth]:
        if not self.dokku.can_execute_regular_commands:
            raise RuntimeError("Cannot read auth list (cannot execute regular commands)")
        netrc_path = "/home/dokku/.netrc"
        command = Command(["touch", netrc_path], sudo=self.dokku.requires_sudo)  # ensure it exists
        self.dokku._execute(command)  # will execute using SSH connection, if configured to
        command = Command(["chmod", "600", netrc_path], sudo=self.dokku.requires_sudo)  # fix permissions
        self.dokku._execute(command)  # will execute using SSH connection, if configured to
        command = Command(["cat", netrc_path], sudo=self.dokku.requires_sudo)
        _, stdout, _ = self.dokku._execute(command)  # will execute using SSH connection, if configured to
        if not stdout.strip():
            return []
        return parse_netrc_file(stdout)

    def sync(
        self,
        app_name: str,
        repository_url: str,
        git_reference: Union[str, None] = None,
        build: bool = False,
        build_if_changes: bool = False,
        execute: bool = True,
    ) -> Union[str, Command]:
        if build and build_if_changes:
            build = False
        params = []
        if build:
            params.append("--build")
        elif build_if_changes:
            params.append("--build-if-changes")
        params.extend([app_name, repository_url])
        if git_reference is not None:
            params.append(git_reference)
        return self._evaluate("sync", params=params, execute=execute)

    def object_list(self, apps: List[App], system: bool = True) -> List[Union[Git, SSHKey, Auth]]:
        result = []
        if self.dokku.can_execute_regular_commands:
            result.extend(self.host_list())
            result.extend(self.auth_list())
        key = self.public_key()
        if key is not None:
            result.append(key)
        result.extend(self.list())
        return result

    def object_create(
        self, obj: Union[Git, SSHKey, Auth], skip_system: bool = False, execute: bool = True
    ) -> Union[List[str], List[Command]]:
        result = []
        if isinstance(obj, Auth):
            result.append(
                self.auth_add(hostname=obj.hostname, username=obj.username, password=obj.password, execute=execute)
            )
        elif isinstance(obj, SSHKey):
            if obj.name != "dokku-public-key":
                for host_or_ip in obj.name.split(","):
                    result.append(self.host_add(hostname=host_or_ip, execute=execute))
        elif isinstance(obj, Git):
            if obj.global_deploy_branch and not skip_system:
                result.append(
                    self.set(app_name=None, key="deploy-branch", value=obj.global_deploy_branch, execute=execute)
                )
            if obj.deploy_branch:
                result.append(
                    self.set(app_name=obj.app_name, key="deploy-branch", value=obj.deploy_branch, execute=execute)
                )
            result.append(self.set(app_name=obj.app_name, key="keep-git-dir", value=obj.keep_git_path, execute=execute))
            if obj.rev_env_var:
                result.append(
                    self.set(app_name=obj.app_name, key="rev-env-var", value=obj.rev_env_var, execute=execute)
                )
            if obj.source_image:
                if obj.last_updated_at is None:  # App was not deployed yet, so just set image name
                    result.append(
                        self.set(app_name=obj.app_name, key="source-image", value=obj.source_image, execute=execute)
                    )
                else:
                    result.append(self.from_image(app_name=obj.app_name, image=obj.source_image, execute=execute))
        return result
