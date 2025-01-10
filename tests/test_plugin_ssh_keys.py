from textwrap import dedent

import pytest

from pydokku.dokku_cli import Dokku
from pydokku.models import SSHKey
from pydokku.plugins.ssh_keys import parse_authorized_keys
from tests.utils import requires_dokku, requires_ssh_keygen


def test_object_classes():
    dokku = Dokku()
    assert dokku.ssh_keys.object_classes == (SSHKey,)


@requires_ssh_keygen
def test_model(temp_file):
    key_name = "root"
    key_content = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIBH/a4e/e+/t5w7SfCUhU/2EjbgrkBLtq84BDc7rmCAJ root@localhost"
    key_fingerprint = "SHA256:BR9rgyN7BoVhMuRcK8cQm2fHkTlDOQpa0uMYWTEkTZc"

    key = SSHKey(name=key_name, public_key=key_content)
    assert key.fingerprint is None
    key.calculate_fingerprint()
    assert key.fingerprint == key_fingerprint

    temp_file.write_text(key_content)
    key = SSHKey.open(key_name, temp_file)
    assert key.public_key == key_content
    assert key.fingerprint == key_fingerprint

    invalid_key_content = "test 123"
    temp_file.write_text(invalid_key_content)
    with pytest.raises(RuntimeError, match="Cannot calculate key fingerprint for: 'test 123'"):
        SSHKey.open(key_name, temp_file)


def test_parse_authorized_keys_file():
    regular_auth_keys = dedent(
        """
        ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIBH/a4e/e+/t5w7SfCUhU/2EjbgrkBLtq84BDc7rmCAJ root@localhost
        ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQCzEfW+7YmD7ETaZBwOzN0GFqAlksdnpSImvKt9Vm92vXlqP/CZ7cqwA6uOThlmql91Syjpz1CcYXBHmUJCnlTwzvD+TKfgaT/upreFhRWjyUgAyrxc2LoRAvlEnif2t5adIX6b6GwHwRiphWhV601Gi+iZMeZol6yNC2fukRWzaad5u3kfhsH5WkLdDoSOCsdIWNliyBOJk7p3qsvitNEWwP/0SEn1jPXe4I8K8R/Tq5xkelQpn5aSqcU6h5zFY+PDIOuAEySkumD0UIYd6OlWw/RntwF8G8ZnCFTRjGiZ3d5WegJ0mxT31iWgTn1CavQe05rws6EFThccd7BVyCsFqMj+YxLBURFbTBUR4JM1yKLJ4/sI/xzYhoXMbx1c7gjZyZi15+hmpHh//ev36gc2jrSkkP/LhoXvnAJgNiz3voRc7WOGnZZAmvEjdonxX/NZOte8N4quYqBoqfx5vxUZo3pwbEBCyPPhzc0M6kn8fOXko6ab/ari3rNFbGsq1u8= root@localhost
    """
    )
    dokku_auth_keys = dedent(
        r"""
        command="FINGERPRINT=SHA256:BR9rgyN7BoVhMuRcK8cQm2fHkTlDOQpa0uMYWTEkTZc NAME=\"root-1\" `cat /home/dokku/.sshcommand` $SSH_ORIGINAL_COMMAND",no-agent-forwarding,no-user-rc,no-X11-forwarding,no-port-forwarding ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIBH/a4e/e+/t5w7SfCUhU/2EjbgrkBLtq84BDc7rmCAJ root@localhost
        command="FINGERPRINT=SHA256:DhvG0hhRIcuOrs4Xe+ObprP+19wc2dr+VNdZWSUEG4A NAME=\"root-2\" `cat /home/dokku/.sshcommand` $SSH_ORIGINAL_COMMAND",no-agent-forwarding,no-user-rc,no-X11-forwarding,no-port-forwarding ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQCzEfW+7YmD7ETaZBwOzN0GFqAlksdnpSImvKt9Vm92vXlqP/CZ7cqwA6uOThlmql91Syjpz1CcYXBHmUJCnlTwzvD+TKfgaT/upreFhRWjyUgAyrxc2LoRAvlEnif2t5adIX6b6GwHwRiphWhV601Gi+iZMeZol6yNC2fukRWzaad5u3kfhsH5WkLdDoSOCsdIWNliyBOJk7p3qsvitNEWwP/0SEn1jPXe4I8K8R/Tq5xkelQpn5aSqcU6h5zFY+PDIOuAEySkumD0UIYd6OlWw/RntwF8G8ZnCFTRjGiZ3d5WegJ0mxT31iWgTn1CavQe05rws6EFThccd7BVyCsFqMj+YxLBURFbTBUR4JM1yKLJ4/sI/xzYhoXMbx1c7gjZyZi15+hmpHh//ev36gc2jrSkkP/LhoXvnAJgNiz3voRc7WOGnZZAmvEjdonxX/NZOte8N4quYqBoqfx5vxUZo3pwbEBCyPPhzc0M6kn8fOXko6ab/ari3rNFbGsq1u8= root@localhost
    """
    )

    result_1 = parse_authorized_keys(regular_auth_keys)
    assert len(result_1) == 0  # Only dokku-configured keys should be returned

    result_2 = parse_authorized_keys(dokku_auth_keys)
    assert len(result_2) == 2
    assert result_2 == [
        SSHKey(
            name="root-1",
            fingerprint="SHA256:BR9rgyN7BoVhMuRcK8cQm2fHkTlDOQpa0uMYWTEkTZc",
            public_key="ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIBH/a4e/e+/t5w7SfCUhU/2EjbgrkBLtq84BDc7rmCAJ root@localhost",
        ),
        SSHKey(
            fingerprint="SHA256:DhvG0hhRIcuOrs4Xe+ObprP+19wc2dr+VNdZWSUEG4A",
            name="root-2",
            public_key="ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQCzEfW+7YmD7ETaZBwOzN0GFqAlksdnpSImvKt9Vm92vXlqP/CZ7cqwA6uOThlmql91Syjpz1CcYXBHmUJCnlTwzvD+TKfgaT/upreFhRWjyUgAyrxc2LoRAvlEnif2t5adIX6b6GwHwRiphWhV601Gi+iZMeZol6yNC2fukRWzaad5u3kfhsH5WkLdDoSOCsdIWNliyBOJk7p3qsvitNEWwP/0SEn1jPXe4I8K8R/Tq5xkelQpn5aSqcU6h5zFY+PDIOuAEySkumD0UIYd6OlWw/RntwF8G8ZnCFTRjGiZ3d5WegJ0mxT31iWgTn1CavQe05rws6EFThccd7BVyCsFqMj+YxLBURFbTBUR4JM1yKLJ4/sI/xzYhoXMbx1c7gjZyZi15+hmpHh//ev36gc2jrSkkP/LhoXvnAJgNiz3voRc7WOGnZZAmvEjdonxX/NZOte8N4quYqBoqfx5vxUZo3pwbEBCyPPhzc0M6kn8fOXko6ab/ari3rNFbGsq1u8= root@localhost",
        ),
    ]


