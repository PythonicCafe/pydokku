import json
import re
from collections import Counter
from functools import lru_cache
from typing import Iterator, List

from ..models import App, Command, Process, ProcessInfo
from ..utils import clean_stderr, get_stdout_rows_parser, parse_bool, parse_path
from .base import DokkuPlugin

REGEXP_PROCESS_STATUS = re.compile(r"^([^(]+) \(CID: ([^)]+)\)")


class PsPlugin(DokkuPlugin):
    name = "ps"
    object_class = ProcessInfo

    def inspect(self, app_name: str, execute: bool = True) -> List[dict]:
        result = self._evaluate("inspect", [app_name], execute=execute)
        if not execute:
            return result
        return json.loads(result)

    @lru_cache
    def _get_rows_parser(self):
        return get_stdout_rows_parser(
            normalize_keys=False,
            discards=["Processes", "Ps computed procfile path"],
            renames={
                "Ps can scale": "can_scale",
                "Ps procfile path": "app_procfile_path",
                "Ps global procfile path": "global_procfile_path",
                "Ps restart policy": "restart_policy",
                "Deployed": "deployed",
                "Restore": "restore",
                "Running": "running",
            },
            parsers={
                "can_scale": parse_bool,
                "deployed": parse_bool,
                "restore": parse_bool,
                "running": parse_bool,
                "global_procfile_path": parse_path,
                "app_procfile_path": parse_path,
            },
        )

    def _convert_rows(self, parsed_rows: List[dict]) -> List[Process]:
        result = []
        for row in parsed_rows:
            row["processes"] = []
            status_keys = [key for key in row.keys() if key.startswith("Status ")]
            for key in status_keys:
                value = row.pop(key)
                rest = key[len("Status ") :]
                name, process_id = rest.rsplit(" ", maxsplit=1)
                regexp_result = REGEXP_PROCESS_STATUS.findall(value)
                status, cid = regexp_result[0]
                row["processes"].append(Process(id=int(process_id), type=name, status=status, container_id=cid))
            result.append(self.object_class(**row))
        return result

    def report(self, app_name: str = None) -> List[ProcessInfo] | ProcessInfo:
        """Get a report of . If `app_name` is `None`, the report includes all apps

        WARNING: if the app is not deployed yet, it won't show the scale for each process type - in this case you can
        get those numbers by executing `self.get_scale(app_name)`.
        """
        _, stdout, stderr = self._evaluate("report", params=[] if app_name is None else [app_name], full_return=True)
        stderr = clean_stderr(stderr)
        if "You haven't deployed any applications yet" in stderr:
            return []
        elif stderr:
            raise RuntimeError(f"Error executing ps:report: {stderr}")
        rows_parser = self._get_rows_parser()
        parsed_rows = rows_parser(stdout)
        return self._convert_rows(parsed_rows)

    def start(self, app_name: str = None, parallel: int = None, execute: bool = True) -> str | Command:
        system = app_name is None
        params = []
        if parallel is not None:
            params.extend(["--parallel", str(parallel)])
        params.append(app_name if not system else "--all")
        return self._evaluate("start", params=params, execute=execute)

    def stop(self, app_name: str = None, parallel: int = None, execute: bool = True) -> str | Command:
        system = app_name is None
        params = []
        if parallel is not None:
            params.extend(["--parallel", str(parallel)])
        params.append(app_name if not system else "--all")
        return self._evaluate("stop", params=params, execute=execute)

    def restart(
        self, app_name: str = None, parallel: int = None, process: str = None, execute: bool = True
    ) -> str | Command:
        """
        Restart an app with process-type granularity

        Dokku provides restart with process-type granularity, but only app-level granularity is available for
        start/stop.
        WARNING: if `process` is specified but there's no process with this name for the app, then Dokku will restart
        ALL the processes for that app!
        """
        system = app_name is None
        if system and process is not None:
            raise ValueError("Cannot restart a specific process type for all apps")
        params = []
        if parallel is not None:
            params.extend(["--parallel", str(parallel)])
        params.append(app_name if not system else "--all")
        if process is not None:
            params.append(process)
        return self._evaluate("restart", params=params, execute=execute)

    def rebuild(self, app_name: str = None, parallel: int = None, execute: bool = True) -> str | Command:
        system = app_name is None
        params = []
        if parallel is not None:
            params.extend(["--parallel", str(parallel)])
        params.append(app_name if not system else "--all")
        return self._evaluate("rebuild", params=params, execute=execute)

    def restore(self, app_name: str = None, parallel: int = None, execute: bool = True) -> str | Command:
        system = app_name is None
        params = []
        if parallel is not None:
            params.extend(["--parallel", str(parallel)])
        params.append(app_name if not system else "--all")
        return self._evaluate("restore", params=params, execute=execute)

    def set_procfile_path(self, app_name: str | None, value: str, execute: bool = True) -> str | Command:
        system = app_name is None
        app_parameter = app_name if not system else "--global"
        return self._evaluate("set", params=[app_parameter, "procfile-path", str(value)], execute=execute)

    def unset_procfile_path(self, app_name: str | None, execute: bool = True) -> str | Command:
        system = app_name is None
        app_parameter = app_name if not system else "--global"
        return self._evaluate("set", params=[app_parameter, "procfile-path"], execute=execute)

    def set_restart_policy(self, app_name: str | None, value: str, execute: bool = True) -> str | Command:
        system = app_name is None
        app_parameter = app_name if not system else "--global"
        return self._evaluate("set", params=[app_parameter, "restart-policy", str(value)], execute=execute)

    def unset_restart_policy(self, app_name: str | None, execute: bool = True) -> str | Command:
        system = app_name is None
        app_parameter = app_name if not system else "--global"
        return self._evaluate("set", params=[app_parameter, "restart-policy"], execute=execute)

    def _parse_scale(self, stdout: str) -> dict[str, int]:
        lines = stdout.split("proctype: qty", maxsplit=1)[1].strip().splitlines()
        pairs = {}
        for line in lines:
            stop = line.find(":")
            key, value = line[:stop].strip(), line[stop + 1 :].strip()
            if value != "---":
                pairs[key] = int(value)
        return pairs

    def get_scale(self, app_name: str) -> dict[str, int]:
        """Get number of processes for each process type of an app (`dokku ps:scale app-name`)"""
        _, stdout, stderr = self._evaluate("scale", params=[app_name], execute=True, full_return=True)
        if stderr:
            raise RuntimeError(f"Cannot get scale for app {repr(app_name)}: {clean_stderr(stderr)}")
        return self._parse_scale(stdout)

    def set_scale(
        self, app_name: str, process_counts: dict[str, int], skip_deploy: bool = False, execute: bool = True
    ) -> str | Command:
        """Set the number of processes for process types of an app (`dokku ps:scale app-name type1=n1 type2=n2 ...`)"""
        params = []
        if skip_deploy:
            params.append("--skip-deploy")
        params.append(app_name)
        params.extend([f"{proc_type}={number}" for proc_type, number in process_counts.items()])
        return self._evaluate("scale", params=params, execute=execute)

    def dump_all(self, apps: List[App], system: bool = True) -> List[dict]:
        apps_names = [app.name for app in apps]
        result = []
        for app_name in apps_names:
            process_info = self.report(app_name=app_name)[0]
            if not process_info.processes:  # Probably app not deployed yet - get more info via `self.get_scale`
                for proc_type, number in self.get_scale(app_name=app_name).items():
                    for process_id in range(1, number + 1):
                        process_info.processes.append(
                            Process(
                                type=proc_type,
                                id=process_id,
                                status=None,
                                container_id=None,
                            )
                        )
            result.append(process_info.serialize())
        return result

    def _create_object(
        self, obj: Process, skip_global: bool = False, execute: bool = True
    ) -> List[str] | List[Command]:
        app_name = obj.app_name
        result = []
        if not skip_global:
            result.append(self.set_procfile_path(app_name=None, value=obj.global_procfile_path, execute=execute))
        if obj.app_procfile_path is not None:
            result.append(self.set_procfile_path(app_name=app_name, value=obj.app_procfile_path, execute=execute))
        result.append(self.set_restart_policy(app_name=app_name, value=obj.restart_policy, execute=execute))
        process_counter = Counter([process.type for process in obj.processes])
        result.append(self.set_scale(app_name=app_name, process_counts=dict(process_counter), execute=execute))
        return result

    def create_object(self, obj: Process, execute: bool = True) -> List[str] | List[Command]:
        return self._create_object(obj=obj, execute=execute, skip_global=False)

    def create_objects(self, objs: List[ProcessInfo], execute: bool = True) -> Iterator[str] | Iterator[Command]:
        # The difference between this and calling `self.create_object` for each object is that this one yields only
        # one global command
        if objs:
            yield self.set_procfile_path(app_name=None, value=objs[0].global_procfile_path, execute=execute)  # Global
            for obj in objs:
                yield from self._create_object(obj=obj, execute=execute, skip_global=True)
