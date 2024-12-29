import base64
import json
from itertools import groupby
from typing import Iterator, List

from ..models import App, Command, Config
from .base import DokkuPlugin


class ConfigPlugin(DokkuPlugin):
    name = "config"
    object_class = Config

    def get(self, app_name: str, merged: bool = False, as_dict: bool = False) -> List[Config] | dict:
        """Get all configurations set for an app, with the option to merge them with the global ones"""
        # `dokku config <--global|app_name>` does not encode values, so we can't parse correctly if values have
        # newlines or other special chars. We use `config:export --format=json` instead.
        system = app_name is None
        params = ["--format", "json"]
        if merged:
            params.append("--merged")
        params.append("--global" if system else app_name)
        stdout = self._evaluate("export", params=params)
        data = json.loads(stdout)
        if as_dict:
            return data
        return [Config(app_name=app_name, key=key, value=value) for key, value in data.items()]

    def set_many(self, configs: List[Config], restart: bool = False, execute: bool = True) -> str | Command:
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

    def set_many_dict(self, app_name: str, keys_values: dict, restart: bool = False, execute: bool = True) -> str | Command:
        """Utility method so you don't need to convert a `dict` into a list of `Config` objects to set many"""
        configs = [Config(app_name=app_name, key=key, value=value) for key, value in keys_values.items()]
        return self.set_many(configs=configs, restart=restart, execute=execute)

    def set(self, config: Config, restart: bool = False, execute: bool = True) -> str | Command:
        return self.set_many(configs=[config], restart=restart, execute=execute)

    def unset_many(self, configs: List[Config], restart: bool = False, execute: bool = True) -> str | Command:
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

    def unset_many_list(self, app_name: str, keys: List[str], restart: bool = False, execute: bool = True) -> str | Command:
        """Utility method so you don't need to convert a list of keys into a list of `Config` objects to unset many"""
        configs = [Config(app_name=app_name, key=key, value=None) for key in keys]
        return self.unset_many(configs=configs, restart=restart, execute=execute)

    def unset(self, config: Config, restart: bool = False, execute: bool = True) -> str | Command:
        return self.unset_many(configs=[config], restart=restart, execute=execute)

    def clear(self, app_name: str, restart: bool = False, execute: bool = True) -> str | Command:
        system = app_name is None
        if system and restart:
            raise ValueError("Cannot restart when clearing global config")
        params = []
        if not restart and not system:
            params.append("--no-restart")
        params.append("--global" if system else app_name)
        return self._evaluate("clear", params=params, execute=execute)

    def dump_all(self, apps: List[App]) -> List[Config]:
        app_names = [None] + [app.name for app in apps]
        result = []
        for app_name in app_names:
            objs = self.get(app_name=app_name)
            result.extend([obj.serialize() for obj in objs])
        return result

    def create_object(self, obj: Config, execute: bool = True) -> List[str] | List[Command]:
        return [self.set_many(configs=[obj], restart=False, execute=execute)]

    def create_objects(self, objs: List[Config], execute: bool = True) -> Iterator[str] | Iterator[Command]:
        sort_func = lambda obj: obj.app_name
        objs.sort(key=sort_func)
        groups = groupby(objs, key=sort_func)
        for app_name, configs in groups:
            configs = list(configs)
            if not execute:
                yield self.set_many(configs=list(configs), restart=False, execute=execute)
            else:
                # We're using a bulk operation that returns only one string (not a list of them) for a list of objects,
                # so we can't use `yield from`
                yield self.set_many(configs=list(configs), restart=False, execute=execute)
