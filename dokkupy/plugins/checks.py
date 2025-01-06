from typing import List

from ..models import App, Check, Command
from ..utils import REGEXP_DOKKU_HEADER, clean_stderr
from .base import DokkuPlugin


def parse_checks_list(text):
    if text == "none":
        return []
    return text.split(",")


class ChecksPlugin(DokkuPlugin):
    """dokku checks plugin

    Since the only option to `checks:set` is `wait-to-retire` (and it didn't change for the last years), it was decided
    to add this as a method `set_wait_to_retire` instead of a generic `checks:set` method.
    """

    name = "checks"
    object_class = Check

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
        result = []
        for app_checks in REGEXP_DOKKU_HEADER.split(stdout.strip())[1:]:
            lines = app_checks.strip().splitlines()
            row_app_name, _ = lines[0].split(maxsplit=1)
            row = {}
            for line in lines[1:]:
                key, value = line.strip().split(":", maxsplit=1)
                row[key.lower()] = value.strip()
            app_wait_to_retire = int(row["checks wait to retire"]) if row["checks wait to retire"] else None
            global_wait_to_retire = (
                int(row["checks global wait to retire"]) if row["checks global wait to retire"] else None
            )
            if not result and app_name is None:
                # No object was added to the list, so we add the global one
                result.append(
                    self.object_class(
                        app_name=None,
                        process="_all_",
                        status=None,
                        global_wait_to_retire=global_wait_to_retire,
                        app_wait_to_retire=None,
                    )
                )
            disabled = parse_checks_list(row["checks disabled list"])
            skipped = parse_checks_list(row["checks skipped list"])
            if not disabled and not skipped:
                result.append(
                    self.object_class(
                        app_name=row_app_name,
                        process="_all_",
                        status="enabled",
                        app_wait_to_retire=app_wait_to_retire,
                        global_wait_to_retire=global_wait_to_retire,
                    )
                )
            else:
                for process in disabled:
                    result.append(
                        self.object_class(
                            app_name=row_app_name,
                            process=process,
                            status="disabled",
                            app_wait_to_retire=app_wait_to_retire,
                            global_wait_to_retire=global_wait_to_retire,
                        )
                    )
                for process in skipped:
                    result.append(
                        self.object_class(
                            app_name=row_app_name,
                            process=process,
                            status="skipped",
                            app_wait_to_retire=app_wait_to_retire,
                            global_wait_to_retire=global_wait_to_retire,
                        )
                    )
        return result

    def set_wait_to_retire(self, app_name: str | None, value: int, execute: bool = True):
        """Set app's wait to retire time"""
        system = app_name is None
        app_parameter = app_name if not system else "--global"
        return self._evaluate("set", params=[app_parameter, "wait-to-retire", str(value)], execute=execute)

    def disable(self, app_name: str, process_names: List[str] = None, execute: bool = True):
        ps = [",".join(process_names)] if process_names is not None else []
        return self._evaluate("disable", params=[app_name] + ps, execute=execute)

    def enable(self, app_name: str, process_names: List[str] = None, execute: bool = True):
        ps = [",".join(process_names)] if process_names is not None else []
        return self._evaluate("enable", params=[app_name] + ps, execute=execute)

    def skip(self, app_name: str, process_names: List[str] = None, execute: bool = True):
        ps = [",".join(process_names)] if process_names is not None else []
        return self._evaluate("skip", params=[app_name] + ps, execute=execute)

    def run(self, app_name: str, execute: bool = True):
        return self._evaluate("run", params=[app_name], execute=execute)

    def dump_all(self, apps: List[App], system: bool = True) -> List[dict]:
        apps_names = [app.name for app in apps]
        if system:
            apps_names = [None] + apps_names
        return [obj.serialize() for obj in self.list() if obj.app_name in apps_names]

    def create_object(self, obj: Check, execute: bool = True) -> List[str] | List[Command]:
        app_name = obj.app_name
        system = app_name is None
        result = []
        # First, set wait to retire
        if system:
            result.append(self.set_wait_to_retire(app_name=None, value=obj.global_wait_to_retire, execute=execute))
        elif obj.app_wait_to_retire is not None:
            result.append(self.set_wait_to_retire(app_name=app_name, value=obj.app_wait_to_retire, execute=execute))
        if not system:  # Set process status (only if not global)
            if obj.status == "enabled":
                result.append(self.enable(app_name=obj.app_name, process_names=[obj.process], execute=execute))
            elif obj.status == "disabled":
                result.append(self.disable(app_name=obj.app_name, process_names=[obj.process], execute=execute))
            elif obj.status == "skipped":
                result.append(self.skip(app_name=obj.app_name, process_names=[obj.process], execute=execute))
        return result

    # TODO: implement create_objects and execute one operation per group of status
