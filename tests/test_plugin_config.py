from dokkupy.dokku_cli import Dokku

# TODO: may use dokkupy.inspector to assert the result of each command or mock the command execution and check the
# to-be-executed command (list of strings)


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


# TODO: implement tests for Dokku.config.* using an app (instead of global), alternating between restart=True|False
