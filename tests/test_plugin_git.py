import datetime

import pytest

from pydokku import Dokku
from pydokku.models import Git
from pydokku.utils import get_system_tzinfo
from tests.utils import requires_dokku


def test_object_class():
    dokku = Dokku()
    assert dokku.git.object_class is Git


def test_set_command():
    dokku = Dokku()
    app_name = "test-app-1"
    changes = {
        "deploy-branch": "main",
        "keep-git-dir": False,
        "rev-env-var": "NEW_GIT_REV",
        "source-image": "bla-bla/1.0.0",
    }
    for key, new_value in changes.items():
        if isinstance(new_value, bool):
            expected = str(new_value).lower()
        else:
            expected = str(new_value)
        command = dokku.git.set(app_name, key=key, value=new_value, execute=False)
        assert command.command == ["dokku", "git:set", app_name, key, expected]


def test_unset_command():
    dokku = Dokku()
    app_name = "test-app-1"
    keys = ("deploy-branch", "keep-git-dir", "rev-env-var", "source-image")
    for key in keys:
        command = dokku.git.unset(app_name, key=key, execute=False)
        assert command.command == ["dokku", "git:set", app_name, key]


def test_allow_host_command():
    dokku = Dokku()
    host = "example.net"
    command = dokku.git.allow_host(host, execute=False)
    assert command.command == ["dokku", "git:allow-host", host]


def test_parse_deploy_key():
    stdout = """
        Generating public/private ed25519 key pair.
        Your identification has been saved in /home/dokku/.ssh/id_ed25519
        Your public key has been saved in /home/dokku/.ssh/id_ed25519.pub
        The key fingerprint is:
        SHA256:tGfI8g97+PZA2avezez0qBKKoGtvtgMcqUzOfKD46c0 dokku@localhost
        The key's randomart image is:
        +--[ED25519 256]--+
        |                 |
        |                 |
        |   .    .        |
        | oo    o o o     |
        |Oo..  . S = .    |
        |+=o..  o +.  .   |
        | ..+ . .oo... .  |
        |  =o+ . o+++ = o |
        | oo=Eo  .==o+o* .|
        +----[SHA256]-----+
    """
    dokku = Dokku()
    expected = (
        "SHA256:tGfI8g97+PZA2avezez0qBKKoGtvtgMcqUzOfKD46c0 dokku@localhost",
        "/home/dokku/.ssh/id_ed25519.pub",
    )
    result = dokku.git._parse_generate_deploy_key(stdout)
    assert result == expected


def test_parse_report():
    stdout = """
        =====> test-app-10 git information
            Git deploy branch:             master
            Git global deploy branch:      main
            Git keep git dir:              false
            Git rev env var:               GIT_REV
            Git sha:                       HEAD
            Git source image:
            Git last updated at:
        =====> test-app-7 git information
            Git deploy branch:             master
            Git global deploy branch:      main
            Git keep git dir:              false
            Git rev env var:               GIT_REV
            Git sha:                       HEAD
            Git source image:
            Git last updated at:
        =====> test-app-8 git information
            Git deploy branch:             master
            Git global deploy branch:      main
            Git keep git dir:              false
            Git rev env var:               GIT_REV
            Git sha:                       HEAD
            Git source image:
            Git last updated at:
        =====> test-app-9 git information
            Git deploy branch:             main
            Git global deploy branch:      main
            Git keep git dir:              false
            Git rev env var:               GIT_REV
            Git sha:                       75a174dfa0aa1af0dc13cbb7490946588e8242fc
            Git source image:              nginx:1.27
            Git last updated at:           1736395053
    """
    expected = [
        {
            "app_name": "test-app-10",
            "deploy_branch": "master",
            "global_deploy_branch": "main",
            "keep_git_path": False,
            "rev_env_var": "GIT_REV",
            "sha": "HEAD",
            "source_image": None,
            "last_updated_at": None,
        },
        {
            "app_name": "test-app-7",
            "deploy_branch": "master",
            "global_deploy_branch": "main",
            "keep_git_path": False,
            "rev_env_var": "GIT_REV",
            "sha": "HEAD",
            "source_image": None,
            "last_updated_at": None,
        },
        {
            "app_name": "test-app-8",
            "deploy_branch": "master",
            "global_deploy_branch": "main",
            "keep_git_path": False,
            "rev_env_var": "GIT_REV",
            "sha": "HEAD",
            "source_image": None,
            "last_updated_at": None,
        },
        {
            "app_name": "test-app-9",
            "deploy_branch": "main",
            "global_deploy_branch": "main",
            "keep_git_path": False,
            "rev_env_var": "GIT_REV",
            "sha": "75a174dfa0aa1af0dc13cbb7490946588e8242fc",
            "source_image": "nginx:1.27",
            "last_updated_at": datetime.datetime(2025, 1, 9, 3, 57, 33).utctimetuple(),
        },
    ]
    dokku = Dokku()
    rows_parser = dokku.git._get_rows_parser()
    result = rows_parser(stdout)
    for row in result:
        # Converts to UTC so we don't have failing tests depending on the machine's timezone
        if row["last_updated_at"]:
            row["last_updated_at"] = row["last_updated_at"].utctimetuple()
    assert result == expected


def test_initialize_command():
    app_name = "test-app-9"
    dokku = Dokku()
    command = dokku.git.initialize(app_name=app_name, execute=False)
    assert command.command == ["dokku", "git:initialize", app_name]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False


def test_from_image_command():
    app_name = "test-app-9"
    image = "nginx:1.27"
    build_path = "/tmp/olar"
    git_username, git_email = "turicas", "admin@example.net"
    dokku = Dokku()
    command = dokku.git.from_image(app_name=app_name, image=image, execute=False)
    assert command.command == ["dokku", "git:from-image", app_name, image]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False

    command = dokku.git.from_image(app_name=app_name, image=image, build_path=build_path, execute=False)
    assert command.command == ["dokku", "git:from-image", "--build-dir", build_path, app_name, image]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False

    command = dokku.git.from_image(
        app_name=app_name, image=image, git_username=git_username, git_email=git_email, execute=False
    )
    assert command.command == ["dokku", "git:from-image", app_name, image, git_username, git_email]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False

    with pytest.raises(ValueError, match="`git_username` is required for using `git_email`"):
        dokku.git.from_image(app_name=app_name, image=image, git_username=None, git_email=git_email, execute=False)


@requires_dokku
def test_deploy_key():
    dokku = Dokku()
    ssh_key = dokku.git.generate_deploy_key()
    result = dokku.git.public_key()
    assert ssh_key == result
