import json
import re
from pathlib import Path
from typing import List

from .base import DokkuPlugin

REGEXP_ENSURE_DIR = re.compile("-----> Ensuring (.*) exists")
REGEXP_USER_GROUP = re.compile("Setting directory ownership to (.*):(.*)$")


class StoragePlugin(DokkuPlugin):
    name = "storage"
    _chown_options = ("heroku", "herokuish", "packeto", "root")

    def list(self, app_name: str) -> List[dict]:
        _, stdout, _ = self._execute("list", [app_name, "--format", "json"], check=False)
        return json.loads(stdout)

    def ensure_directory(self, name, chown=None):
        if chown is not None and chown not in self._chown_options:
            raise ValueError(f"Invalid value for chown: {repr(chown)} (expected: {', '.join(self._chown_options)})")
        params = [name]
        if chown is not None:
            params.extend(["--chown", chown])
        _, stdout, _ = self._execute("ensure-directory", params)
        lines = stdout.strip().splitlines()
        path = Path(REGEXP_ENSURE_DIR.findall(lines[0])[0])
        user, group = [int(item) for item in REGEXP_USER_GROUP.findall(lines[1])[0]]
        return path, (user, group)

    # TODO: implement storage:list <app> [--format text|json]                 List bind mounts for app's container(s) (host:container)
    # TODO: implement storage:report [<app>] [<flag>]                         Displays a checks report for one or more apps
    # TODO: implement storage:mount <app> <host-dir:container-dir>            Create a new bind mount
    # TODO: implement storage:unmount <app> <host-dir:container-dir>          Remove an existing bind mount
    # TODO: implement storage:ensure-directory [--chown option] <directory>   Creates a persistent storage directory in the recommended storage path
