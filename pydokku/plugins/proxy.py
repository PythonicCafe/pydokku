from functools import lru_cache
from typing import Iterator, List

from ..models import App, Command, Proxy
from ..utils import clean_stderr, get_stdout_rows_parser, parse_bool
from .base import DokkuPlugin


class ProxyPlugin(DokkuPlugin):
    """
    dokku core proxy plugin

    Subcommands NOT implemented: none.

    Extra features: none.
    """

    name = "proxy"
    object_classes = (Proxy,)

    @lru_cache
    def _get_rows_parser(self):
        return get_stdout_rows_parser(
            normalize_keys=False,
            discards=["Proxy computed type"],
            renames={
                "Proxy enabled": "enabled",
                "Proxy global type": "global_type",
                "Proxy type": "app_type",
            },
            parsers={
                "enabled": parse_bool,
            },
        )

    def report(self, app_name: str = None) -> List[Proxy] | Proxy:
        """Get the list of proxy configs for each app. If `app_name` is `None`, the report includes all apps"""
        _, stdout, stderr = self._evaluate("report", params=[] if app_name is None else [app_name], full_return=True)
        stderr = clean_stderr(stderr)
        if "You haven't deployed any applications yet" in stderr:
            return []
        elif stderr:
            raise RuntimeError(f"Error executing proxy:report: {stderr}")
        rows_parser = self._get_rows_parser()
        parsed_rows = rows_parser(stdout)
        return [Proxy(**row) for row in parsed_rows]

    def enable(self, app_name: str, execute: bool = True) -> str | Command:
        return self._evaluate("enable", params=[app_name], execute=execute)

    def disable(self, app_name: str, execute: bool = True) -> str | Command:
        return self._evaluate("disable", params=[app_name], execute=execute)

    def set(self, app_name: str | None, proxy_type: str, execute: bool = True) -> str | Command:
        system = app_name is None
        app_parameter = app_name if not system else "--global"
        return self._evaluate("set", params=[app_parameter, proxy_type], execute=execute)

    def clear_config(self, app_name: str | None, execute: bool = True) -> str | Command:
        system = app_name is None
        app_parameter = app_name if not system else "--all"
        return self._evaluate("clear-config", params=[app_parameter], execute=execute)

    def build_config(self, app_name: str | None, parallel: int = None, execute: bool = True) -> str | Command:
        system = app_name is None
        app_parameter = app_name if not system else "--all"
        params = []
        if parallel is not None:
            params.extend(["--parallel", str(parallel)])
        params.append(app_parameter)
        return self._evaluate("build-config", params=params, execute=execute)

    def object_list(self, apps: List[App], system: bool = True) -> List[Proxy]:
        apps_names = [app.name for app in apps]
        return [self.report(app_name)[0] for app_name in apps_names]

    def _create_object(self, obj: Proxy, skip_system: bool = False, execute: bool = True) -> List[str] | List[Command]:
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

    def object_create(self, obj: Proxy, execute: bool = True) -> List[str] | List[Command]:
        return self._create_object(obj=obj, execute=execute, skip_system=False)

    def object_create_many(self, objs: List[Proxy], execute: bool = True) -> Iterator[str] | Iterator[Command]:
        # The difference between this and calling `self.object_create` for each object is that this one yields only one
        # global command, so it's faster.
        for index, obj in enumerate(objs):
            yield from self._create_object(obj=obj, skip_system=index > 0, execute=execute)
