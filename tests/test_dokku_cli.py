import re

from dokkupy.dokku_cli import Dokku

# TODO: may use dokkupy.inspector to assert the result of each command
# TODO: implement tests for apps:clone
# TODO: implement tests for apps:lock/unlock
# TODO: implement tests for apps:rename
# TODO: implement tests for Dokku.apps.* methods
# TODO: implement tests for Dokku.config.* using an app (instead of global), alternating between restart=True|False
# TODO: implement tests for SSH (key without passphrase)
# TODO: implement tests for SSH (key with passphrase)


def test_version():
    dokku = Dokku()
    version = dokku.version()
    assert re.match(r"[0-9]+\.[0-9]+\.[0-9]+", version) is not None


def test_list_create_destroy_app():
    app_name = "test-app"
    dokku = Dokku()
    apps_before = dokku.apps.list()
    dokku.apps.create(app_name)
    apps_after = dokku.apps.list()
    assert len(apps_before) + 1 == len(apps_after)
    assert apps_after[-1].name == app_name
    dokku.apps.destroy(app_name)
    assert len(dokku.apps.list()) == 0


def test_config_set_get():
    key1, value1 = "key1", "some value\nwith multiple lines"
    key2, value2 = "key2", 123456  # int value instead of str
    key3, value3 = "key3", True  # bool value instead of str
    key4, value4 = "key4", None  # None value instead of str
    dokku = Dokku()
    configs_before = dokku.config.get(app_name=None)
    dokku.config.set(app_name=None, key=key1, value=value1)
    configs_after = dokku.config.get(app_name=None)
    expected = configs_before.copy()
    expected.update({key1: value1})
    assert len(expected) == len(configs_after)
    assert configs_after[key1] == value1
    dokku.config.unset(app_name=None, key=key1)
    new_configs = dokku.config.get(app_name=None)
    del expected[key1]
    assert len(expected) == len(new_configs)
    pairs = {key1: str(value1 or ""), key2: str(value2 or ""), key3: str(value3 or ""), key4: str(value4 or "")}
    dokku.config.set_many(app_name=None, keys_values=pairs)
    final_configs = dokku.config.get(app_name=None)
    expected = configs_before.copy()
    expected.update(pairs)
    assert final_configs == expected


def test_config_clear():
    pairs = {"k1": "v1", "k2": "v2"}
    dokku = Dokku()
    dokku.config.set_many(app_name=None, keys_values=pairs)
    configs_after = dokku.config.get(app_name=None)
    assert len(configs_after) >= len(pairs)
    dokku.config.clear(app_name=None)
    final_configs = dokku.config.get(app_name=None)
    assert len(final_configs) == 0


def test_ssh_keys():
    dokku = Dokku()
    keys = dokku.ssh_keys.list()
    assert len(keys) == 0

    name = "debian"
    content = """
        ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQC9bIQ9NsZXsOVy/ho6KmRob3MPDgXdmj3XsRzUUjTgjMOPjrGkzKnKQmT+Cq05eGqYqJJChsbWrbazYsEntfYwqE2UGuYJRCs7zlXs10nXb007QkxBaiGkrJz94zayR/8qt6+geGejVl9I7l8EINRK1+SOvv62+8fc1TWQwnsboY0kMN59eS64Lvq35k3gSFn6ZC03ompqZp1OJFqMW+wT7FHGCm9Hoe0si+XU6GWqIKrjg+1GBLUxdtcmfxmUjiimHwAcof3OYl+iTl0zCykYLvamTVwjNLV9guRJ9sq68ljtmxNEZtMs3SgS1y9my/HYM8LQYeePxCuXAFFu3lh493e/mu4YrMdk4rO+3Fqlkr10im+SkEIo3EmKnCWturUrf2i3d37w2QNnX+77T313yH6FYx826ZxfoDknktVZYEmeVQNHG1903bmFNfoDY+R+PI3Pkn0NCs7uhXLFL+pDYJHw12ys32XALYQXyIQbx2H2NHFlugGTGemqYQhCm5U= debian@localhost
    """.strip()
    fingerprint = "SHA256:XiRjUCWNDCrKwSFRSqhR2kP33fEkDsUKbbwhCbnJXas"
    dokku.ssh_keys.add(name=name, content=content)

    keys = dokku.ssh_keys.list()
    assert len(keys) == 1
    assert keys[0]["name"] == name
    assert keys[0]["fingerprint"] == fingerprint

    # (venv) debian@localhost:~$ cat .ssh/id_rsa.pub | sudo dokku ssh-keys:add turicas
    # Duplicate ssh key name
    #  !     sshcommand returned an error: 1

    # (venv) debian@localhost:~$ echo "oiioioi" | sudo dokku ssh-keys:add turicasssss
    #  !     Key specified in is not a valid ssh public key

    # TODO: delete existing key
    # TODO: delete non-existing key
