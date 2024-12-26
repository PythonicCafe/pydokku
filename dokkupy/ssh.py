import subprocess
import tempfile
from pathlib import Path


def key_requires_password(filename: Path | str) -> bool:
    """Use `ssh-keygen` to check if a SSH key file is password-protected

    `ssh-keygen` is used to print the public key related to a private one. If the key is password-protected, the
    program will wait for input on stdin. As we're closing the stdin without sending anything, it'll end with an
    error.
    """
    command = ["ssh-keygen", "-y", "-f", str(Path(filename).expanduser().absolute())]
    process = subprocess.Popen(
        command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8",
    )
    process.stdin.close()
    return process.wait() != 0


def key_create(filename: Path | str, key_type: str, password=None):
    """Use `ssh-keygen` to create a new SSH key"""
    key_types = "dsa ecdsa ecdsa-sk ed25519 ed25519-sk rsa".split()
    if key_type not in key_types:
        raise ValueError(f"Invalid SSH key type: {repr(key_type)}")
    filename = Path(filename).expanduser().absolute()
    if not filename.parent.exists():
        filename.parent.mkdir(parents=True, exist_ok=True)
    command = ["ssh-keygen", "-t", key_type, "-f", str(filename), "-N", str(password or "")]
    process = subprocess.Popen(
        command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8",
    )
    result = process.wait()
    if result != 0:
        stderr = process.stderr.read().strip()
        raise ValueError(f"Error creating SSH key: {stderr}")
    return process.stdout.read().strip()


def key_unlock(filename: Path | str, password: str) -> Path:
    """Copy the SSH key to a temp file and uses `ssh-keygen` to unlock and overwrite the newly created file"""
    filename = Path(filename).expanduser().absolute()
    temp = tempfile.NamedTemporaryFile(delete=False, prefix="")  # TODO: use a prefix so the user can easily identify
    temp_filename = Path(temp.name)
    temp_filename.chmod(0o600)
    with filename.open(mode="rb") as in_fobj, temp_filename.open(mode="wb") as out_fobj:
        out_fobj.write(in_fobj.read())
    command = ["ssh-keygen", "-p", "-P", password, "-N", "", "-f", str(temp_filename)]
    process = subprocess.Popen(
        command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8",
    )
    result = process.wait()
    if result != 0:
        temp_filename.unlink()
        stderr = process.stderr.read().strip()
        raise ValueError(f"Error unlocking SSH key: {stderr}")
    return temp_filename
