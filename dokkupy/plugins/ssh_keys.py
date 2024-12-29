import json
import re
from pathlib import Path
from typing import List

from ..models import App, Command, SSHKey
from ..ssh import KEY_TYPES
from ..utils import clean_stderr
from .base import DokkuPlugin

REGEXP_SSH_PUBLIC_KEY = re.compile(f"ssh-({'|'.join(KEY_TYPES)}) AAAA[a-zA-Z0-9+/=]+( [^@]+@[^@]+)?")



class SSHKeysPlugin(DokkuPlugin):
    name = "ssh-keys"
    object_class = SSHKey

    def list(self) -> List[SSHKey]:
        _, stdout, stderr = self._evaluate("list", ["--format", "json"], check=False, full_return=True)
        if "No public keys found" in stderr:
            return []
        result = []
        for item in json.loads(stdout):
            name, fingerprint = item.pop("name"), item.pop("fingerprint")
            result.append(SSHKey(name=name, fingerprint=fingerprint, options=item))
        return result

    def add(self, name: str, key: str | Path, execute: bool = True) -> str | Command:
        """Add a SSH key to Dokku

        `key` can be the public key itself or the path to the public key file
        """
        key_content = None
        if isinstance(key, str):
            if REGEXP_SSH_PUBLIC_KEY.match(key):  # key is the actual string
                key_content = key
            else:
                key = Path(key)
        if isinstance(key, Path):
            # Key file is plain ASCII (base64-encoded), so we can read as if it were UTF-8 and have it in `str` instead
            # of `bytes`
            with key.open(mode="r") as fobj:
                key_content = fobj.read()
        if key_content is None:
            raise ValueError(f"Unknown key type: {repr(key)}")
        result = self._evaluate(
            "add",
            params=[name],
            stdin=key_content + "\n",
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

    def remove(self, name: str, is_fingerprint: bool = False, execute: bool = True) -> str | Command:
        # WARNING: Dokku won't throw an error if you try to delete an unexisting key
        params = ["--fingerprint", name] if is_fingerprint else [name]
        return self._evaluate("remove", params=params, sudo=True, execute=execute)

    def dump_all(self, apps: List[App]) -> List[dict]:
        return [obj.serialize() for obj in self.list()]

    def create_object(self, obj: SSHKey, execute: bool = True) -> List[str] | List[Command]:
        return [self.add(obj, execute=execute)]
