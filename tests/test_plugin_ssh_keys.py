import pytest

from dokkupy.dokku_cli import Dokku
from tests.utils import requires_dokku


def test_add_command(temp_file):
    key_name = "test-myuser"
    key_path = temp_file
    key_content = "test 123"
    with temp_file.open(mode="w") as fobj:
        fobj.write(key_content)
    dokku = Dokku()

    command = dokku.ssh_keys.add(name=key_name, key=key_path, execute=False)
    assert command.command == ["dokku", "ssh-keys:add", key_name]
    assert command.stdin == key_content + "\n"
    assert command.check is False
    assert command.sudo is True


def test_remove_command():
    key_name = "test-myuser"
    key_fingerprint = "SHA256:I/Du4ECSnSCpI3Q+CCgg+bWnR0sjwlIVwz2IRCEAwbw"
    dokku = Dokku()

    command = dokku.ssh_keys.remove(key_name, is_fingerprint=False, execute=False)
    assert command.command == ["dokku", "ssh-keys:remove", key_name]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is True

    command = dokku.ssh_keys.remove(key_fingerprint, is_fingerprint=True, execute=False)
    assert command.command == ["dokku", "ssh-keys:remove", "--fingerprint", key_fingerprint]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is True


@requires_dokku
def test_add_remove(temp_file):
    dokku = Dokku()
    keys_before = dokku.ssh_keys.list()

    name = "test-debian"
    another_name = "test-turicas"
    content = """
        ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQC9bIQ9NsZXsOVy/ho6KmRob3MPDgXdmj3XsRzUUjTgjMOPjrGkzKnKQmT+Cq05eGqYqJJChsbWrbazYsEntfYwqE2UGuYJRCs7zlXs10nXb007QkxBaiGkrJz94zayR/8qt6+geGejVl9I7l8EINRK1+SOvv62+8fc1TWQwnsboY0kMN59eS64Lvq35k3gSFn6ZC03ompqZp1OJFqMW+wT7FHGCm9Hoe0si+XU6GWqIKrjg+1GBLUxdtcmfxmUjiimHwAcof3OYl+iTl0zCykYLvamTVwjNLV9guRJ9sq68ljtmxNEZtMs3SgS1y9my/HYM8LQYeePxCuXAFFu3lh493e/mu4YrMdk4rO+3Fqlkr10im+SkEIo3EmKnCWturUrf2i3d37w2QNnX+77T313yH6FYx826ZxfoDknktVZYEmeVQNHG1903bmFNfoDY+R+PI3Pkn0NCs7uhXLFL+pDYJHw12ys32XALYQXyIQbx2H2NHFlugGTGemqYQhCm5U= debian@localhost
    """.strip()
    fingerprint = "SHA256:XiRjUCWNDCrKwSFRSqhR2kP33fEkDsUKbbwhCbnJXas"
    dokku.ssh_keys.add(name=name, key=content)

    keys_after = dokku.ssh_keys.list()
    assert len(keys_before) + 1 == len(keys_after)
    keys_after_by_name = {key.name: key for key in keys_after}
    assert name in keys_after_by_name
    assert keys_after_by_name[name].fingerprint == fingerprint
    assert "SSHCOMMAND_ALLOWED_KEYS" in keys_after_by_name[name].options

    with pytest.raises(ValueError, match="Duplicate ssh key name"):
        dokku.ssh_keys.add(name=name, key=content)

    with pytest.raises(ValueError, match="Cannot add SSH key: Key specified in is not a valid ssh public key"):
        with temp_file.open(mode="w") as fobj:
            fobj.write("invalid key content")
        dokku.ssh_keys.add(name=another_name, key=temp_file)

    dokku.ssh_keys.remove(name=name, is_fingerprint=False)
    keys_final = dokku.ssh_keys.list()
    assert len(keys_before) == len(keys_final)
