import base64
import json
from itertools import groupby
from typing import Iterator, List, Union

from ..models import App, Command, Config
from ..utils import get_app_name
from .base import DokkuPlugin


class ConfigPlugin(DokkuPlugin):
    """
    dokku core config plugin

    Subcommands NOT implemented:
    - `config <app>` or `config:show <app>`: `export` is used instead (equivalent data, better format)
    - `config:get`: can be extracted by `get(app_name, as_dict=True)[key]`
    - `config:keys`: list of config keys can be extracted by `get(app_name, as_dict=True).keys()`
    - `config:bundle`: `export` already provides similar feature

    Extra features:
    - `get()`: hide internal Dokku env vars (keys starting with `DOKKU_`)
    """

    name = subcommand = plugin_name = "config"
    object_classes = (Config,)
    requires = ("apps",)
    requires_extra_commands = False

    def get(
        self, app_name: Union[str, None], merged: bool = False, hide_internal: bool = True, as_dict: bool = False
    ) -> Union[List[Config], dict]:
        """Get all configurations set for an app, with the option to merge them with the global ones"""
        # TODO: even if `hide_internal` is `True`, this method will also export internal configs like `NO_VHOST` and
        # `GIT_REV`, which will impact other plugins (like `domains` and `git`). Need to decide whether to
        # export/expose or not these plugin-internal configs or just via the plugins. Since these don't start with
        # `DOKKU_`, a list of "skip vars" must be made manually.
        # `dokku config <--global|app_name>` does not encode values, so we can't parse correctly if values have
        # newlines or other special chars. We use `config:export --format=json` instead.
        system = app_name is None
        params = ["--format", "json"]
        if merged:
            params.append("--merged")
        params.append("--global" if system else app_name)
        stdout = self._evaluate("export", params=params)
        data = json.loads(stdout)
        if hide_internal:
            data = {key: value for key, value in data.items() if not key.startswith("DOKKU_")}
        if as_dict:
            return data
        return [Config(app_name=app_name, key=key, value=value) for key, value in data.items()]

    def set_many(self, configs: List[Config], restart: bool = False, execute: bool = True) -> Union[str, Command]:
        """Set many key-value configuration pairs in one command - for one app only"""
        encoded_pairs = {}
        app_names = set()
        for config in configs:
            app_names.add(config.app_name)
            encoded_value = base64.b64encode(
                str(config.value if config.value is not None else "").encode("utf-8")
            ).decode("ascii")
            encoded_pairs[config.key] = encoded_value
        if len(app_names) != 1:
            raise ValueError(f"`set_many` can only be called for one app (got {len(app_names)})")
        app_name = list(app_names)[0]  # TODO: fix (may be empty)
        system = app_name is None
        if system and restart:
            raise ValueError("Cannot restart when setting global config")
        params = ["--encoded"]
        if not restart and not system:
            params.append("--no-restart")
        params.append("--global" if system else app_name)
        params.extend([f"{key}={value}" for key, value in encoded_pairs.items()])
        return self._evaluate("set", params=params, execute=execute)

    def set_many_dict(
        self, app_name: str, keys_values: dict, restart: bool = False, execute: bool = True
    ) -> Union[str, Command]:
        """Utility method so you don't need to convert a `dict` into a list of `Config` objects to set many"""
        configs = [Config(app_name=app_name, key=key, value=value) for key, value in keys_values.items()]
        return self.set_many(configs=configs, restart=restart, execute=execute)

    def set(self, config: Config, restart: bool = False, execute: bool = True) -> Union[str, Command]:
        return self.set_many(configs=[config], restart=restart, execute=execute)

    def unset_many(self, configs: List[Config], restart: bool = False, execute: bool = True) -> Union[str, Command]:
        keys = []
        app_names = set()
        for config in configs:
            app_names.add(config.app_name)
            keys.append(config.key)
        if len(app_names) > 1:
            raise ValueError(f"`unset_many` cannot be called for multiple apps (got {len(app_names)})")
        app_name = list(app_names)[0]
        system = app_name is None
        if system and restart:
            raise ValueError("Cannot restart when unsetting global config")
        params = []
        if not restart and not system:
            params.append("--no-restart")
        params.append("--global" if system else app_name)
        params.extend(keys)
        return self._evaluate("unset", params=params, execute=execute)

    def unset_many_list(
        self, app_name: str, keys: List[str], restart: bool = False, execute: bool = True
    ) -> Union[str, Command]:
        """Utility method so you don't need to convert a list of keys into a list of `Config` objects to unset many"""
        configs = [Config(app_name=app_name, key=key, value=None) for key in keys]
        return self.unset_many(configs=configs, restart=restart, execute=execute)

    def unset(self, config: Config, restart: bool = False, execute: bool = True) -> Union[str, Command]:
        return self.unset_many(configs=[config], restart=restart, execute=execute)

    def clear(self, app_name: Union[str, None], restart: bool = False, execute: bool = True) -> Union[str, Command]:
        system = app_name is None
        if system and restart:
            raise ValueError("Cannot restart when clearing global config")
        params = []
        if not restart and not system:
            params.append("--no-restart")
        params.append("--global" if system else app_name)
        return self._evaluate("clear", params=params, execute=execute)

    def object_list(self, apps: List[App], system: bool = True) -> List[Config]:
        app_names = [app.name for app in apps]
        if system:
            app_names = [None] + app_names
        result = []
        for app_name in app_names:
            result.extend(self.get(app_name=app_name, hide_internal=True))
        return result

    def object_create(
        self, obj: Config, skip_system: bool = False, execute: bool = True
    ) -> Union[List[str], List[Command]]:
        return [self.set_many(configs=[obj], restart=False, execute=execute)]

    def object_create_many(self, objs: List[Config], execute: bool = True) -> Union[Iterator[str], Iterator[Command]]:
        objs.sort(key=get_app_name)
        groups = groupby(objs, key=get_app_name)
        for app_name, configs in groups:
            yield self.set_many(configs=list(configs), restart=False, execute=execute)
