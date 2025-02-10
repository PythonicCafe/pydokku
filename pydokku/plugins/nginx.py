import datetime
from functools import lru_cache
from typing import Any, List, Union

from ..models import App, Command, Feature, Nginx
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
    features = [
        Feature(name="requires_extra_commands", is_available=Feature.never),
        Feature(
            name="global_settings",
            is_available=Feature.from_version,
            dokku_version=(0, 35, 2),
            dokku_git_commit="e70169f591e4d4db01bb55d289503f9e17d85aa9",
            description="Old versions do not support setting global config for this plugin",
        ),
        Feature(
            name="set:access-log-format",
            is_available=Feature.from_version,
            dokku_version=(0, 22, 0),
            dokku_git_commit="c0581a0e375a24f0fca77b9c01876573f2168bd7",
        ),
        Feature(
            name="set:access-log-path",
            is_available=Feature.from_version,
            dokku_version=(0, 20, 1),
            dokku_git_commit="62caa85423f9ab2d4e7d01e9e57226359bc7b7f8",
        ),
        Feature(
            name="set:bind-address-ipv4",
            is_available=Feature.from_version,
            dokku_version=(0, 19, 12),
            dokku_git_commit="6b431378a15207e7a74579094496dc82990bb0bd",
        ),
        Feature(
            name="set:bind-address-ipv6",
            is_available=Feature.from_version,
            dokku_version=(0, 19, 12),
            dokku_git_commit="6b431378a15207e7a74579094496dc82990bb0bd",
        ),
        Feature(
            name="set:client-body-timeout",
            is_available=Feature.from_version,
            dokku_version=(0, 35, 6),
            dokku_git_commit="4d7f779c28f5a5866a3d3a730084aebea61b581c",
        ),
        Feature(
            name="set:client-header-timeout",
            is_available=Feature.from_version,
            dokku_version=(0, 35, 6),
            dokku_git_commit="4d7f779c28f5a5866a3d3a730084aebea61b581c",
        ),
        Feature(
            name="set:client-max-body-size",
            is_available=Feature.from_version,
            dokku_version=(0, 23, 0),
            dokku_git_commit="277e9691e1dd07b532da977d1f7022aa7fc3549a",
        ),
        Feature(
            name="set:disable-custom-config",
            is_available=Feature.from_version,
            dokku_version=(0, 22, 0),
            dokku_git_commit="f5ba843cf30cbe9d7ce41b0795451fb584994836",
        ),
        Feature(
            name="set:error-log-path",
            is_available=Feature.from_version,
            dokku_version=(0, 20, 1),
            dokku_git_commit="62caa85423f9ab2d4e7d01e9e57226359bc7b7f8",
        ),
        Feature(
            name="set:hsts",
            is_available=Feature.from_version,
            dokku_version=(0, 20, 0),
            dokku_git_commit="73e7ff7b18c7324b60e849bbc00e40573c64dedd",
        ),
        Feature(
            name="set:hsts-include-subdomains",
            is_available=Feature.from_version,
            dokku_version=(0, 20, 0),
            dokku_git_commit="73e7ff7b18c7324b60e849bbc00e40573c64dedd",
        ),
        Feature(
            name="set:hsts-max-age",
            is_available=Feature.from_version,
            dokku_version=(0, 20, 0),
            dokku_git_commit="73e7ff7b18c7324b60e849bbc00e40573c64dedd",
        ),
        Feature(
            name="set:hsts-preload",
            is_available=Feature.from_version,
            dokku_version=(0, 20, 0),
            dokku_git_commit="73e7ff7b18c7324b60e849bbc00e40573c64dedd",
        ),
        Feature(
            name="set:keepalive-timeout",
            is_available=Feature.from_version,
            dokku_version=(0, 35, 6),
            dokku_git_commit="4d7f779c28f5a5866a3d3a730084aebea61b581c",
        ),
        Feature(
            name="set:lingering-timeout",
            is_available=Feature.from_version,
            dokku_version=(0, 35, 6),
            dokku_git_commit="4d7f779c28f5a5866a3d3a730084aebea61b581c",
        ),
        Feature(
            name="set:nginx-conf-sigil-path",
            is_available=Feature.from_version,
            dokku_version=(0, 29, 0),
            dokku_git_commit="17814d484717e17a38912c1bf4a370b053e88ecc",
        ),
        Feature(
            name="set:proxy-buffer-size",
            is_available=Feature.from_version,
            dokku_version=(0, 22, 0),
            dokku_git_commit="30414cbd0c5eb55891984740a6cab86f401d622b",
        ),
        Feature(
            name="set:proxy-buffering",
            is_available=Feature.from_version,
            dokku_version=(0, 22, 0),
            dokku_git_commit="30414cbd0c5eb55891984740a6cab86f401d622b",
        ),
        Feature(
            name="set:proxy-buffers",
            is_available=Feature.from_version,
            dokku_version=(0, 22, 0),
            dokku_git_commit="30414cbd0c5eb55891984740a6cab86f401d622b",
        ),
        Feature(
            name="set:proxy-busy-buffers-size",
            is_available=Feature.from_version,
            dokku_version=(0, 22, 0),
            dokku_git_commit="30414cbd0c5eb55891984740a6cab86f401d622b",
        ),
        Feature(
            name="set:proxy-connect-timeout",
            is_available=Feature.from_version,
            dokku_version=(0, 35, 6),
            dokku_git_commit="4d7f779c28f5a5866a3d3a730084aebea61b581c",
        ),
        Feature(
            name="set:proxy-read-timeout",
            is_available=Feature.from_version,
            dokku_version=(0, 21, 0),
            dokku_git_commit="42122a7540a22dd9eebee5455393564e7014dda7",
        ),
        Feature(
            name="set:proxy-send-timeout",
            is_available=Feature.from_version,
            dokku_version=(0, 35, 6),
            dokku_git_commit="4d7f779c28f5a5866a3d3a730084aebea61b581c",
        ),
        Feature(
            name="set:send-timeout",
            is_available=Feature.from_version,
            dokku_version=(0, 35, 6),
            dokku_git_commit="4d7f779c28f5a5866a3d3a730084aebea61b581c",
        ),
        Feature(
            name="set:underscore-in-headers",
            is_available=Feature.from_version,
            dokku_version=(0, 33, 8),
            dokku_git_commit="b99c25f090e03a64b01ac7ee54825b414e2d551c",
        ),
        Feature(
            name="set:x-forwarded-for-value",
            is_available=Feature.from_version,
            dokku_version=(0, 23, 0),
            dokku_git_commit="a6062d4ab4c28758c29c397301f0dc52cfa7af07",
        ),
        Feature(
            name="set:x-forwarded-port-value",
            is_available=Feature.from_version,
            dokku_version=(0, 23, 0),
            dokku_git_commit="a6062d4ab4c28758c29c397301f0dc52cfa7af07",
        ),
        Feature(
            name="set:x-forwarded-proto-value",
            is_available=Feature.from_version,
            dokku_version=(0, 23, 0),
            dokku_git_commit="a6062d4ab4c28758c29c397301f0dc52cfa7af07",
        ),
        Feature(
            name="set:x-forwarded-ssl",
            is_available=Feature.from_version,
            dokku_version=(0, 23, 7),
            dokku_git_commit="f7e218637ec9bff002899eed35241f64b5e2c0ea",
        ),
    ]

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
            if app_name is None and not self.has("global_settings"):
                # Old versions do not support setting global config for this plugin
                continue
            if value is None:
                result.append(self.unset(app_name=app_name, key=field_name.replace("_", "-"), execute=execute))
            else:
                property_name = field_name.replace("_", "-")
                if self.has(f"set:{property_name}"):
                    result.append(self.set(app_name=app_name, key=property_name, value=value, execute=execute))
        return result
