import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List

from ..ssh import KEY_TYPES
from .base import DokkuPlugin

REGEXP_SSH_PUBLIC_KEY = re.compile(f"ssh-({'|'.join(KEY_TYPES)}) AAAA[a-zA-Z0-9+/=]+( [^@]+@[^@]+)?")


@dataclass
class SSHKey:
    fingerprint: str
    name: str
    options: dict

    def serialize(self):
        return asdict(self)


class SSHKeysPlugin(DokkuPlugin):
    name = "ssh-keys"

    def list(self) -> List[dict]:
        _, stdout, stderr = self._execute("list", ["--format", "--json"], check=False)
        if "No public keys found" in stderr:
            return []
        result = []
        for item in json.loads(stdout):
            name, fingerprint = item.pop("name"), item.pop("fingerprint")
            result.append(SSHKey(name=name, fingerprint=fingerprint, options=item))
        return result

    def add(self, name: str, key: str | Path):
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
            with key.open() as fobj:
                key_content = fobj.read()
        if key_content is None:
            raise ValueError(f"Unknown key type: {repr(key)}")
        _, stdout, _ = self._execute("add", [name], stdin=key_content, sudo=True)
        return stdout

    def remove(self, name: str, is_fingerprint=False) -> str:
        _, stdout, _ = self._execute("remove", ["--fingerprint", name] if is_fingerprint else [name], sudo=True)
        return stdout
