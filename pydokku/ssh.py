import re
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import List, Union

KEY_TYPES = "dsa ecdsa ecdsa-sk ed25519 ed25519-sk rsa".split()
REGEXP_SSH_PUBLIC_KEY = re.compile(f"(ssh-(?:{'|'.join(KEY_TYPES)}) AAAA[a-zA-Z0-9+/=]+(?: [^@]+@[^@]+)?)")


def command(
    user: str,
    host: str,
    private_key: Union[Path, str, None] = None,
    port: int = 22,
    mux: bool = False,
    mux_filename: Union[Path, str, None] = None,
    mux_timeout: int = 600,
) -> List[str]:
    cmd = ["ssh", "-p", str(port)]
    if private_key is not None:
        cmd.extend(["-i", str(Path(private_key).expanduser().absolute())])
    if mux:
        mux_filename = Path(mux_filename).expanduser().absolute()
        cmd.extend(
            [
                "-o",
                f"ControlPersist={mux_timeout}",
                "-o",
                "ControlMaster=auto",
                "-o",
                f"ControlPath={mux_filename}",
            ]
        )
    cmd.append(f"{user}@{host}")
    return cmd


def start_process(command) -> subprocess.Popen:
    """Start a new process using `subprocess.Popen` to run `ssh-keygen`

    Note: `start_new_session` is required so `ssh-keygen` won't take over the current process' stdin/stdout with
    "Enter passphrase:".
    """
    return subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        start_new_session=True,
    )


def key_requires_password(filename: Union[Path, str], timeout: float = 5.0) -> bool:
    """Use `ssh-keygen` to check if a SSH key file is password-protected

    `ssh-keygen` is used to print the public key related to a private one. If the key is password-protected, the
    program will wait for input on stdin. As we're closing the stdin without sending anything, it'll end with an error.
    """
    command = ["ssh-keygen", "-y", "-f", str(Path(filename).expanduser().absolute())]
    process = start_process(command)
    try:
        process.communicate(timeout=timeout)
    finally:
        process.kill()
    return process.returncode != 0


def key_create(filename: Union[Path, str], key_type: str, password: Union[str, None] = None, timeout: float = 10.0) -> str:
    """Use `ssh-keygen` to create a new SSH key"""
    if key_type not in KEY_TYPES:
        raise ValueError(f"Invalid SSH key type: {repr(key_type)}")
    filename = Path(filename).expanduser().absolute()
    if not filename.parent.exists():
        filename.parent.mkdir(parents=True, exist_ok=True)
    if filename.exists():
        # If the file exists and is empty, we delete it so `ssh-keygen` won't expect interaction (asking if should
        # overwrite)
        if filename.stat().st_size > 0:
            raise RuntimeError("SSH key file must not exist or be empty")
        filename.unlink()
    command = ["ssh-keygen", "-t", key_type, "-f", str(filename), "-N", str(password if password is not None else "")]
    process = start_process(command)
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    finally:
        process.kill()
    result = process.returncode
    if result != 0:
        raise RuntimeError(f"Error creating SSH key: {stderr.strip()}")
    return stdout.strip()


def key_unlock(filename: Union[Path, str], password: str, timeout: float = 5.0) -> Path:
    """Copy the SSH key to a temp file and uses `ssh-keygen` to unlock and overwrite the newly created file"""
    filename = Path(filename).expanduser().absolute()
    temp = tempfile.NamedTemporaryFile(delete=False, prefix="pydokku-")
    temp_filename = Path(temp.name)
    temp_filename.chmod(0o600)
    with filename.open(mode="rb") as in_fobj, temp_filename.open(mode="wb") as out_fobj:
        out_fobj.write(in_fobj.read())
    command = ["ssh-keygen", "-p", "-P", password, "-N", "", "-f", str(temp_filename)]
    process = start_process(command)
    try:
        _, stderr = process.communicate(timeout=timeout)
    finally:
        process.kill()
    result = process.returncode
    if result != 0:
        temp_filename.unlink()
        raise RuntimeError(f"Error unlocking SSH key: {stderr.strip()}")
    return temp_filename


@contextmanager
def unlock_key(filename: Union[Path, str], password: str):
    """Context manager for temporarily unlocking a SSH key"""
    temp_key = None
    try:
        temp_key = key_unlock(filename, password)
        yield temp_key
    finally:
        if temp_key and temp_key.exists():
            temp_key.unlink()


def key_fingerprint(filename_or_content: Union[Path, str], timeout: float = 5.0) -> str:
    """Extract a fingerprint from a public SSH key"""
    if isinstance(filename_or_content, str) and REGEXP_SSH_PUBLIC_KEY.findall(filename_or_content):
        # `filename_or_content` is the key content, so we use `ssh-keygen`'s stdin
        command = ["ssh-keygen", "-lf", "-"]
        stdin = filename_or_content
    else:  # `filename_or_content` is the key path
        filename = Path(filename_or_content).expanduser().absolute()
        command = ["ssh-keygen", "-lf", str(filename)]
        stdin = None
    process = start_process(command)
    try:
        stdout, stderr = process.communicate(input=stdin, timeout=timeout)
    finally:
        process.kill()
    result = process.returncode
    if result != 0:
        raise RuntimeError(f"Error reading SSH key fingerprint: {stderr.strip()}")
    return stdout.strip()
