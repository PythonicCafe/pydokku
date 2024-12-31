import re
from pathlib import Path
from typing import List

from ..models import App, Command
from ..utils import REGEXP_DOKKU_HEADER, parse_bool, parse_timestamp
from .base import DokkuPlugin

REGEXP_APP_METADATA = re.compile(r"App\s+([^:]+):\s*(.*)")


class AppsPlugin(DokkuPlugin):
    name = "apps"
    object_class = App

    def list(self) -> List[App]:
        _, stdout, stderr = self._evaluate("report", check=False, execute=True, full_return=True)
        if not stdout and "You haven't deployed any applications yet" in stderr:
            return []
        apps_infos = REGEXP_DOKKU_HEADER.split(stdout)[1:]
        result = []
        for app_info in apps_infos:
            lines = app_info.splitlines()
            keys_values = [REGEXP_APP_METADATA.findall(line.strip())[0] for line in lines[1:]]
            row = {key.replace(" ", "_"): value or None for key, value in keys_values}
            row["locked"] = parse_bool(row["locked"])
            result.append(
                self.object_class(
                    name=lines[0].split()[0],
                    path=Path(row["dir"]),
                    locked=parse_bool(row["locked"]),
                    created_at=parse_timestamp(row["created_at"]) if row["created_at"] else None,
                    deploy_source=row.get("deploy_source"),
                    deploy_source_metadata=row.get("deploy_source_metadata"),
                )
            )
        return result

    def create(self, name: str, execute: bool = True) -> str | Command:
        return self._evaluate("create", params=[name], execute=execute)

    def destroy(self, name: str, execute: bool = True) -> str | Command:
        return self._evaluate("destroy", params=[name], stdin=name, execute=execute)

    def clone(self, old_name: str, new_name: str, execute: bool = True) -> str | Command:
        return self._evaluate("clone", params=[old_name, new_name], execute=execute)

    def lock(self, name: str, execute: bool = True) -> str | Command:
        return self._evaluate("lock", params=[name], execute=execute)

    def unlock(self, name: str, execute: bool = True) -> str | Command:
        return self._evaluate("unlock", params=[name], execute=execute)

    def locked(self, name: str) -> bool:
        stdout = self._evaluate("unlock", params=[name], check=False, execute=True)
        return bool(stdout)

    def rename(self, old_name: str, new_name: str, execute: bool = True) -> str | Command:
        return self._evaluate("rename", params=[old_name, new_name], execute=execute)

    def dump_all(self, apps: List[App]) -> List[dict]:
        return [obj.serialize() for obj in apps]

    def create_object(self, obj: App, execute: bool = True) -> List[str] | List[Command]:
        result = [self.create(name=obj.name, execute=execute)]
        if obj.locked:
            result.append(self.lock(name=obj.name, execute=execute))
        return result
