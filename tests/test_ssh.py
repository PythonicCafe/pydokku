from pathlib import Path

import pytest

from pydokku import ssh
from tests.utils import requires_ssh_keygen


@requires_ssh_keygen
def test_command():
    relative_key_path = ".ssh/id_rsa"
    result = ssh.command(user="dokku", host="example.net", port=2222, private_key=relative_key_path)
    full_key_path = str((Path(__file__).parent.parent / relative_key_path).absolute())
    expected = ["ssh", "-p", "2222", "-i", full_key_path, "dokku@example.net"]
    assert expected == result


@requires_ssh_keygen
def test_key_requires_password(temp_dir):
    # Key without password
    key_path = temp_dir / "key_no_pass"
    ssh.key_create(key_path, "rsa")
    assert not ssh.key_requires_password(key_path)

    # Key with password
    key_path_with_pass = temp_dir / "key_with_pass"
    ssh.key_create(key_path_with_pass, "rsa", password="test123")
    assert ssh.key_requires_password(key_path_with_pass)


@requires_ssh_keygen
def test_key_create(temp_dir):
    # Invalid key type
    key_path = temp_dir / "test_key"
    with pytest.raises(ValueError, match="Invalid SSH key type"):
        ssh.key_create(key_path, "invalid_type")

    # Key without password
    output = ssh.key_create(key_path, "rsa")
    pubkey_path = key_path.with_suffix(".pub")
    assert key_path.exists()
    assert pubkey_path.exists()
    assert isinstance(output, str)

    # Key with password
    key_path_pass = temp_dir / "test_key_pass"
    ssh.key_create(key_path_pass, "rsa", password="test123")
    assert ssh.key_requires_password(key_path_pass)


@requires_ssh_keygen
def test_key_unlock(temp_dir):
    # Create a password-protected key
    key_path = temp_dir / "protected_key"
    password = "test123"
    ssh.key_create(key_path, "rsa", password=password)
    assert ssh.key_requires_password(key_path)

    # Test unlocking the key
    unlocked_key_path = ssh.key_unlock(key_path, password)
    try:
        assert not ssh.key_requires_password(unlocked_key_path)
    finally:
        if unlocked_key_path.exists():
            unlocked_key_path.unlink()

    # Test wrong password
    with pytest.raises(RuntimeError, match="Error unlocking SSH key"):
        ssh.key_unlock(key_path, "wrong_password")


@requires_ssh_keygen
def test_key_fingerprint(temp_dir):
    # Valid key file
    key_path = temp_dir / "test_key"
    pubkey_path = key_path.with_suffix(".pub")
    ssh.key_create(key_path, "rsa")
    fingerprint = ssh.key_fingerprint(pubkey_path)
    assert isinstance(fingerprint, str)
    assert len(fingerprint) > 0

    # Invalid key file
    invalid_key = temp_dir / "invalid_key"
    invalid_key.touch()
    with pytest.raises(RuntimeError, match="Error reading SSH key fingerprint"):
        ssh.key_fingerprint(invalid_key)
