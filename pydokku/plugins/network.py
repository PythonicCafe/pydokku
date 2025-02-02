import json
from functools import lru_cache
from typing import Any, List, Union

from ..models import App, AppNetwork, Command, Network
from ..utils import REGEXP_DOKKU_HEADER, clean_stderr, get_stdout_rows_parser, parse_bool, parse_comma_separated_list
from .base import DokkuPlugin


class NetworkPlugin(DokkuPlugin):
    """
    dokku core network plugin

    This plugin WILL NOT recreate non-Dokku networks (the ones created using `dokku network:create` has a
    "com.dokku.network-name" label set you can see using `docker network inspect <name>`).

    Subcommands NOT implemented:
    - `network:exists`: you can check if a network exists by calling `list()` and checking the `name` parameter on
      returned objects
    - `network:info`: has the same information as `network:list`

    Extra features:
    - `rebuild` and `rebuildall` merged into `rebuild()`
    """

    name = subcommand = plugin_name = "network"
    object_classes = (Network, AppNetwork)
    requires = ("apps",)
    requires_extra_commands = True

    def create(self, name: str, execute: bool = True) -> Union[str, Command]:
        return self._evaluate("create", params=[name], execute=execute)

    def destroy(self, name: str, force: bool = False, execute: bool = True) -> Union[str, Command]:
        params = []
        if force:
            params.append("--force")
        params.append(name)
        return self._evaluate("destroy", params=params, stdin=name if not force else None, execute=execute)

    def _parse_list_json(self, data: str) -> List[Network]:
        return [Network.from_dict(row) for row in json.loads(data)]

    def list(self) -> List[Network]:
        if self.dokku.version() >= (0, 35, 3):
            # Support for `--format json` was added on 0.35.3: <https://github.com/dokku/dokku/releases/tag/v0.35.3>
            stdout = self._evaluate("list", params=["--format", "json"], execute=True)
            return self._parse_list_json(stdout)
        else:
            # For older versions the `network:list` command only provides the names of the networks. If we want to get
            # more data, we need to run `docker network inspect`.
            stdout = self._evaluate("list", params=[], execute=True)
            network_names = REGEXP_DOKKU_HEADER.split(stdout.strip())[1:][0].splitlines()[1:]
            if not network_names:  # Would be weird (since Docker has default networks), but better check
                rows = []
            elif self.dokku.can_execute_regular_commands:
                command = Command(["docker", "network", "inspect"] + network_names, sudo=self.dokku.requires_sudo)
                _, stdout, _ = self.dokku._execute(command)  # will execute using SSH connection, if configured to
                data = json.loads(stdout)
                rows = [
                    {
                        "Name": row["Name"],
                        "ID": row["Id"],
                        "Driver": row["Driver"],
                        "Scope": row["Scope"],
                        "CreatedAt": row["Created"],
                        "Internal": row["Internal"],
                        "IPv6": row["EnableIPv6"],
                        "Labels": row["Labels"],
                    }
                    for row in data
                ]
            else:
                # Worst case: there are networks and we can't execute `docker network inspect` to get additional data
                rows = [{"Name": name} for name in network_names]
            return [Network.from_dict(row) for row in rows]

    def set(self, app_name: Union[str, None], key: str, value: Any, execute: bool = True) -> Union[str, Command]:
        return self.set_many(app_name=app_name, key=key, values=[value], execute=execute)

    def set_many(
        self, app_name: Union[str, None], key: str, values: List[str], execute: bool = True
    ) -> Union[str, Command]:
        system = app_name is None
        app_parameter = app_name if not system else "--global"
        params = [app_parameter, key]
        for value in values:
            if isinstance(value, bool):  # bind-all-interfaces
                value = str(value).lower()
            else:
                value = str(value)
            params.append(value)
        return self._evaluate("set", params=params, execute=execute)

    def unset(self, app_name: Union[str, None], key: str, execute: bool = True) -> Union[str, Command]:
        system = app_name is None
        app_parameter = app_name if not system else "--global"
        return self._evaluate("set", params=[app_parameter, key], execute=execute)

    @lru_cache
    def _get_rows_parser(self):
        # XXX: don't know what the 'Network web listeners' property means. Is it global-related? Global can't be
        # set for `static-web-listeners` (which would be the app-equivalent)
        return get_stdout_rows_parser(
            normalize_keys=True,
            remove_prefix="network_",
            discards=[
                "computed_attach_post_create",
                "computed_attach_post_deploy",
                "computed_bind_all_interfaces",
                "computed_initial_network",
                "computed_tld",
                "web_listeners",
            ],
            parsers={
                "attach_post_create": parse_comma_separated_list,
                "attach_post_deploy": parse_comma_separated_list,
                "bind_all_interfaces": parse_bool,
                "global_attach_post_create": parse_comma_separated_list,
                "global_attach_post_deploy": parse_comma_separated_list,
                "global_bind_all_interfaces": parse_bool,
            },
        )

    def _convert_rows(self, parsed_rows: List[dict], skip_system: bool = False) -> List[AppNetwork]:
        result = []
        for row in parsed_rows:
            if not result and not skip_system:
                global_row = {
                    key.replace("global_", ""): value for key, value in row.items() if key.startswith("global_")
                }
                result.append(AppNetwork(app_name=None, **global_row))
            app_row = {key: value for key, value in row.items() if not key.startswith("global_")}
            result.append(AppNetwork(**app_row))
        return result

    def report(self, app_name: Union[str, None] = None) -> List[AppNetwork]:
        system = app_name is None
        # `dokku network:report --format json` is useless since it does not contain the app name!
        # Dokku WILL return error in this `report` command, so `check=False` is used in all `:report/list` because of
        # this inconsistent behavior <https://github.com/dokku/dokku/issues/7454>
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
            raise RuntimeError(f"Error executing network:report: {stderr}")
        rows_parser = self._get_rows_parser()
        parsed_rows = rows_parser(stdout)
        return self._convert_rows(parsed_rows, skip_system=app_name is not None)

    def rebuild(self, app_name: Union[str, None], execute: bool = True) -> Union[str, Command]:
        system = app_name is None
        if system:
            subcommand, params = "rebuildall", []
        else:
            subcommand, params = "rebuild", [app_name]
        return self._evaluate(subcommand, params=params, execute=execute)

    def object_list(self, apps: List[App], system: bool = True) -> List[Union[Network, AppNetwork]]:
        apps_names = [app.name for app in apps]
        result = []
        result.extend(self.list())
        if system:
            result.extend([obj for obj in self.report() if obj.app_name in [None] + apps_names])
        else:
            result.extend([self.report(app_name=app_name) for app_name in apps_names])
        return result

    def object_create(
        self, obj: Union[Network, AppNetwork], skip_system: bool = False, execute: bool = True
    ) -> Union[List[str], List[Command]]:
        result = []
        if isinstance(obj, Network):
            if obj.labels is not None and "com.dokku.network-name" in obj.labels:  # Create only Dokku-created networks
                result.append(self.create(name=obj.name, execute=execute))
        elif isinstance(obj, AppNetwork):
            app_name = obj.app_name
            if obj.attach_post_create:
                result.append(
                    self.set_many(
                        app_name=app_name, key="attach-post-create", values=obj.attach_post_create, execute=execute
                    )
                )
            if obj.attach_post_deploy:
                result.append(
                    self.set_many(
                        app_name=app_name, key="attach-post-deploy", values=obj.attach_post_deploy, execute=execute
                    )
                )
            if obj.initial_network is not None:
                result.append(
                    self.set(app_name=app_name, key="initial-network", value=obj.initial_network, execute=execute)
                )
            if obj.bind_all_interfaces is not None:
                result.append(
                    self.set(
                        app_name=app_name, key="bind-all-interfaces", value=obj.bind_all_interfaces, execute=execute
                    )
                )
            if obj.static_web_listener is not None:
                result.append(
                    self.set(
                        app_name=app_name, key="static-web-listener", value=obj.static_web_listener, execute=execute
                    )
                )
            if obj.tld is not None:
                result.append(self.set(app_name=app_name, key="tld", value=obj.tld, execute=execute))
        return result
