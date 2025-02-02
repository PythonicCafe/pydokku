import datetime
from typing import Any, Dict, List, Union

from ..models import App, Command, LetsEncrypt
from ..utils import clean_stderr, get_system_tzinfo, parse_iso_format, parse_timedelta
from .base import DokkuPlugin


class LetsEncryptPlugin(DokkuPlugin):
    """
    dokku letsencrypt plugin

    Subcommands NOT implemented:
    - `letsencrypt:help`: not needed

    Extra features:
    - In `list(): absolute datetime of renewal is calculated based on expirity date and time before expires, so we always
      have absolute datetimes and don't need to know when the `:list` command ran.
    - The `list()` method, after running `:list` will also try to read plugin config (to get properties set for each
      app) and run `:active` to check if is enabled (if the user has the permission to do so).
    - `letsencrypt:set`: was split in `set()` and `unset()` methods
    """

    name = subcommand = plugin_name = "letsencrypt"
    object_classes = (LetsEncrypt,)
    requires = ("apps", "domains", "proxy", "nginx")
    requires_extra_commands = True

    def _parse_list(self, stdout: str) -> List[Dict]:
        lines = stdout.strip().splitlines()
        result = []
        for line in lines[1:]:
            app_name, rest = line.split(" ", maxsplit=1)
            info = [item.strip() for item in rest.strip().split("  ") if item.strip()]
            expires_at = parse_iso_format(info[0]).replace(tzinfo=get_system_tzinfo())
            expires_in = parse_timedelta(info[1])
            renewals_in = parse_timedelta(info[2])
            ran_at = expires_at - expires_in
            renewals_at = ran_at + renewals_in
            result.append(
                {
                    "app_name": app_name,
                    "expires_at": expires_at,
                    "renewals_at": renewals_at,
                }
            )
        return result

    def enable(self, app_name: str, execute: bool = True) -> Union[str, Command]:
        return self._evaluate("enable", params=[app_name], execute=execute)

    def disable(self, app_name: str, execute: bool = True) -> Union[str, Command]:
        return self._evaluate("disable", params=[app_name], execute=execute)

    def active(self, app_name: str) -> bool:
        _, stdout, stderr = self._evaluate("active", params=[app_name], check=False, full_return=True, execute=True)
        stderr = clean_stderr(stderr)
        if "does not exist" in stderr:
            return []
        elif stderr:
            raise RuntimeError(f"Error executing letsencrypt:active: {stderr}")
        return {"true": True, "false": False}[stdout.strip().lower()]

    def cleanup(self, app_name: str, execute: bool = True) -> Union[str, Command]:
        return self._evaluate("cleanup", params=[app_name], execute=execute)

    def revoke(self, app_name: str, execute: bool = True) -> Union[str, Command]:
        return self._evaluate("revoke", params=[app_name], execute=execute)

    def auto_renew(self, app_name: Union[str, None], execute: bool = True) -> Union[str, Command]:
        return self._evaluate("auto-renew", params=[] if app_name is None else [app_name], execute=execute)

    def cron_job_add(self, execute: bool = True) -> Union[str, Command]:
        return self._evaluate("cron-job", params=["--add"], execute=execute)

    def cron_job_remove(self, execute: bool = True) -> Union[str, Command]:
        return self._evaluate("cron-job", params=["--remove"], execute=execute)

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

    def _list(self, apps_names: Union[List[str], None] = None) -> List[LetsEncrypt]:
        # Dokku won't return error in this `list` command, but `check=False` is used in all `:report/list` because of
        # this inconsistent behavior <https://github.com/dokku/dokku/issues/7454>
        _, stdout, stderr = self._evaluate("list", check=False, full_return=True, execute=True)
        stderr = clean_stderr(stderr)
        if "You haven't deployed any applications yet" in stderr:
            return []
        elif stderr:
            raise RuntimeError(f"Error executing letsencrypt:list: {stderr}")
        rows = self._parse_list(stdout)
        if apps_names is not None:
            rows = [row for row in rows if row["app_name"] in apps_names]
        if apps_names is None or None in apps_names:
            # `dokku letsencrypt:list` won't list the global one, but it has options
            rows.insert(0, {"app_name": None, "expires_at": None, "renewals_at": None})
        for row in rows:
            app_name = row["app_name"]
            if self.dokku.can_execute_regular_commands:
                row["options"] = self.dokku.plugin_app_config(
                    plugin_name=self.plugin_name,
                    app_name=app_name if app_name is not None else "--global",
                )
            if app_name is None:
                # If the plugin is enabled and we were able to run the `list` command, then global is enabled
                row["enabled"] = True
            else:
                row["enabled"] = self.active(app_name=app_name)
        return [LetsEncrypt(**row) for row in rows]

    def list(self) -> List[LetsEncrypt]:
        return self._list(apps_names=None)

    def object_list(self, apps: List[App], system: bool = True) -> List[LetsEncrypt]:
        apps_names = [app.name for app in apps]
        if system:
            apps_names = [None] + apps_names
        return self._list(apps_names=apps_names)

    def object_create(
        self, obj: LetsEncrypt, skip_system: bool = False, execute: bool = True
    ) -> Union[List[str], List[Command]]:
        # Since there's a specific object for "system" (having `app_name=None`), `skip_system` is ignored here (it's
        # different from other plugins like `proxy`, where the system object is "hidden" in another object).
        app_name = obj.app_name
        result = []
        if obj.options:
            for key, value in obj.options.items():
                result.append(self.set(app_name=app_name, key=key, value=value, execute=execute))
        if app_name is not None:  # Global object does not need to be enabled/disabled
            if obj.enabled:
                result.append(self.enable(app_name=app_name, execute=execute))
            else:
                result.append(self.disable(app_name=app_name, execute=execute))
        else:
            result.append(self.cron_job_add(execute=execute))
        return result
