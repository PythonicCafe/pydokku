import json
import re
from pathlib import Path
from typing import List, Literal

from ..models import App, Command, Storage
from ..utils import clean_stderr
from .base import DokkuPlugin

REGEXP_ENSURE_DIR = re.compile("-----> Ensuring (.*) exists")
REGEXP_USER_GROUP = re.compile("Setting directory ownership to (.*):(.*)$")
CHOWN_OPTIONS = {
    "herokuish": (32767, 32767),
    "heroku": (1000, 1000),
    "packeto": (2000, 2000),
    "root": (0, 0),
}
ChownType = None
for opt in CHOWN_OPTIONS.keys():
    ChownType |= Literal[opt]
USER_GROUP_ID_CHOWN = {value: key for key, value in CHOWN_OPTIONS.items()}


class StoragePlugin(DokkuPlugin):
    name = "storage"
    object_class = Storage

    # TODO: create helper method to get a storage's size

    def list(self, app_name: str) -> List[Storage]:
        stdout = self._evaluate("list", [app_name, "--format", "json"], check=False)
        result = [
            self.object_class(app_name=app_name, host_path=item["host_path"], container_path=item["container_path"])
            for item in json.loads(stdout)
        ]
        # XXX: if it's running over SSH and the user is `dokku`, we won't be able to execute `stat` to get permission
        # info
        # TODO: add a warning regarding this?
        if result and self.dokku.can_execute_regular_commands:
            if not self.dokku.via_ssh:
                for storage in result:
                    stat = storage.host_path.stat()
                    storage.user_id, storage.group_id = stat.st_uid, stat.st_gid
            else:
                storage_paths = [str(storage.host_path) for storage in result]
                command = Command(["stat", "--format='%u %g'"] + storage_paths, sudo=self.dokku.requires_sudo)
                _, stdout, _ = self.dokku._execute(command)  # will execute using SSH connection
                permissions = stdout.strip().splitlines()
                assert len(permissions) == len(result), f"Got wrong response from `stat`: {repr(stdout)}"
                for storage, permission in zip(result, permissions):
                    storage.user_id, storage.group_id = [int(item) for item in permission.strip().split()]
        return result

    def ensure_directory(
        self, name: str, chown: ChownType = None, execute: bool = True
    ) -> tuple[Path, tuple[int, int]] | Command:
        params = []
        if chown is not None:
            if chown not in CHOWN_OPTIONS.keys():
                raise ValueError(
                    f"Invalid value for chown: {repr(chown)} (expected: {', '.join(CHOWN_OPTIONS.keys())})"
                )
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
            raise RuntimeError(f"Cannot unmount storage for {storage.app_name}: {clean_stderr(stderr)}")
        return stdout

    def dump_all(self, apps: List[App]) -> List[dict]:
        return [obj.serialize() for app in apps for obj in self.list(app.name)]

    def create_object(self, obj: Storage, execute: bool = True) -> List[str] | List[Command]:
        # XXX: if storage's user and group ID can't be found in USER_GROUP_ID_CHOWN, won't apply any chown
        chown = USER_GROUP_ID_CHOWN.get((obj.user_id, obj.group_id))
        return [
            self.ensure_directory(obj.host_path.name, chown=chown, execute=execute),
            self.mount(obj, execute=execute),
        ]
