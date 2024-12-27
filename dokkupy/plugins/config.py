import base64
import json
from typing import List

from .base import DokkuPlugin


class ConfigPlugin(DokkuPlugin):
    name = "config"

    def get(self, app_name: str) -> str:
        # `dokku config <--global|app_name>` does not encode values, so we can't parse correctly if values has newlines
        # or other special chars. So we first get the keys and then read each key
        system = app_name is None
        _, stdout, _ = self._execute("export", ["--format=json", "--global" if system else app_name])
        return json.loads(stdout)

    def set_many(self, app_name: str, keys_values: dict, restart: bool = False) -> str:
        system = app_name is None
        if system and restart:
            raise ValueError("Cannot restart when setting global config")
        encoded_pairs = {
            key: base64.b64encode(str(value or "").encode("utf-8")).decode("ascii")
            for key, value in keys_values.items()
        }
        params = ["--encoded"]
        if not restart and not system:
            params.append("--no-restart")
        params.append("--global" if system else app_name)
        params.extend([f"{key}={value}" for key, value in encoded_pairs.items()])
        _, stdout, _ = self._execute("set", params)
        return stdout

    def set(self, app_name: str, key: str, value: str, restart: bool = False) -> str:
        return self.set_many(app_name=app_name, keys_values={key: value}, restart=restart)

    def unset_many(self, app_name: str, keys: List[str], restart: bool = False) -> str:
        system = app_name is None
        if system and restart:
            raise ValueError("Cannot restart when setting global config")
        params = []
        if not restart and not system:
            params.append("--no-restart")
        params.append("--global" if system else app_name)
        params.extend(keys)
        _, stdout, _ = self._execute("unset", params)
        return stdout

    def unset(self, app_name: str, key: str, restart: bool = False) -> str:
        return self.unset_many(app_name=app_name, keys=[key], restart=restart)

    def clear(self, app_name: str, restart: bool = False) -> str:
        system = app_name is None
        if system and restart:
            raise ValueError("Cannot restart when setting global config")
        params = []
        if not restart and not system:
            params.append("--no-restart")
        params.append("--global" if system else app_name)
        _, stdout, _ = self._execute("clear", params)
        return stdout
