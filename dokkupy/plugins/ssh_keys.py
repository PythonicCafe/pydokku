import json
import re
from pathlib import Path
from typing import List

from ..models import App, Command, SSHKey
from ..utils import clean_stderr
from .base import DokkuPlugin




class SSHKeysPlugin(DokkuPlugin):
    name = "ssh-keys"
    object_class = SSHKey

    def list(self) -> List[SSHKey]:
        _, stdout, stderr = self._evaluate("list", ["--format", "json"], check=False, full_return=True)
        if "No public keys found" in stderr:
            return []
        keys = []
        for item in json.loads(stdout):
            name, fingerprint = item.pop("name"), item.pop("fingerprint")
            keys.append(self.object_class(name=name, fingerprint=fingerprint, public_key=None))
        return keys

    def add(self, name: str, key: str | Path, execute: bool = True) -> str | Command:
        """Add a SSH key to Dokku

    def add(self, key: SSHKey, execute: bool = True) -> str | Command:
        """Add a SSH key to Dokku"""
        if key.public_key is None:
            raise ValueError(f"Cannot add an empty public key")
        result = self._evaluate(
            "add",
            params=[key.name],
            stdin=key.public_key + "\n",
            sudo=True,
            execute=execute,
            check=False,
            full_return=True,
        )
        if not execute:
            return result
        _, stdout, stderr = result
        if stderr:
            raise ValueError(f"Cannot add SSH key: {clean_stderr(stderr)}")
        return stdout

    def remove(self, key: SSHKey, execute: bool = True) -> str | Command:
        # WARNING: Dokku won't throw an error if you try to delete an unexisting key
        if not key.name and not key.fingerprint:
            raise ValueError("A key name or fingerprint is needed so it can be removed")
        is_fingerprint = key.name is None
        params = ["--fingerprint", key.fingerprint] if is_fingerprint else [key.name]
        return self._evaluate("remove", params=params, sudo=True, execute=execute)

    def dump_all(self, apps: List[App]) -> List[dict]:
        return [obj.serialize() for obj in self.list()]

    def create_object(self, obj: SSHKey, execute: bool = True) -> List[str] | List[Command]:
        return [self.add(obj, execute=execute)]