def test_add_command(temp_file):
    key_name = "test-myuser"
    key_path = temp_file
    key_content = "test 123"
    temp_file.write_text(key_content)
    dokku = Dokku()

    command = dokku.ssh_keys.add(SSHKey.open(key_name, key_path, calculate_fingerprint=False), execute=False)
    assert command.command == ["dokku", "ssh-keys:add", key_name]
    assert command.stdin == key_content + "\n"
    assert command.check is False
    assert command.sudo is True


def test_remove_command():
    key_name = "test-myuser"
    key_fingerprint = "SHA256:I/Du4ECSnSCpI3Q+CCgg+bWnR0sjwlIVwz2IRCEAwbw"
    dokku = Dokku()

    command = dokku.ssh_keys.remove(SSHKey(name=key_name, fingerprint=None), execute=False)
    assert command.command == ["dokku", "ssh-keys:remove", key_name]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is True

    command = dokku.ssh_keys.remove(SSHKey(name=None, fingerprint=key_fingerprint), execute=False)
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
    dokku.ssh_keys.add(SSHKey(name=name, public_key=content))

    keys_after = dokku.ssh_keys.list()
    assert len(keys_before) + 1 == len(keys_after)
    keys_after_by_name = {key.name: key for key in keys_after}
    assert name in keys_after_by_name
    assert keys_after_by_name[name].fingerprint == fingerprint

    with pytest.raises(ValueError, match="Duplicate ssh key name"):
        dokku.ssh_keys.add(SSHKey(name=name, public_key=content))

    with pytest.raises(ValueError, match="Cannot add SSH key: Key specified in is not a valid ssh public key"):
        temp_file.write_text("invalid key content")
        dokku.ssh_keys.add(SSHKey.open(another_name, temp_file, calculate_fingerprint=False))

    dokku.ssh_keys.remove(SSHKey(name=name))
    keys_final = dokku.ssh_keys.list()
    assert len(keys_before) == len(keys_final)


# TODO: test dump
# TODO: test object_create
