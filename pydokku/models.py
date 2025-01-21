import base64
import datetime
import shlex
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List, Literal

from .utils import parse_iso_format


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
        self.fingerprint = result.split()[1]

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
    app_name: str | None
    key: str
    value: str | None


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
class Domain(BaseModel):
    app_name: str | None
    enabled: bool
    domains: List[str]


@dataclass
class Check(BaseModel):
    app_name: str | None
    process: str
    status: Literal["enabled"] | Literal["disabled"] | Literal["skipped"] | None
    app_wait_to_retire: int | None
    global_wait_to_retire: int | None

    @property
    def wait_to_retire(self) -> int | None:
        return self.app_wait_to_retire or self.global_wait_to_retire


@dataclass
class Process(BaseModel):
    type: str
    id: int
    status: Literal["running"] | Literal["exited"] | None
    container_id: str | None = None


@dataclass
class ProcessInfo(BaseModel):
    app_name: str
    deployed: bool
    processes: List[Process]
    can_scale: bool
    restart_policy: str
    restore: bool
    running: bool
    global_procfile_path: Path | None = None
    app_procfile_path: Path | None = None

    def __post_init__(self):
        if self.processes and not isinstance(self.processes[0], Process):
            self.processes = [Process(**row) for row in self.processes]

    @property
    def procfile_path(self):
        return self.app_procfile_path or self.global_procfile_path


@dataclass
class Git(BaseModel):
    app_name: str
    global_deploy_branch: str
    keep_git_path: bool
    deploy_branch: str
    rev_env_var: str
    sha: str
    source_image: str | None = None
    last_updated_at: datetime.datetime | None = None


@dataclass
class Auth(BaseModel):
    hostname: str
    username: str | None = None
    password: str | None = None


@dataclass
class Proxy(BaseModel):
    app_name: str
    enabled: bool
    global_type: str | None = None
    app_type: str | None = None

    @property
    def type(self) -> str | None:
        return self.app_type or self.global_type


@dataclass
class Port(BaseModel):
    app_name: str | None
    scheme: str
    host_port: int
    container_port: int | None


@dataclass
class Nginx(BaseModel):
    app_name: str | None
    access_log_format: str | None = None
    access_log_path: Path | None = None
    bind_address_ipv4: str | None = None
    bind_address_ipv6: str | None = None
    client_body_timeout: str | None = None
    client_header_timeout: str | None = None
    client_max_body_size: str | None = None
    disable_custom_config: bool | None = None
    error_log_path: Path | None = None
    hsts: bool | None = None
    hsts_include_subdomains: bool | None = None
    hsts_max_age: datetime.timedelta | None = None
    hsts_preload: bool | None = None
    keepalive_timeout: str | None = None
    last_visited_at: str | None = None
    lingering_timeout: str | None = None
    nginx_conf_sigil_path: Path | None = None
    proxy_buffer_size: str | None = None
    proxy_buffering: str | None = None
    proxy_buffers: str | None = None
    proxy_busy_buffers_size: str | None = None
    proxy_connect_timeout: str | None = None
    proxy_read_timeout: str | None = None
    proxy_send_timeout: str | None = None
    send_timeout: str | None = None
    underscore_in_headers: str | None = None
    x_forwarded_for_value: str | None = None
    x_forwarded_port_value: str | None = None
    x_forwarded_proto_value: str | None = None
    x_forwarded_ssl: str | None = None

    def serialize(self):
        row = super().serialize()
        if row["hsts_max_age"] is not None:
            row["hsts_max_age"] = int(row["hsts_max_age"].total_seconds())
        return row


@dataclass
class Network(BaseModel):
    name: str
    id: str
    created_at: datetime.datetime
    driver: str
    scope: str
    internal: bool
    ipv6: bool
    labels: dict[str, str]

    @classmethod
    def from_dict(cls, data: dict) -> "Network":
        return cls(
            id=data["ID"],
            name=data["Name"],
            driver=data["Driver"],
            scope=data["Scope"],
            created_at=parse_iso_format(data["CreatedAt"]),
            internal=data["Internal"],
            ipv6=data["IPv6"],
            labels=data["Labels"],
        )


@dataclass
class AppNetwork(BaseModel):
    app_name: str
    attach_post_create: List[str]
    attach_post_deploy: List[str]
    bind_all_interfaces: bool
    initial_network: str | None = None
    static_web_listener: str | None = None
    tld: str | None = None


@dataclass
class Plugin(BaseModel):
    name: str
    version: str
    enabled: bool
    description: str
    git_url: str | None = None
    git_reference: str | None = None

    @property
    def is_core(self):
        return self.description.startswith("dokku core ")
