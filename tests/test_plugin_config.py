import random

import pytest

from dokkupy.dokku_cli import Dokku
from tests.utils import random_value, requires_dokku


def test_set_many_command():
    app_name = "test-app"
    pairs = {random_value(8): random_value(64) for _ in range(random.randint(1, 10))}
    dokku = Dokku()
    command = dokku.config.set_many(app_name, pairs, restart=False, execute=False)
    assert command.command[:5] == ["dokku", "config:set", "--encoded", "--no-restart", app_name]
    assert len(command.command[5:]) == len(pairs)
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False

    command = dokku.config.set_many(None, pairs, restart=False, execute=False)
    assert command.command[:4] == ["dokku", "config:set", "--encoded", "--global"]
    assert len(command.command[4:]) == len(pairs)
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False

    with pytest.raises(ValueError, match="Cannot restart when setting global config"):
        dokku.config.set_many(None, pairs, restart=True, execute=False)


def test_unset_many_command():
    app_name = "test-app"
    keys = [random_value(8) for _ in range(random.randint(1, 10))]
    dokku = Dokku()
    command = dokku.config.unset_many(app_name, keys, restart=False, execute=False)
    assert command.command[:4] == ["dokku", "config:unset", "--no-restart", app_name]
    assert len(command.command[4:]) == len(keys)
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False

    command = dokku.config.unset_many(None, keys, restart=False, execute=False)
    assert command.command[:3] == ["dokku", "config:unset", "--global"]
    assert len(command.command[3:]) == len(keys)
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False

    with pytest.raises(ValueError, match="Cannot restart when unsetting global config"):
        dokku.config.unset_many(None, keys, restart=True, execute=False)


def test_clear_command():
    app_name = "test-app"
    dokku = Dokku()
    command = dokku.config.clear(app_name, restart=False, execute=False)
    assert command.command == ["dokku", "config:clear", "--no-restart", app_name]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False

    command = dokku.config.clear(None, restart=False, execute=False)
    assert command.command == ["dokku", "config:clear", "--global"]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False

    with pytest.raises(ValueError, match="Cannot restart when clearing global config"):
        dokku.config.clear(None, restart=True, execute=False)


@requires_dokku
def test_set_get():
    key1, value1 = "test_key1", "some value\nwith multiple lines"
    key2, value2 = "test_key2", 123456  # int value instead of str
    key3, value3 = "test_key3", True  # bool value instead of str
    key4, value4 = "test_key4", None  # None value instead of str
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
    pairs = {
        key1: str(value1 if value1 is not None else ""),
        key2: str(value2 if value2 is not None else ""),
        key3: str(value3 if value3 is not None else ""),
        key4: str(value4 if value4 is not None else ""),
    }
    dokku.config.set_many(app_name=None, keys_values=pairs)
    final_configs = dokku.config.get(app_name=None)
    expected = configs_before.copy()
    expected.update(pairs)
    assert final_configs == expected


@requires_dokku
def test_set_get_merged():
    app_name = "test-app"
    keys_local = {"test_a": 1, "test_b": 2, "test_c": 3}
    keys_global = {"test_a": 0, "test_b": 0, "test_d": 4}
    dokku = Dokku()
    initial_global = dokku.config.get(None)
    dokku.apps.create(app_name)
    assert dokku.config.get(app_name, merged=False) == {}
    expected_merged = {key: str(value) for key, value in initial_global.items()}
    assert dokku.config.get(app_name, merged=True) == expected_merged
    dokku.config.set_many(None, keys_global)
    assert dokku.config.get(app_name, merged=False) == {}
    expected_merged = {key: str(value) for key, value in {**initial_global, **keys_global}.items()}
    assert dokku.config.get(app_name, merged=True) == expected_merged
    dokku.config.set_many(app_name, keys_local, restart=False)
    assert dokku.config.get(app_name, merged=False) == {key: str(value) for key, value in keys_local.items()}
    expected_merged = {key: str(value) for key, value in {**initial_global, **keys_global, **keys_local}.items()}
    assert dokku.config.get(app_name, merged=True) == expected_merged
    dokku.apps.destroy(app_name)


@requires_dokku
def test_clear():
    pairs = {"test_k1": "v1", "test_k2": "v2"}
    dokku = Dokku()
    dokku.config.set_many(app_name=None, keys_values=pairs)
    configs_after = dokku.config.get(app_name=None)
    assert len(configs_after) >= len(pairs)
    dokku.config.clear(app_name=None)
    final_configs = dokku.config.get(app_name=None)
    assert len(final_configs) == 0
