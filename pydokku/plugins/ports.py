from functools import cached_property, lru_cache
from itertools import groupby
from typing import Dict, Iterator, List, Union

from ..models import App, Command, Port
from ..utils import clean_stderr, get_app_name, get_stdout_rows_parser, parse_space_separated_list
from .base import DokkuPlugin


class PortsPlugin(DokkuPlugin):
    """
    dokku core ports plugin

    If 'Ports map' is empty, then 'Ports map detected' is used. if not, then DISCARDS 'Ports map detected'.

    Subcommands NOT implemented:
    - `ports:list`: same data as `report`

    Extra features: none.
    """

    name = plugin_name = "ports"
    object_classes = (Port,)
    requires = ("apps", "domains")
    requires_extra_commands = False

    @cached_property
    def subcommand(self):
        return "ports" if self.dokku.version() >= (0, 31, 0) else "proxy"

    @cached_property
    def _operation_prefix(self):
        return "" if self.dokku.version() >= (0, 31, 0) else "ports-"

    @lru_cache
    def _get_rows_parser(self):
        return get_stdout_rows_parser(
            normalize_keys=True,
            remove_prefix="ports_",
            discards=[],
            renames={
                "map": "app_map",
                "map_detected": "global_map",
            },
            parsers={
                "app_map": parse_space_separated_list,
                "global_map": parse_space_separated_list,
            },
        )

    def _parse_port_string(self, app_name: Union[str, None], value: str) -> Port:
        scheme, ports = value.split(":", maxsplit=1)
        if ":" in ports:
            host_port, container_port = [int(item) for item in ports.split(":")]
        else:
            host_port, container_port = int(ports), None
        return Port(app_name=app_name, scheme=scheme, host_port=host_port, container_port=container_port)

    def _convert_rows(self, parsed_rows: List[dict], skip_system: bool = False) -> List[Port]:
        result = []
        for row in parsed_rows:
            if not result and row["global_map"] and not skip_system:
                for port in row["global_map"]:
                    result.append(self._parse_port_string(app_name=None, value=port))
            for port in row["app_map"]:
                result.append(self._parse_port_string(app_name=row["app_name"], value=port))
        return result

    def _parse_old_row(self, stdout: str) -> Dict:
        app_name = None
        app_map = []
        for line in stdout.splitlines():
            line = line.strip()
            if line.startswith("-----> Port mappings for"):
                app_name = line.split(" for ")[1]
            if line.startswith("----->"):
                continue
            app_map.append(":".join(line.split()))
        return {"app_name": app_name, "app_map": app_map, "global_map": None}

    def list(self, app_name: Union[str, None] = None) -> List[Port]:
        # Dokku WILL return error in this `report` command, so `check=False` is used in all `:report/list` because of
        # this inconsistent behavior <https://github.com/dokku/dokku/issues/7454>
        system = app_name is None
        if self.dokku.version() >= (0, 31, 0):
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
                raise RuntimeError(f"Error executing {self._operation_prefix}report: {stderr}")
            rows_parser = self._get_rows_parser()
            parsed_rows = rows_parser(stdout)
            return self._convert_rows(parsed_rows, skip_system=app_name is not None)
        else:
            if system:
                apps_names = [app.name for app in self.dokku.apps.list()]
            else:
                apps_names = [app_name]
            result = []
            for app_name in apps_names:
                _, stdout, stderr = self._evaluate(
                    "ports",
                    params=[app_name],
                    check=False,
                    full_return=True,
                    execute=True,
                )
                stderr = clean_stderr(stderr)
                if "No port mappings configured" in stderr:
                    continue
                elif stderr:
                    raise RuntimeError(f"Error executing {self._operation_prefix}report: {stderr}")
                result.extend(self._convert_rows([self._parse_old_row(stdout)], skip_system=True))
            return result

    def clear(self, app_name: str, execute: bool = True) -> Union[str, Command]:
        return self._evaluate(f"{self._operation_prefix}clear", params=[app_name], execute=execute)

    def add(self, ports: List[Port], execute: bool = True) -> Union[List[str], List[Command]]:
        result = []
        ports.sort(key=get_app_name)
        for app_name, app_ports in groupby(ports, key=get_app_name):
            params = [app_name]
            for port in app_ports:
                if port.container_port is not None:
                    params.append(f"{port.scheme}:{port.host_port}:{port.container_port}")
                else:
                    params.append(f"{port.scheme}:{port.host_port}")
            app_result = self._evaluate(f"{self._operation_prefix}add", params=params, execute=execute)
            if execute and "No port set" in app_result:
                app_title = "global" if app_name is None else f"app {app_name}"
                raise RuntimeError(f"Cannot add port to {app_title}: {app_result}")
            result.append(app_result)
        return result

    def set(self, ports: List[Port], execute: bool = True) -> Union[List[str], List[Command]]:
        result = []
        ports.sort(key=get_app_name)
        for app_name, app_ports in groupby(ports, key=get_app_name):
            params = [app_name]
            for port in app_ports:
                if port.container_port is not None:
                    params.append(f"{port.scheme}:{port.host_port}:{port.container_port}")
                else:
                    params.append(f"{port.scheme}:{port.host_port}")
            app_result = self._evaluate(f"{self._operation_prefix}set", params=params, execute=execute)
            if execute and "No port set" in app_result:
                app_title = "global" if app_name is None else f"app {app_name}"
                raise RuntimeError(f"Cannot set port to {app_title}: {app_result}")
            result.append(app_result)
        return result

    def remove(self, ports: List[Port], execute: bool = True) -> Union[List[str], List[Command]]:
        result = []
        ports.sort(key=get_app_name)
        for app_name, app_ports in groupby(ports, key=get_app_name):
            params = [app_name]
            for port in app_ports:
                if port.container_port is not None:
                    params.append(f"{port.scheme}:{port.host_port}:{port.container_port}")
                else:
                    params.append(f"{port.scheme}:{port.host_port}")
            result.append(self._evaluate(f"{self._operation_prefix}remove", params=params, execute=execute))
        return result

    def object_list(self, apps: List[App], system: bool = True) -> List[Port]:
        apps_names = [app.name for app in apps]
        if system:
            return [obj for obj in self.list() if obj.app_name in [None] + apps_names]
        else:
            result = []
            for app_name in apps_names:
                result.extend(self.list(app_name=app_name))
            return result

    def object_create(
        self, obj: Port, skip_system: bool = False, execute: bool = True
    ) -> Union[List[str], List[Command]]:
        # `skip_system` is ignored since there's no way to set global port mapping
        if obj.app_name is None:
            return []
        return self.set(ports=[obj], execute=execute)

    def object_create_many(self, objs: List[Port], execute: bool = True) -> Union[Iterator[str], Iterator[Command]]:
        filtered_objs = [obj for obj in objs if obj.app_name is not None]
        if filtered_objs:
            yield from self.set(ports=filtered_objs, execute=execute)
