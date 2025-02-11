import re
from functools import lru_cache
from typing import List, Union

from ..models import App, Command
from ..utils import get_stdout_rows_parser, parse_bool, parse_path, parse_timestamp
from .base import DokkuPlugin

REGEXP_APP_METADATA = re.compile(r"App\s+([^:]+):\s*(.*)")


class AppsPlugin(DokkuPlugin):
    """
    dokku core apps plugin

    Subcommands NOT implemented:
    - `apps:exists`: can check if app exists by calling `list()` and checking `app.name` for the objects returned
    - `apps:report`: is actually run in `list()` method
    - `apps:list`: is not run at all (redundant with `report`, but `report` exposes more information)

    Extra features: none.
    """

    name = subcommand = plugin_name = "apps"
    object_classes = (App,)
    requires = ("plugin",)
    requires_extra_commands = False

    @lru_cache
    def _get_rows_parser(self):
        return get_stdout_rows_parser(
            normalize_keys=True,
            remove_prefix="app_",
            renames={"dir": "path", "app_name": "name"},
            parsers={
                "path": parse_path,
                "locked": parse_bool,
                "created_at": parse_timestamp,
            },
        )

    def list(self) -> List[App]:
        # Dokku WILL return error in this `report` command, so `check=False` is used in all `:report/list` because of
        # this inconsistent behavior <https://github.com/dokku/dokku/issues/7454>
        _, stdout, stderr = self._evaluate("report", check=False, full_return=True, execute=True)
        if not stdout and "You haven't deployed any applications yet" in stderr:
            return []
        elif stderr:
            raise RuntimeError(f"Error executing apps:report: {stderr}")
        rows_parser = self._get_rows_parser()
        return [App(**row) for row in rows_parser(stdout)]

    def create(self, name: str, execute: bool = True) -> Union[str, Command]:
        return self._evaluate("create", params=[name], execute=execute)

    def destroy(self, name: str, execute: bool = True) -> Union[str, Command]:
        return self._evaluate("destroy", params=[name], stdin=name, execute=execute)

    def clone(self, old_name: str, new_name: str, execute: bool = True) -> Union[str, Command]:
        return self._evaluate("clone", params=[old_name, new_name], execute=execute)

    def lock(self, name: str, execute: bool = True) -> Union[str, Command]:
        return self._evaluate("lock", params=[name], execute=execute)

    def unlock(self, name: str, execute: bool = True) -> Union[str, Command]:
        return self._evaluate("unlock", params=[name], execute=execute)

    def locked(self, name: str) -> bool:
        stdout = self._evaluate("unlock", params=[name], check=False, execute=True)
        return bool(stdout)

    def rename(self, old_name: str, new_name: str, execute: bool = True) -> Union[str, Command]:
        return self._evaluate("rename", params=[old_name, new_name], execute=execute)

    def object_list(self, apps: List[App], system: bool = True) -> List[App]:
        return apps

    def object_create(
        self, obj: App, skip_system: bool = False, execute: bool = True
    ) -> Union[List[str], List[Command]]:
        result = [self.create(name=obj.name, execute=execute)]
        if obj.locked:
            result.append(self.lock(name=obj.name, execute=execute))
        return result
