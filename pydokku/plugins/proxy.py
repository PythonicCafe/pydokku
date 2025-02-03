from functools import lru_cache
from typing import List, Union

from ..models import App, Command, Proxy
from ..utils import clean_stderr, get_stdout_rows_parser, parse_bool
from .base import DokkuPlugin


class ProxyPlugin(DokkuPlugin):
    """
    dokku core proxy plugin

    Subcommands NOT implemented: none.

    Extra features: none.
    """

    name = subcommand = plugin_name = "proxy"
    object_classes = (Proxy,)
    requires = ("apps",)
    requires_extra_commands = False

    @lru_cache
    def _get_rows_parser(self):
        return get_stdout_rows_parser(
            normalize_keys=True,
            remove_prefix="proxy_",
            discards=["computed_type"],
            renames={"type": "app_type"},
            parsers={"enabled": parse_bool},
        )

    def list(self, app_name: Union[str, None] = None) -> Union[List[Proxy]]:
        """Get the list of proxy configs for each app. If `app_name` is `None`, the report includes all apps"""
        # Dokku WILL return error in this `report` command, so `check=False` is used in all `:report/list` because of
        # this inconsistent behavior <https://github.com/dokku/dokku/issues/7454>
        system = app_name is None
        _, stdout, stderr = self._evaluate(
            "report", params=[] if system else [app_name], check=False, full_return=True, execute=True
        )
        stderr = clean_stderr(stderr)
        if "You haven't deployed any applications yet" in stderr:
            return []
        elif stderr:
            raise RuntimeError(f"Error executing proxy:report: {stderr}")
        rows_parser = self._get_rows_parser()
        parsed_rows = rows_parser(stdout)
        if self.dokku.version() < (0, 31, 0):
            for row in parsed_rows:
                del row["port_map"]
        return [Proxy(**row) for row in parsed_rows]

    def enable(self, app_name: str, execute: bool = True) -> Union[str, Command]:
        return self._evaluate("enable", params=[app_name], execute=execute)

    def disable(self, app_name: str, execute: bool = True) -> Union[str, Command]:
        return self._evaluate("disable", params=[app_name], execute=execute)

    def set(self, app_name: Union[str, None], proxy_type: str, execute: bool = True) -> Union[str, Command]:
        system = app_name is None
        app_parameter = app_name if not system else "--global"
        return self._evaluate("set", params=[app_parameter, proxy_type], execute=execute)

    def clear_config(self, app_name: Union[str, None], execute: bool = True) -> Union[str, Command]:
        system = app_name is None
        app_parameter = app_name if not system else "--all"
        return self._evaluate("clear-config", params=[app_parameter], execute=execute)

    def build_config(
        self, app_name: Union[str, None], parallel: int = None, execute: bool = True
    ) -> Union[str, Command]:
        system = app_name is None
        app_parameter = app_name if not system else "--all"
        params = []
        if parallel is not None:
            params.extend(["--parallel", str(parallel)])
        params.append(app_parameter)
        return self._evaluate("build-config", params=params, execute=execute)

    def object_list(self, apps: List[App], system: bool = True) -> List[Proxy]:
        apps_names = [app.name for app in apps]
        return [proxy for proxy in self.list() if proxy.app_name in apps_names]

    def object_create(
        self, obj: Proxy, skip_system: bool = False, execute: bool = True
    ) -> Union[List[str], List[Command]]:
        app_name = obj.app_name
        result = []
        if not skip_system:
            result.append(self.set(app_name=None, proxy_type=obj.global_type, execute=execute))
        if obj.app_type:
            result.append(self.set(app_name=app_name, proxy_type=obj.app_type, execute=execute))
        if obj.enabled:
            result.append(self.enable(app_name=app_name, execute=execute))
        else:
            result.append(self.disable(app_name=app_name, execute=execute))
        result.append(self.build_config(app_name=app_name, execute=execute))
        return result
