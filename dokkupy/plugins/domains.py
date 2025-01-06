from typing import List

from ..models import App, Command, Domain
from ..utils import REGEXP_DOKKU_HEADER, parse_bool
from .base import DokkuPlugin


class DomainsPlugin(DokkuPlugin):
    name = "domains"
    object_class = Domain

    def list(self, app_name: str | None = None) -> List[Domain]:
        if app_name is None:
            stdout_global = self._evaluate("report", ["--global"], execute=True)
            stdout_apps = self._evaluate("report", execute=True)
            stdout = f"{stdout_global}\n{stdout_apps}"
        else:
            stdout = self._evaluate("report", [app_name], execute=True)
        result = []
        for index, app_domains in enumerate(REGEXP_DOKKU_HEADER.split(stdout.strip())[1:]):
            lines = app_domains.strip().splitlines()
            row_app_name, _ = lines[0].split(maxsplit=1)
            if app_name is None and index == 0:
                assert (
                    row_app_name == "Global"
                ), f"Expected the first domin report to be 'Global', got '{repr(row_app_name)}'"
                row_app_name = None
                key_str = "global"
            else:
                key_str = "app"
            row = {}
            for line in lines[1:]:
                key, value = line.strip().split(":", maxsplit=1)
                row[key.lower()] = value.strip()
            result.append(
                self.object_class(
                    app_name=row_app_name,
                    enabled=parse_bool(row[f"domains {key_str} enabled"]),
                    domains=row[f"domains {key_str} vhosts"].split(),
                )
            )
        return result

    def add(self, app_name: str, domains: List[str], execute: bool = True) -> str | Command:
        system = app_name is None
        if not system:
            command, params = "add", [app_name] + domains
        else:
            command, params = "add-global", domains
        return self._evaluate(command, params=params, execute=execute)

    def set(self, app_name: str, domains: List[str], execute: bool = True) -> str | Command:
        system = app_name is None
        if not system:
            command, params = "set", [app_name] + domains
        else:
            command, params = "set-global", domains
        return self._evaluate(command, params=params, execute=execute)

    def clear(self, app_name: str, execute: bool = True) -> str | Command:
        system = app_name is None
        if not system:
            command, params = "clear", [app_name]
        else:
            command, params = "clear-global", []
        return self._evaluate(command, params=params, execute=execute)

    def remove(self, app_name: str, domains: List[str], execute: bool = True) -> str | Command:
        system = app_name is None
        if not system:
            command, params = "remove", [app_name] + domains
        else:
            command, params = "remove-global", domains
        return self._evaluate(command, params=params, execute=execute)

    def enable(self, app_name: str, execute: bool = True) -> str | Command:
        return self._evaluate("enable", params=[app_name], execute=execute)

    def disable(self, app_name: str, execute: bool = True) -> str | Command:
        return self._evaluate("disable", params=[app_name], execute=execute)

    def dump_all(self, apps: List[App], system: bool = True) -> List[dict]:
        apps_names = [app.name for app in apps]
        if system:
            apps_names = [None] + apps_names
        return [obj.serialize() for obj in self.list() if obj.app_name in apps_names]

    def create_object(self, obj: Domain, execute: bool = True) -> List[str] | List[Command]:
        if not obj.enabled:
            return [self.disable(app_name=obj.app_name, execute=execute)]
        return [self.set(obj.app_name, domains=obj.domains, execute=execute)]
