import json
import re
from pathlib import Path
from typing import List, Literal

from ..models import App, Command, Storage
from ..utils import clean_stderr
from .base import DokkuPlugin

REGEXP_ENSURE_DIR = re.compile("-----> Ensuring (.*) exists")
REGEXP_USER_GROUP = re.compile("Setting directory ownership to (.*):(.*)$")
CHOWN_OPTIONS = ("heroku", "herokuish", "packeto", "root")
ChownType = None
for opt in CHOWN_OPTIONS:
    ChownType |= Literal[opt]


class StoragePlugin(DokkuPlugin):
    name = "storage"
    object_class = Storage

    # TODO: create helper method to get a storage size

    def list(self, app_name: str) -> List[Storage]:
        stdout = self._evaluate("list", [app_name, "--format", "json"], check=False)
        result = []
        for item in json.loads(stdout):
            result.append(
                Storage(
                    host_path=item["host_path"], container_path=item["container_path"], options=item["volume_options"]
                )
            )
        return result

    def ensure_directory(
        self, name: str, chown: ChownType = None, execute: bool = True
    ) -> tuple[Path, tuple[int, int]] | Command:
        params = []
        if chown is not None:
            if chown not in CHOWN_OPTIONS:
                raise ValueError(f"Invalid value for chown: {repr(chown)} (expected: {', '.join(CHOWN_OPTIONS)})")
            params.extend(["--chown", chown])
        params.append(name)
        result = self._evaluate("ensure-directory", params=params, execute=execute)
        if not execute:
            return result
        stdout = result
        lines = stdout.strip().splitlines()
        path = Path(REGEXP_ENSURE_DIR.findall(lines[0])[0])
        user_id, group_id = [int(item) for item in REGEXP_USER_GROUP.findall(lines[1])[0]]
        return path, (user_id, group_id)

    def mount(self, storage: Storage, execute: bool = True) -> str | Command:
        host_path = storage.host_path
        container_path = storage.container_path
        if not host_path.is_absolute():
            raise ValueError(f"`host_path` must be an absolute path (got: {host_path})")
        elif not container_path.is_absolute():
            raise ValueError(f"`container_path` must be an absolute path (got: {container_path})")
        return self._evaluate("mount", params=[storage.app_name, f"{host_path}:{container_path}"], execute=execute)

    def unmount(self, storage: Storage, execute: bool = True) -> str | Command:
        host_path = storage.host_path
        container_path = storage.container_path
        result = self._evaluate(
            "unmount", params=[storage.app_name, f"{host_path}:{container_path}"], execute=execute, full_return=True
        )
        if not execute:
            return result
        _, stdout, stderr = result
        if stderr:
            raise RuntimeError(f"Cannot unmount storage for {app_name}: {clean_stderr(stderr)}")
        return stdout

    # TODO: implement `dump`
    # TODO: implement `ensure_object`
