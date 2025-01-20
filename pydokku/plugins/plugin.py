import configparser
import re
from typing import List

from ..models import App, Command, Plugin
from .base import DokkuPlugin

REGEXP_PLUGIN_LIST = re.compile(r"^\s*([^ ]+)\s+([^ ]+)?\s*(enabled|disabled)\s+(.*)$")


def get_git_origin_url(config_data: str) -> str | None:
    parser = configparser.ConfigParser()
    parser.read_string(config_data)
    if 'remote "origin"' in parser:
        section = parser['remote "origin"']
        return section.get("url")


def parse_git_head(value: str) -> str:
    """
    >>> parse_git_head('ref: refs/heads/master')
    'master'
    >>> parse_git_head('ref: refs/heads/master\\n')
    'master'
    >>> parse_git_head('392d9e4423c52591c29f81e25242a87b1d150e4f')
    '392d9e4423c52591c29f81e25242a87b1d150e4f'
    >>> parse_git_head('392d9e4423c52591c29f81e25242a87b1d150e4f\\n')
    '392d9e4423c52591c29f81e25242a87b1d150e4f'
    """
    if value.startswith("ref: refs/heads/"):
        return value[len("ref: refs/heads/") :].strip()
    else:
        return value.strip()


class PluginPlugin(DokkuPlugin):
    """
    dokku core plugin plugin

    Subcommands NOT implemented: xxx

    EXTRA features:
    - `list` will add the actual git remote and reference reading files inside `.git` for each non-core plugin.
    """

    name = "plugin"
    object_classes = (Plugin,)
    requires = ()

    def _parse_list(self, stdout: str) -> List[Plugin]:
        result = []
        for line in stdout.strip().splitlines():
            line.strip()
            if not line:
                continue
            parsed = REGEXP_PLUGIN_LIST.findall(line)
            if not parsed:
                continue
            name, version, status, description = parsed[0]
            result.append(
                Plugin(name=name, version=version or None, enabled=status == "enabled", description=description)
            )
        return result

    def list(self) -> List[Plugin]:
        stdout = self._evaluate("list", execute=True)
        plugins = self._parse_list(stdout)
        if self.dokku.can_execute_regular_commands:
            for plugin in plugins:
                if plugin.is_core:
                    continue
                cmd = Command(["cat", f"/var/lib/dokku/plugins/available/{plugin.name}/.git/HEAD"], check=False)
                returncode_head, stdout_head, stderr_head = self.dokku._execute(cmd)
                if returncode_head == 0 and not stderr_head:
                    plugin.git_reference = parse_git_head(stdout_head)
                cmd = Command(["cat", f"/var/lib/dokku/plugins/available/{plugin.name}/.git/config"], check=False)
                returncode_config, stdout_config, stderr_config = self.dokku._execute(cmd)
                if returncode_config == 0 and not stderr_config:
                    plugin.git_url = get_git_origin_url(stdout_config)
        return plugins

    def install(
        self,
        git_url: str | None = None,
        git_reference: str | None = None,
        name: str | None = None,
        core: bool = False,
        execute: bool = True,
    ) -> str | Command:
        if core:
            if git_url is not None or git_reference is not None or name is not None:
                raise ValueError("If `core` is `True`, then no other option should be provided")
            params = ["--core"]
        else:
            if git_url is None:
                raise ValueError("`git_url` must be provided")
            params = [git_url]
            if git_reference is not None:
                # `--committish` is required! Dokku parsing of CLI args SUCKS.
                params.extend(["--committish", git_reference])
            if name is not None:
                # `--name` is required! Dokku parsing of CLI args SUCKS.
                params.extend(["--name", name])
        return self._evaluate("install", params=params, sudo=True, execute=execute)

    def enable(self, name: str, execute: bool = True) -> str | Command:
        return self._evaluate("enable", params=[name], sudo=True, execute=execute)

    def disable(self, name: str, execute: bool = True) -> str | Command:
        return self._evaluate("disable", params=[name], sudo=True, execute=execute)

    def uninstall(self, name: str, execute: bool = True) -> str | Command:
        return self._evaluate("uninstall", params=[name], sudo=True, execute=execute)

    def update(self, name: str | None = None, git_reference: str | None = None, execute: bool = True) -> str | Command:
        params = []
        if name is not None:
            params.append(name)
        if git_reference is not None:
            params.append(git_reference)
        return self._evaluate("update", params=params, sudo=True, execute=execute)

    def install_dependencies(self, core: bool = False, execute: bool = True) -> str | Command:
        params = [] if not core else ["--core"]
        return self._evaluate("install-dependencies", params=params, sudo=True, execute=execute)

    def trigger(self, args: List[str], execute: bool = True) -> str | Command:
        return self._evaluate("trigger", params=list(args), sudo=True, execute=execute)

    def object_list(self, apps: List[App], system: bool = True) -> List[Plugin]:
        return self.list()

    def object_create(self, obj: Plugin, skip_system: bool = False, execute: bool = True) -> List[str] | List[Command]:
        if obj.is_core:
            return []
        result = []
        if obj.git_url is not None:
            result.append(
                self.install(git_url=obj.git_url, git_reference=obj.git_reference, name=obj.name, execute=execute)
            )
        if not obj.enabled:
            result.append(self.disable(obj.name, execute=execute))
        return result

    # TODO: add self.install_dependencies(core=False) in object_create_many?
