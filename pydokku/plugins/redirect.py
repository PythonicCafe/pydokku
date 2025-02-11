from itertools import zip_longest
from typing import List, Union

from ..models import App, Command, Redirect
from .base import DokkuPlugin


class RedirectPlugin(DokkuPlugin):
    """dokku official redirect plugin

    Subcommands NOT implemented: none.

    Extra features: none.
    """

    name = subcommand = plugin_name = "redirect"
    object_classes = (Redirect,)
    requires = ("apps", "domains")
    requires_extra_commands = False

    def _parse_list(self, stdout: str) -> List[dict]:
        lines = stdout.splitlines()
        first_line = lines[0]
        header = ("SOURCE", "DESTINATION", "CODE")
        header_indices = [first_line.index(key) for key in header]
        result = []
        for line in lines[1:]:
            row = {}
            for field_name, (start, stop) in zip(header, zip_longest(header_indices, header_indices[1:])):
                field_name = field_name.lower()
                row[field_name] = line[start:stop].strip()
            row["code"] = int(row["code"])
            result.append(row)
        return result

    def list(self, app_name: str) -> List[Redirect]:
        # Dokku won't return error in this "list" command, but `check=False` is used in all `:report/list` because of
        # this inconsistent behavior <https://github.com/dokku/dokku/issues/7454>
        _, stdout, stderr = self._evaluate(None, params=[app_name], check=False, full_return=True, execute=True)
        if "There are no redirects for" in stderr:
            return []
        elif stderr:
            raise RuntimeError(f"Error executing redirect (list): {stderr}")
        return [Redirect(app_name=app_name, **row) for row in self._parse_list(stdout)]

    def set(
        self, app_name: str, source: str, destination: str, code: Union[int, None] = None, execute: bool = True
    ) -> Union[str, Command]:
        params = [app_name, source, destination]
        if code is not None:
            params.append(str(code))
        return self._evaluate("set", params=params, execute=execute)

    def unset(self, app_name: str, source: str, execute: bool = True) -> Union[str, Command]:
        return self._evaluate("unset", params=[app_name, source], execute=execute)

    def object_list(self, apps: List[App], system: bool = True) -> List[Redirect]:
        result = []
        for app in apps:
            result.extend(self.list(app.name))
        return result

    def object_create(
        self, obj: Redirect, skip_system: bool = False, execute: bool = True
    ) -> Union[List[str], List[Command]]:
        return [
            self.set(
                app_name=obj.app_name, source=obj.source, destination=obj.destination, code=obj.code, execute=execute
            )
        ]
