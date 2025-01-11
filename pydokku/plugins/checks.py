from functools import lru_cache
from typing import List

from ..models import App, Check, Command
from ..utils import clean_stderr, get_stdout_rows_parser, parse_comma_separated_list, parse_int
from .base import DokkuPlugin


class ChecksPlugin(DokkuPlugin):
    """dokku core checks plugin

    It returns one global check and for each app more one check *per process type*.

    Subcommands NOT implemented: none.

    Extra features:
    - `checks:set`: was split in `set()` and `unset()` methods
    """

    name = "checks"
    object_classes = (Check,)

    @lru_cache
    def _get_rows_parser(self):
        return get_stdout_rows_parser(
            normalize_keys=True,
            renames={
                "checks_disabled_list": "disabled",
                "checks_skipped_list": "skipped",
                "checks_global_wait_to_retire": "global_wait_to_retire",
                "checks_wait_to_retire": "app_wait_to_retire",
            },
            discards=[
                "checks_computed_wait_to_retire",
            ],
            parsers={
                "global_wait_to_retire": parse_int,
                "app_wait_to_retire": parse_int,
                "disabled": parse_comma_separated_list,
                "skipped": parse_comma_separated_list,
            },
        )

    def _convert_rows(self, parsed_rows: List[dict], app_name: str | None) -> List[Check]:
        result = []
        for row in parsed_rows:
            if not result and app_name is None:
                # No object was added to the list, so we add the global one
                result.append(
                    Check(
                        app_name=None,
                        process="_all_",
                        status=None,
                        global_wait_to_retire=row["global_wait_to_retire"],
                        app_wait_to_retire=None,
                    )
                )
            if not row["disabled"] and not row["skipped"]:
                result.append(
                    Check(
                        app_name=row["app_name"],
                        process="_all_",
                        status="enabled",
                        app_wait_to_retire=row["app_wait_to_retire"],
                        global_wait_to_retire=row["global_wait_to_retire"],
                    )
                )
            else:
                for status in ("disabled", "skipped"):
                    for process in row[status]:
                        result.append(
                            Check(
                                app_name=row["app_name"],
                                process=process,
                                status=status,
                                app_wait_to_retire=row["app_wait_to_retire"],
                                global_wait_to_retire=row["global_wait_to_retire"],
                            )
                        )
        return result

    def list(self, app_name: str | None = None) -> List[Check]:
        """List disabled and skipped checks for an app

        WARNING: Dokku doesn't list the enabled checks! You must call
        `dokku ps:inspect <app-name> | grep com.dokku.process-type` to check all running process types. Dokku also does
        not provide an way to retrieve the 'wait-to-retire' global option unless we take it from the app listing,
        so if you haven't created any app, you wouldn't know the global wait to retire setting.
        """
        _, stdout, stderr = self._evaluate("report", params=[] if app_name is None else [app_name], full_return=True)
        if "You haven't deployed any applications yet" in clean_stderr(stderr):
            return []
        elif stderr:
            raise RuntimeError(f"Error executing checks:report: {stderr}")
        rows_parser = self._get_rows_parser()
        parsed_rows = rows_parser(stdout)
        return self._convert_rows(parsed_rows, app_name)

    def set(self, app_name: str | None, key: str, value: int, execute: bool = True) -> str | Command:
        """Set app's property"""
        system = app_name is None
        app_parameter = app_name if not system else "--global"
        return self._evaluate("set", params=[app_parameter, key, str(value)], execute=execute)

    def unset(self, app_name: str | None, key: str, execute: bool = True) -> str | Command:
        system = app_name is None
        app_parameter = app_name if not system else "--global"
        return self._evaluate("set", params=[app_parameter, key], execute=execute)

    def disable(self, app_name: str, process_names: List[str] = None, execute: bool = True) -> str | Command:
        ps = [",".join(process_names)] if process_names is not None else []
        return self._evaluate("disable", params=[app_name] + ps, execute=execute)

    def enable(self, app_name: str, process_names: List[str] = None, execute: bool = True) -> str | Command:
        ps = [",".join(process_names)] if process_names is not None else []
        return self._evaluate("enable", params=[app_name] + ps, execute=execute)

    def skip(self, app_name: str, process_names: List[str] = None, execute: bool = True) -> str | Command:
        ps = [",".join(process_names)] if process_names is not None else []
        return self._evaluate("skip", params=[app_name] + ps, execute=execute)

    def run(self, app_name: str, execute: bool = True) -> str | Command:
        return self._evaluate("run", params=[app_name], execute=execute)

    def object_list(self, apps: List[App], system: bool = True) -> List[Check]:
        apps_names = [app.name for app in apps]
        if system:
            apps_names = [None] + apps_names
        return [obj for obj in self.list() if obj.app_name in apps_names]

    def object_create(self, obj: Check, execute: bool = True) -> List[str] | List[Command]:
        app_name = obj.app_name
        system = app_name is None
        result = []
        # First, set wait to retire
        if system:
            result.append(
                self.set(app_name=None, key="wait-to-retire", value=obj.global_wait_to_retire, execute=execute)
            )
        elif obj.app_wait_to_retire is not None:
            result.append(
                self.set(app_name=app_name, key="wait-to-retire", value=obj.app_wait_to_retire, execute=execute)
            )
        if not system:  # Set process status (only if not global)
            if obj.status == "enabled":
                result.append(self.enable(app_name=obj.app_name, process_names=[obj.process], execute=execute))
            elif obj.status == "disabled":
                result.append(self.disable(app_name=obj.app_name, process_names=[obj.process], execute=execute))
            elif obj.status == "skipped":
                result.append(self.skip(app_name=obj.app_name, process_names=[obj.process], execute=execute))
        return result

    # TODO: implement object_create_many and execute one operation per group of status
