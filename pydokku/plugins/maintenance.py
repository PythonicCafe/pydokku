from functools import lru_cache
from typing import List, Union

from ..models import App, Command, Maintenance
from ..utils import get_stdout_rows_parser, parse_bool
from .base import DokkuPlugin


class MaintenancePlugin(DokkuPlugin):
    """
    dokku official maintenance plugin

    Subommands NOT implemented:
    - `custom-page`: huge stdin input is currently not a priority

    EXTRA features: none.
    """

    name = "maintenance"
    subcommand = "maintenance"
    plugin_name = "maintenance"
    object_classes = (Maintenance,)
    requires = ("plugin", "apps")

    @lru_cache
    def _get_rows_parser(self):
        return get_stdout_rows_parser(
            normalize_keys=True,
            remove_prefix="maintenance_",
            parsers={
                "enabled": parse_bool,
            },
        )

    def list(self, app_name: Union[str, None] = None) -> List[Maintenance]:
        system = app_name is None
        # Dokku WILL return error in this `report` command, so `check=False` is used in all `:report/list` because of
        # this inconsistent behavior <https://github.com/dokku/dokku/issues/7454>
        _, stdout, stderr = self._evaluate(
            "report", params=[] if system else [app_name], check=False, full_return=True, execute=True
        )
        if not stdout and "You haven't deployed any applications yet" in stderr:
            return []
        elif stderr:
            raise RuntimeError(f"Error executing maintenance:report: {stderr}")
        rows_parser = self._get_rows_parser()
        return [Maintenance(**row) for row in rows_parser(stdout)]

    def enable(self, app_name: str, execute: bool = True) -> Union[str, Command]:
        return self._evaluate("enable", params=[app_name], execute=execute)

    def disable(self, app_name: str, execute: bool = True) -> Union[str, Command]:
        return self._evaluate("disable", params=[app_name], execute=execute)

    def object_list(self, apps: List[App], system: bool = True) -> List[Maintenance]:
        apps_names = [app.name for app in apps]
        return [obj for obj in self.list() if obj.app_name in apps_names]

    def object_create(self, obj: Maintenance, skip_system: bool = False, execute: bool = True) -> Union[List[str], List[Command]]:
        app_name = obj.app_name
        result = []
        if obj.enabled:
            result.append(self.enable(app_name=app_name, execute=execute))
        else:
            result.append(self.disable(app_name=app_name, execute=execute))
        return result
