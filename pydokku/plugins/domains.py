import random
import string
from functools import lru_cache
from typing import List

from ..models import App, Command, Domain
from ..utils import get_stdout_rows_parser, parse_bool, parse_space_separated_list
from .base import DokkuPlugin


class DomainsPlugin(DokkuPlugin):
    """
    dokku core apps plugin

    Subcommands NOT implemented: none.

    Extra features:
    - `domains:add` and `domains:add-global` were merged into `add()`
    - `domains:clear` and `domains:clear-global` were merged into `clear()`
    - `domains:remove` and `domains:remove-global` were merged into `remove()`
    - `domains:set` and `domains:set-global` were merged into `set()`
    - `list()`: will execute `domains:report` both for global and for all apps
    """
    name = "domains"
    object_classes = (Domain,)

    @lru_cache
    def _get_rows_parser(self):
        return get_stdout_rows_parser(
            normalize_keys=True,
            renames={
                "domains_app_enabled": "app_enabled",
                "domains_app_vhosts": "app_domains",
                "domains_global_enabled": "global_enabled",
                "domains_global_vhosts": "global_domains",
            },
            parsers={
                "app_enabled": parse_bool,
                "app_domains": parse_space_separated_list,
                "global_enabled": parse_bool,
                "global_domains": parse_space_separated_list,
            },
        )

    def _convert_rows(self, parsed_rows: List[dict]) -> List[Domain]:
        result = []
        for row in parsed_rows:
            if row["app_name"] == "Global":
                result.append(
                    Domain(
                        app_name=None,
                        enabled=row["global_enabled"],
                        domains=row["global_domains"],
                    )
                )
            else:
                result.append(
                    Domain(
                        app_name=row["app_name"],
                        enabled=row["app_enabled"],
                        domains=row["app_domains"],
                    )
                )
        return result

    def list(self, app_name: str | None = None) -> List[Domain]:
        if app_name is None:
            stdout_global = self._evaluate("report", ["--global"], execute=True)
            stdout_apps = self._evaluate("report", execute=True)
            stdout = f"{stdout_global}\n{stdout_apps}"
        else:
            stdout = self._evaluate("report", [app_name], execute=True)
        rows_parser = self._get_rows_parser()
        parsed_rows = rows_parser(stdout)
        return self._convert_rows(parsed_rows)

    def add(self, app_name: str | None, domains: List[str], execute: bool = True) -> str | Command:
        system = app_name is None
        if not system:
            command, params = "add", [app_name] + domains
        else:
            command, params = "add-global", domains
        return self._evaluate(command, params=params, execute=execute)

    def set(self, app_name: str | None, domains: List[str], execute: bool = True) -> str | Command:
        system = app_name is None
        if not system:
            command, params = "set", [app_name] + domains
        else:
            command, params = "set-global", domains
        return self._evaluate(command, params=params, execute=execute)

    def clear(self, app_name: str | None, execute: bool = True) -> str | Command:
        system = app_name is None
        if not system:
            command, params = "clear", [app_name]
        else:
            command, params = "clear-global", []
        return self._evaluate(command, params=params, execute=execute)

    def remove(self, app_name: str | None, domains: List[str], execute: bool = True) -> str | Command:
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

    def object_list(self, apps: List[App], system: bool = True) -> List[Domain]:
        apps_names = [app.name for app in apps]
        if system:
            apps_names = [None] + apps_names
        return [obj for obj in self.list() if obj.app_name in apps_names]

    def object_create(self, obj: Domain, execute: bool = True) -> List[str] | List[Command]:
        app_name = obj.app_name
        result = []
        if not obj.domains:
            # XXX: To guarantee there will be no domain in this app, we set it to a random domain, then remove it. This
            # is the only way to really clean domains of an app without parsing the result of `domains:report` (which
            # is required for this command) as of Dokku version 0.35.13. Future versions of Dokku will implement a
            # fixed `domains:clean` command that will make this approach obsolete - but for older versions this is
            # the only way to do it. More info at: <https://github.com/dokku/dokku/issues/7438>
            random_subdomain = "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(32))
            temp_domain = f"{random_subdomain}.tmp.example.net"
            result.extend(
                [
                    self.set(app_name=app_name, domains=[temp_domain], execute=execute),
                    self.remove(app_name=app_name, domains=[temp_domain], execute=execute),
                ]
            )
        if not obj.enabled:
            result.append(self.disable(app_name=obj.app_name, execute=execute))
        elif obj.domains:
            result.append(self.set(obj.app_name, domains=obj.domains, execute=execute))
        return result
