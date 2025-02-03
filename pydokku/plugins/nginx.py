import datetime
from functools import lru_cache
from typing import Any, List, Union

from ..models import App, Command, Nginx
from ..utils import (
    dataclass_field_set,
    get_stdout_rows_parser,
    parse_bool,
    parse_path,
    parse_timedelta_seconds,
    parse_timestamp,
)
from .base import DokkuPlugin


class NginxPlugin(DokkuPlugin):
    """
    dokku core nginx plugin

    Subcommands NOT implemented: none.

    Extra features:
    - `list()` will add a global object
    """

    name = subcommand = "nginx"
    plugin_name = "nginx-vhosts"
    object_classes = (Nginx,)
    requires = ("apps", "domains", "ports", "proxy", "redirect")
    requires_extra_commands = False

    @lru_cache
    def _get_rows_parser(self):
        return get_stdout_rows_parser(
            normalize_keys=True,
            remove_prefix="nginx_",
            discards=[
                "computed_access_log_format",
                "computed_access_log_path",
                "computed_bind_address_ipv4",
                "computed_bind_address_ipv6",
                "computed_client_body_timeout",
                "computed_client_header_timeout",
                "computed_client_max_body_size",
                "computed_disable_custom_config",
                "computed_error_log_path",
                "computed_hsts_include_subdomains",
                "computed_hsts_max_age",
                "computed_hsts_preload",
                "computed_hsts",
                "computed_keepalive_timeout",
                "computed_lingering_timeout",
                "computed_nginx_conf_sigil_path",
                "computed_proxy_buffer_size",
                "computed_proxy_buffering",
                "computed_proxy_buffers",
                "computed_proxy_busy_buffers_size",
                "computed_proxy_connect_timeout",
                "computed_proxy_read_timeout",
                "computed_proxy_send_timeout",
                "computed_send_timeout",
                "computed_underscore_in_headers",
                "computed_x_forwarded_for_value",
                "computed_x_forwarded_port_value",
                "computed_x_forwarded_proto_value",
                "computed_x_forwarded_ssl",
            ],
            parsers={
                "access_log_path": parse_path,
                "disable_custom_config": parse_bool,
                "error_log_path": parse_path,
                "global_access_log_path": parse_path,
                "global_disable_custom_config": parse_bool,
                "global_error_log_path": parse_path,
                "global_hsts": parse_bool,
                "global_hsts_include_subdomains": parse_bool,
                "global_hsts_max_age": parse_timedelta_seconds,
                "global_hsts_preload": parse_bool,
                "global_nginx_conf_sigil_path": parse_path,
                "hsts": parse_bool,
                "hsts_include_subdomains": parse_bool,
                "hsts_max_age": parse_timedelta_seconds,
                "hsts_preload": parse_bool,
                "last_visited_at": parse_timestamp,
                "nginx_conf_sigil_path": parse_path,
            },
        )

    def _convert_rows(self, parsed_rows: List[dict], skip_system: bool = False) -> List[Nginx]:
        result = []
        for row in parsed_rows:
            global_row = {key[len("global_") :]: value for key, value in row.items() if key.startswith("global_")}
            app_row = {key: value for key, value in row.items() if not key.startswith("global_")}
            for key in ("access_log_path", "error_log_path"):
                # The actual log paths are from the app, not really "global". Since 'computed' values are ignored, a
                # fix is made for these fields.
                if app_row[key] is None:
                    app_row[key] = global_row[key]
                global_row[key] = None
            if not result and not skip_system:
                result.append(Nginx(app_name=None, **global_row))
            result.append(Nginx(**app_row))
        return result

    def list(self, app_name: Union[str, None] = None) -> Union[str, Command]:
        # Dokku won't return error in this `report` command, but `check=False` is used in all `:report/list` because of
        # this inconsistent behavior <https://github.com/dokku/dokku/issues/7454>
        system = app_name is None
        stdout = self._evaluate("report", params=[] if system else [app_name], check=False, execute=True)
        rows_parser = self._get_rows_parser()
        parsed_rows = rows_parser(stdout)
        result = []
        for index, row in enumerate(parsed_rows):
            result.extend(self._convert_rows(parsed_rows=[row], skip_system=index > 0))
        return result

    def access_logs(self, app_name: str, execute: bool = True) -> Union[str, Command]:
        return self._evaluate("access-logs", params=[app_name], execute=execute)

    def error_logs(self, app_name: str, execute: bool = True) -> Union[str, Command]:
        return self._evaluate("error-logs", params=[app_name], execute=execute)

    def set(self, app_name: Union[str, None], key: str, value: Any, execute: bool = True) -> Union[str, Command]:
        system = app_name is None
        app_parameter = app_name if not system else "--global"
        if isinstance(value, bool):
            value = str(value).lower()
        elif isinstance(value, datetime.timedelta):
            value = str(int(value.total_seconds()))
        else:
            value = str(value)
        return self._evaluate("set", params=[app_parameter, key, value], execute=execute)

    def unset(self, app_name: Union[str, None], key: str, execute: bool = True) -> Union[str, Command]:
        system = app_name is None
        app_parameter = app_name if not system else "--global"
        return self._evaluate("set", params=[app_parameter, key], execute=execute)

    def start(self, execute: bool = True) -> Union[str, Command]:
        return self._evaluate("start", execute=execute)

    def stop(self, execute: bool = True) -> Union[str, Command]:
        return self._evaluate("stop", execute=execute)

    def get_config(self, app_name: str) -> Union[str, Command]:
        return self._evaluate("show-config", params=[app_name], check=True, execute=True)

    def validate_config(
        self, app_name: Union[str, None] = None, clean: bool = False, execute: bool = True
    ) -> Union[str, Command]:
        params = []
        if app_name is not None:
            params.append(app_name)
        if clean:
            params.append("--clean")
        return self._evaluate("validate-config", params=params, execute=execute)

    def object_list(self, apps: List[App], system: bool = True) -> List[Nginx]:
        apps_names = [app.name for app in apps]
        if system:
            return [obj for obj in self.list() if obj.app_name in [None] + apps_names]
        else:
            result = []
            for app_name in apps_names:
                for obj in self.list(app_name=app_name):
                    if obj.app_name == app_name:
                        serialized = obj.serialize()
                        # Filter out "empty" objects (log paths will always be filled with default values)
                        distinct_values = set(
                            value
                            for key, value in serialized.items()
                            if key not in ("app_name", "access_log_path", "error_log_path")
                        )
                        if distinct_values != {None}:
                            result.append(obj)
            return result

    def object_create(
        self, obj: Nginx, skip_system: bool = False, execute: bool = True
    ) -> Union[List[str], List[Command]]:
        # This command ignores `skip_system` since there's an object dedicated to global configs.
        app_name = obj.app_name
        result = []
        for field_name in dataclass_field_set(Nginx):
            if field_name in ("app_name", "last_visited_at"):  # Not actual properties to set
                continue
            value = getattr(obj, field_name)
            if value is None:
                result.append(self.unset(app_name=app_name, key=field_name.replace("_", "-"), execute=execute))
            else:
                result.append(
                    self.set(app_name=app_name, key=field_name.replace("_", "-"), value=value, execute=execute)
                )
        return result
