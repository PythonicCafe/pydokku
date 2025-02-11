import json
import re
from collections import Counter
from functools import lru_cache
from typing import Dict, List, Union

from ..models import App, Command, Process, ProcessInfo
from ..utils import clean_stderr, get_stdout_rows_parser, parse_bool, parse_path
from .base import DokkuPlugin

REGEXP_PROCESS_STATUS = re.compile(r"^([^(]+) \(CID: ([^)]+)\)")


class PsPlugin(DokkuPlugin):
    """
    dokku core ps plugin

    Subcommands NOT implemented: none.

    Extra features:
    - `ps:set`: was split in `set()` and `unset()` methods
    - `ps:scale`: was split in `get_scale()` and `set_scale()` methods
    """

    name = subcommand = plugin_name = "ps"
    object_classes = (ProcessInfo,)
    requires = ("apps", "git")
    requires_extra_commands = False

    def inspect(self, app_name: str, execute: bool = True) -> List[dict]:
        result = self._evaluate("inspect", [app_name], execute=execute)
        if not execute:
            return result
        return json.loads(result)

    @lru_cache
    def _get_rows_parser(self):
        return get_stdout_rows_parser(
            normalize_keys=False,  # So we get original "Status" string for each process
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

    def _convert_rows(self, parsed_rows: List[dict]) -> List[ProcessInfo]:
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
            result.append(ProcessInfo(**row))
        return result

    def list(self, app_name: Union[str, None] = None) -> Union[List[ProcessInfo], ProcessInfo]:
        """Get the list of processes. If `app_name` is `None`, the report includes all apps

        WARNING: if the app is not deployed yet, it won't show the scale for each process type - in this case you can
        get those numbers by executing `self.get_scale(app_name)`.
        """
        # Dokku WILL return error in this `report` command, so `check=False` is used in all `:report/list` because of
        # this inconsistent behavior <https://github.com/dokku/dokku/issues/7454>
        system = app_name is None
        _, stdout, stderr = self._evaluate(
            "report",
            params=[] if system else [app_name],
            check=False,
            full_return=True,
            execute=True,
        )
        stderr = clean_stderr(stderr)
        if "You haven't deployed any applications yet" in stderr:
            return []
        elif stderr:
            raise RuntimeError(f"Error executing ps:report: {stderr}")
        rows_parser = self._get_rows_parser()
        parsed_rows = rows_parser(stdout)
        return self._convert_rows(parsed_rows)

    def start(
        self, app_name: Union[str, None] = None, parallel: int = None, execute: bool = True
    ) -> Union[str, Command]:
        system = app_name is None
        params = []
        if parallel is not None:
            params.extend(["--parallel", str(parallel)])
        params.append(app_name if not system else "--all")
        return self._evaluate("start", params=params, execute=execute)

    def stop(
        self, app_name: Union[str, None] = None, parallel: int = None, execute: bool = True
    ) -> Union[str, Command]:
        system = app_name is None
        params = []
        if parallel is not None:
            params.extend(["--parallel", str(parallel)])
        params.append(app_name if not system else "--all")
        return self._evaluate("stop", params=params, execute=execute)

    def restart(
        self, app_name: Union[str, None] = None, parallel: int = None, process: str = None, execute: bool = True
    ) -> Union[str, Command]:
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

    def rebuild(
        self, app_name: Union[str, None] = None, parallel: int = None, execute: bool = True
    ) -> Union[str, Command]:
        system = app_name is None
        params = []
        if parallel is not None:
            params.extend(["--parallel", str(parallel)])
        params.append(app_name if not system else "--all")
        return self._evaluate("rebuild", params=params, execute=execute)

    def restore(
        self, app_name: Union[str, None] = None, parallel: int = None, execute: bool = True
    ) -> Union[str, Command]:
        system = app_name is None
        params = []
        if parallel is not None:
            params.extend(["--parallel", str(parallel)])
        params.append(app_name if not system else "--all")
        return self._evaluate("restore", params=params, execute=execute)

    def set(self, app_name: Union[str, None], key: str, value: str, execute: bool = True) -> Union[str, Command]:
        system = app_name is None
        app_parameter = app_name if not system else "--global"
        return self._evaluate("set", params=[app_parameter, key, str(value)], execute=execute)

    def unset(self, app_name: Union[str, None], key: str, execute: bool = True) -> Union[str, Command]:
        system = app_name is None
        app_parameter = app_name if not system else "--global"
        return self._evaluate("set", params=[app_parameter, key], execute=execute)

    def _parse_scale(self, stdout: str) -> Dict[str, int]:
        lines = stdout.split("proctype: qty", maxsplit=1)[1].strip().splitlines()
        pairs = {}
        for line in lines:
            stop = line.find(":")
            key, value = line[:stop].strip(), line[stop + 1 :].strip()
            if value != "---":
                pairs[key] = int(value)
        return pairs

    def get_scale(self, app_name: str) -> Dict[str, int]:
        """Get number of processes for each process type of an app (`dokku ps:scale app-name`)"""
        _, stdout, stderr = self._evaluate("scale", params=[app_name], execute=True, full_return=True)
        if stderr:
            raise RuntimeError(f"Cannot get scale for app {repr(app_name)}: {clean_stderr(stderr)}")
        return self._parse_scale(stdout)

    def set_scale(
        self, app_name: str, process_counts: Dict[str, int], skip_deploy: bool = False, execute: bool = True
    ) -> Union[str, Command]:
        """Set the number of processes for process types of an app (`dokku ps:scale app-name type1=n1 type2=n2 ...`)"""
        params = []
        if skip_deploy:
            params.append("--skip-deploy")
        params.append(app_name)
        params.extend([f"{proc_type}={number}" for proc_type, number in process_counts.items()])
        return self._evaluate("scale", params=params, execute=execute)

    def object_list(self, apps: List[App], system: bool = True) -> List[ProcessInfo]:
        apps_names = [app.name for app in apps]
        result = []
        for app_name in apps_names:
            process_info = self.list(app_name=app_name)[0]
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
            result.append(process_info)
        return result

    def object_create(
        self, obj: ProcessInfo, skip_system: bool = False, execute: bool = True
    ) -> Union[List[str], List[Command]]:
        app_name = obj.app_name
        result = []
        if not skip_system:
            result.append(self.set(app_name=None, key="procfile-path", value=obj.global_procfile_path, execute=execute))
        if obj.app_procfile_path is not None:
            result.append(
                self.set(app_name=app_name, key="procfile-path", value=obj.app_procfile_path, execute=execute)
            )
        result.append(self.set(app_name=app_name, key="restart-policy", value=obj.restart_policy, execute=execute))
        process_counter = Counter([process.type for process in obj.processes])
        result.append(self.set_scale(app_name=app_name, process_counts=dict(process_counter), execute=execute))
        if obj.deployed:
            result.append(self.restore(app_name=app_name, execute=execute))
        return result
