from textwrap import dedent

import pytest

from pydokku import Dokku
from pydokku.models import Plugin
from pydokku.plugins.plugin import get_git_origin_url


def test_parse_stdout():
    stdout = """
        00_dokku-standard    0.35.14 enabled    dokku core standard plugin
        20_events            0.35.14 enabled    dokku core events logging plugin
        apps                 0.35.14 enabled    dokku core apps plugin
        builder              0.35.14 disabled   dokku core builder plugin
        postgres             1.41.0 enabled    dokku postgres service plugin
    """
    expected = [
        Plugin(name="00_dokku-standard", version="0.35.14", enabled=True, description="dokku core standard plugin"),
        Plugin(name="20_events", version="0.35.14", enabled=True, description="dokku core events logging plugin"),
        Plugin(name="apps", version="0.35.14", enabled=True, description="dokku core apps plugin"),
        Plugin(name="builder", version="0.35.14", enabled=False, description="dokku core builder plugin"),
        Plugin(name="postgres", version="1.41.0", enabled=True, description="dokku postgres service plugin"),
    ]
    dokku = Dokku()
    result = dokku.plugin._parse_list(stdout)
    assert result == expected


def test_enable_command():
    dokku = Dokku()
    name = "test-plugin"
    command = dokku.plugin.enable(name=name, execute=False)
    assert command.command == ["dokku", "plugin:enable", name]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is True


def test_disable_command():
    dokku = Dokku()
    name = "test-plugin"
    command = dokku.plugin.disable(name=name, execute=False)
    assert command.command == ["dokku", "plugin:disable", name]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is True


def test_uninstall_command():
    dokku = Dokku()
    name = "test-plugin"
    command = dokku.plugin.uninstall(name=name, execute=False)
    assert command.command == ["dokku", "plugin:uninstall", name]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is True


def test_update_command():
    dokku = Dokku()
    name = "test-plugin"

    command = dokku.plugin.update(execute=False)
    assert command.command == ["dokku", "plugin:update"]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is True
    command = dokku.plugin.update(name=name, execute=False)
    assert command.command == ["dokku", "plugin:update", name]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is True
    command = dokku.plugin.update(name=name, git_reference="develop", execute=False)
    assert command.command == ["dokku", "plugin:update", name, "develop"]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is True


def test_install_dependencies_command():
    dokku = Dokku()

    command = dokku.plugin.install_dependencies(execute=False)
    assert command.command == ["dokku", "plugin:install-dependencies"]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is True
    command = dokku.plugin.install_dependencies(core=True, execute=False)
    assert command.command == ["dokku", "plugin:install-dependencies", "--core"]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is True


def test_trigger_command():
    dokku = Dokku()

    command = dokku.plugin.trigger(args=["dont", "know", "what", "this", "cmd", "does"], execute=False)
    assert command.command == ["dokku", "plugin:trigger", "dont", "know", "what", "this", "cmd", "does"]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is True


def test_get_git_origin_url():
    data = dedent(
        """
         [core]
                 repositoryformatversion = 0
                 filemode = true
                 bare = false
                 logallrefupdates = true
         [remote "origin"]
                 url = https://github.com/dokku/dokku-redirect.git
                 fetch = +refs/heads/*:refs/remotes/origin/*
         [branch "master"]
                 remote = origin
                 merge = refs/heads/master
        """
    ).strip()
    expected = "https://github.com/dokku/dokku-redirect.git"
    result = get_git_origin_url(data)
    assert result == expected


def test_install_command():
    dokku = Dokku()
    name = "postgres"
    git_url = "https://github.com/dokku/dokku-postgres.git"
    git_reference = "9ab50f6feb8792842152b384873e1af9a8b19d6b"

    command = dokku.plugin.install(core=True, execute=False)
    assert command.command == ["dokku", "plugin:install", "--core"]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is True

    with pytest.raises(ValueError, match="If `core` is `True`, then no other option should be provided"):
        dokku.plugin.install(core=True, git_url="some-value", execute=False)
    with pytest.raises(ValueError, match="If `core` is `True`, then no other option should be provided"):
        dokku.plugin.install(core=True, git_reference="some-value", execute=False)
    with pytest.raises(ValueError, match="If `core` is `True`, then no other option should be provided"):
        dokku.plugin.install(core=True, name="some-value", execute=False)

    with pytest.raises(ValueError, match="`git_url` must be provided"):
        dokku.plugin.install(git_url=None, core=False, execute=False)

    command = dokku.plugin.install(git_url=git_url, core=False, execute=False)
    assert command.command == ["dokku", "plugin:install", git_url]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is True

    command = dokku.plugin.install(git_url=git_url, git_reference=git_reference, core=False, execute=False)
    assert command.command == ["dokku", "plugin:install", git_url, "--committish", git_reference]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is True

    command = dokku.plugin.install(git_url=git_url, name=name, core=False, execute=False)
    assert command.command == ["dokku", "plugin:install", git_url, "--name", name]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is True


# TODO: test list and assert git_reference and git_remote
