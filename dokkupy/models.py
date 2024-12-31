import base64
import datetime
import shlex
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List


class BaseModel:
    def serialize(self):
        return asdict(self)


@dataclass
class Command(BaseModel):
    command: List[str]
    stdin: str = None
    check: bool = True
    sudo: bool = False

    def __str__(self):
        command = (["sudo"] if self.sudo else []) + self.command
        cmd_txt = shlex.join(command)
        if self.stdin is None:
            return cmd_txt
        encoded = base64.b64encode(self.stdin.encode("utf-8")).decode("ascii")
        return f"echo {encoded} | base64 --decode | {cmd_txt}"


@dataclass
class SSHKey(BaseModel):
    name: str
    fingerprint: str | None = None
    public_key: str | None = None

    def calculate_fingerprint(self):
        from .ssh import key_fingerprint

        result = key_fingerprint(self.public_key)
        _, self.fingerprint, _ = result.split(maxsplit=2)

    @classmethod
    def open(cls, name: str, path: str | Path, calculate_fingerprint: bool = True) -> "SSHKey":
        """Open a public SSH key file and create a SSHKey object"""
        obj = cls(name=name, public_key=Path(path).expanduser().read_text(), fingerprint=None)
        if calculate_fingerprint:
            try:
                obj.calculate_fingerprint()
            except RuntimeError:
                raise RuntimeError(f"Cannot calculate key fingerprint for: {repr(obj.public_key)}")
        return obj


@dataclass
class App(BaseModel):
    name: str
    path: Path
    locked: bool
    created_at: datetime.datetime | None = None
    deploy_source: str | None = None
    deploy_source_metadata: str | None = None


@dataclass
class Config(BaseModel):
    app_name: str
    key: str
    value: str


@dataclass
class Storage(BaseModel):
    app_name: str
    host_path: Path | str
    container_path: Path | str
    user_id: int | None = None
    group_id: int | None = None

    def __post_init__(self):
        # Force conversion to Path if string is passed
        self.host_path = Path(self.host_path)
        self.container_path = Path(self.container_path)
        self.user_id = int(self.user_id) if self.user_id else None
        self.group_id = int(self.group_id) if self.group_id else None


@dataclass
class Domain:
    app_name: str
    enabled: bool
    domains: List[str]

    def serialize(self):
        return asdict(self)
