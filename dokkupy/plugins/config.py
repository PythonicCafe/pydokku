import base64
import json
from typing import List

from ..models import Command
from .base import DokkuPlugin


class ConfigPlugin(DokkuPlugin):
    name = "config"
    object_class = dict

    def get(self, app_name: str, merged: bool = False) -> dict:
        # `dokku config <--global|app_name>` does not encode values, so we can't parse correctly if values have
        # newlines or other special chars. We use `config:export --format=json` instead.
        system = app_name is None
        params = ["--format", "json"]
        if merged:
            params.append("--merged")
        params.append("--global" if system else app_name)
        stdout = self._evaluate("export", params=params)
        return json.loads(stdout)

    def set_many(self, app_name: str, keys_values: dict, restart: bool = False, execute: bool = True) -> str | Command:
        system = app_name is None
        if system and restart:
            raise ValueError("Cannot restart when setting global config")
        encoded_pairs = {
            key: base64.b64encode(str(value if value is not None else "").encode("utf-8")).decode("ascii")
            for key, value in keys_values.items()
        }
        params = ["--encoded"]
        if not restart and not system:
            params.append("--no-restart")
        params.append("--global" if system else app_name)
        params.extend([f"{key}={value}" for key, value in encoded_pairs.items()])
        return self._evaluate("set", params=params, execute=execute)

    def set(self, app_name: str, key: str, value: str, restart: bool = False, execute: bool = True) -> str | Command:
        return self.set_many(app_name=app_name, keys_values={key: value}, restart=restart, execute=execute)

    def unset_many(self, app_name: str, keys: List[str], restart: bool = False, execute: bool = True) -> str | Command:
        system = app_name is None
        if system and restart:
            raise ValueError("Cannot restart when unsetting global config")
        params = []
        if not restart and not system:
            params.append("--no-restart")
        params.append("--global" if system else app_name)
        params.extend(keys)
        return self._evaluate("unset", params=params, execute=execute)

    def unset(self, app_name: str, key: str, restart: bool = False, execute: bool = True) -> str | Command:
        return self.unset_many(app_name=app_name, keys=[key], restart=restart, execute=execute)

    def clear(self, app_name: str, restart: bool = False, execute: bool = True) -> str | Command:
        system = app_name is None
        if system and restart:
            raise ValueError("Cannot restart when clearing global config")
        params = []
        if not restart and not system:
            params.append("--no-restart")
        params.append("--global" if system else app_name)
        return self._evaluate("clear", params=params, execute=execute)

    # TODO: implement `dump`
    # TODO: implement `ensure_object`
