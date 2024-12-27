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
            result.append(App(**row))
        return result

    def create(self, name: str) -> str:
        _, stdout, _ = self._execute("create", [name])
        return stdout

    def destroy(self, name: str) -> str:
        _, stdout, _ = self._execute("destroy", [name], stdin=name)
        return stdout

    def clone(self, old_name: str, new_name: str) -> str:
        _, stdout, _ = self._execute("clone", [old_name, new_name])
        return stdout

    def lock(self, name: str) -> str:
        _, stdout, _ = self._execute("lock", [name])
        return stdout

    def unlock(self, name: str) -> str:
        _, stdout, _ = self._execute("unlock", [name])
        return stdout

    def locked(self, name: str) -> str:
        _, stdout, stderr = self._execute("unlock", [name], check=False)
        return bool(stdout)

    def rename(self, old_name: str, new_name: str) -> str:
        _, stdout, _ = self._execute("rename", [old_name, new_name])
        return stdout
