import datetime
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List

from ..utils import parse_bool, parse_timestamp
from .base import DokkuPlugin

REGEXP_HEADER = re.compile("^=====> ", flags=re.MULTILINE)
REGEXP_APP_METADATA = re.compile(r"App\s+([^:]+):\s*(.*)")


@dataclass
class App:
    name: str
    created_at: datetime.datetime
    dir: Path
    locked: bool
    deploy_source: str = None
    deploy_source_metadata: str = None

    def serialize(self):
        return asdict(self)


class AppsPlugin(DokkuPlugin):
    name = "apps"
    object_class = App

    def list(self) -> List[str]:
        _, stdout, stderr = self._execute("report", check=False)
        if not stdout and "You haven't deployed any applications yet" in stderr:
            return []
        apps_infos = REGEXP_HEADER.split(stdout)[1:]
        result = []
        for app_info in apps_infos:
            lines = app_info.splitlines()
            keys_values = [REGEXP_APP_METADATA.findall(line.strip())[0] for line in lines[1:]]
            row = {
                "name": lines[0].split()[0],
                **{key.replace(" ", "_"): value or None for key, value in keys_values},
            }
            row["created_at"] = parse_timestamp(row["created_at"])
            row["dir"] = Path(row["dir"])
            row["locked"] = parse_bool(row["locked"])
            result.append(self.object_class(**row))
        return result

    def create(self, name: str, execute: bool = True) -> str | dict:
        cmd_spec = {"command": "create", "params": [name]}
        if not execute:
            return cmd_spec
        _, stdout, _ = self._execute(**cmd_spec)
        return stdout

    def destroy(self, name: str, execute: bool = True) -> str | dict:
        cmd_spec = {"command": "destroy", "params": [name], "stdin": name}
        if not execute:
            return cmd_spec
        _, stdout, _ = self._execute(**cmd_spec)
        return stdout

    def clone(self, old_name: str, new_name: str, execute: bool = True) -> str | dict:
        cmd_spec = {"command": "clone", "params": [old_name, new_name]}
        if not execute:
            return cmd_spec
        _, stdout, _ = self._execute(**cmd_spec)
        return stdout

    def lock(self, name: str, execute: bool = True) -> str | dict:
        cmd_spec = {"command": "lock", "params": [name]}
        if not execute:
            return cmd_spec
        _, stdout, _ = self._execute(**cmd_spec)
        return stdout

    def unlock(self, name: str, execute: bool = True) -> str | dict:
        cmd_spec = {"command": "unlock", "params": [name]}
        if not execute:
            return cmd_spec
        _, stdout, _ = self._execute(**cmd_spec)
        return stdout

    def locked(self, name: str) -> str:
        _, stdout, stderr = self._execute("unlock", [name], check=False)
        return bool(stdout)

    def rename(self, old_name: str, new_name: str, execute: bool = True) -> str | dict:
        cmd_spec = {"command": "rename", "params": [old_name, new_name]}
        if not execute:
            return cmd_spec
        _, stdout, _ = self._execute(**cmd_spec)
        return stdout

    def ensure_object(self, obj: App, execute: bool = True) -> List:
        result = [self.create(name=obj.name, execute=execute)]
        if obj.locked:
            result.append(self.lock(name=obj.name, execute=execute))
        return result
