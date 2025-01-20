import json
import re
from typing import List

from ..models import App, Command, SSHKey
from ..ssh import REGEXP_SSH_PUBLIC_KEY
from ..utils import clean_stderr
from .base import DokkuPlugin

REGEXP_KV = re.compile(r'([A-Z]+)=(?:[\\"]+)?([^ "\\]+)(?:[\\"]+)?')


def parse_authorized_keys(contents: str) -> List[dict]:
    result = []
    for line in contents.splitlines():
        line = line.strip()
        row = {key.lower(): value for key, value in REGEXP_KV.findall(line)}
        if "fingerprint" not in row or "name" not in row:
            continue
        keys_found = REGEXP_SSH_PUBLIC_KEY.findall(line)
        if not keys_found:
            continue
        if len(keys_found) > 1:
            raise RuntimeError(f"Expected only one key per line (found {len(keys_found)})")
        result.append(SSHKey(name=row["name"], fingerprint=row["fingerprint"], public_key=keys_found[0]))
    return result


class SSHKeysPlugin(DokkuPlugin):
    """
    dokku ssh-keys core plugin

    EXTRA features:
    - `list` will add the actual public key by reading the Dokku SSH authorized keys file (if the user has the
      permission to do so)
    """

    name = "ssh-keys"
    object_classes = (SSHKey,)

    def _read_authorized_keys(self):
        """
        Read the SSH authorized keys file using `cat` command (locally or via SSH, if Dokku is configured to)

        It's assumed that the home directory for `dokku` user is `/home/dokku` in the machine it's going to be
        executed.
        """
        command = Command(["cat", "/home/dokku/.ssh/authorized_keys"], sudo=self.dokku.requires_sudo)
        _, stdout, _ = self.dokku._execute(command)  # will execute using SSH connection, if configured to
        return stdout

    def list(self) -> List[SSHKey]:
        # First, read keys on `dokku ssh-keys:list` command
        # Dokku WILL return error in this `list` command, so `check=False` is used in all `:report/list` because of
        # this inconsistent behavior <https://github.com/dokku/dokku/issues/7454>
        _, stdout, stderr = self._evaluate("list", ["--format", "json"], check=False, full_return=True, execute=True)
        if "No public keys found" in stderr:
            return []
        keys = []
        for item in json.loads(stdout):
            name, fingerprint = item.pop("name"), item.pop("fingerprint")
            keys.append(SSHKey(name=name, fingerprint=fingerprint, public_key=None))

        if self.dokku.can_execute_regular_commands:
            # Read the actual `authorized_keys` file (populated by `sshcommand`) to get the public keys
            authorized_keys = parse_authorized_keys(self._read_authorized_keys())
            found_key_names = set(key.name for key in authorized_keys)
            listed_key_names = [obj.name for obj in keys]
            missing_key_names = set(listed_key_names) - found_key_names
            if missing_key_names:
                raise RuntimeError(f"Missing keys in authorized_keys file: {', '.join(missing_key_names)}")
            return [key for key in authorized_keys if key.name in listed_key_names]
        else:
            # If it's running over SSH and the remote user is dokku, we won't be able to execute `cat` to get
            # authorized keys
            return keys

    def add(self, key: SSHKey, execute: bool = True) -> str | Command:
        """Add a SSH key to Dokku"""
        if key.public_key is None:
            raise ValueError("Cannot add an empty public key")
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

    def object_list(self, apps: List[App], system: bool = True) -> List[SSHKey]:
        return self.list()

    def object_create(self, obj: SSHKey, skip_system: bool = False, execute: bool = True) -> List[str] | List[Command]:
        return [self.add(obj, execute=execute)]
