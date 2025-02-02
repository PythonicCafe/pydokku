import datetime
from textwrap import dedent

from pydokku.dokku_cli import Dokku
from pydokku.models import LetsEncrypt
from pydokku.utils import get_system_tzinfo


def test_object_classes():
    dokku = Dokku()
    assert dokku.letsencrypt.object_classes == (LetsEncrypt,)


def test_enable_command():
    dokku = Dokku()
    app_name = "test-app-le"
    command = dokku.letsencrypt.enable(app_name, execute=False)
    assert command.command == ["dokku", "letsencrypt:enable", app_name]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False


def test_disable_command():
    dokku = Dokku()
    app_name = "test-app-le"
    command = dokku.letsencrypt.disable(app_name, execute=False)
    assert command.command == ["dokku", "letsencrypt:disable", app_name]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False


def test_cleanup_command():
    dokku = Dokku()
    app_name = "test-app-le"
    command = dokku.letsencrypt.cleanup(app_name, execute=False)
    assert command.command == ["dokku", "letsencrypt:cleanup", app_name]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False


def test_revoke_command():
    dokku = Dokku()
    app_name = "test-app-le"
    command = dokku.letsencrypt.revoke(app_name, execute=False)
    assert command.command == ["dokku", "letsencrypt:revoke", app_name]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False


def test_auto_renew_command():
    dokku = Dokku()
    app_name = "test-app-le"
    command = dokku.letsencrypt.auto_renew(app_name, execute=False)
    assert command.command == ["dokku", "letsencrypt:auto-renew", app_name]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False

    command = dokku.letsencrypt.auto_renew(app_name=None, execute=False)
    assert command.command == ["dokku", "letsencrypt:auto-renew"]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False


def test_cron_job_command():
    dokku = Dokku()
    command = dokku.letsencrypt.cron_job_add(execute=False)
    assert command.command == ["dokku", "letsencrypt:cron-job", "--add"]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False
    command = dokku.letsencrypt.cron_job_remove(execute=False)
    assert command.command == ["dokku", "letsencrypt:cron-job", "--remove"]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False


def test_set_command():
    app_name = "test-app-1"
    dokku = Dokku()
    command = dokku.letsencrypt.set(app_name=app_name, key="some-key", value=True, execute=False)
    assert command.command == ["dokku", "letsencrypt:set", app_name, "some-key", "true"]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False
    command = dokku.letsencrypt.set(app_name=None, key="some-key", value=123, execute=False)
    assert command.command == ["dokku", "letsencrypt:set", "--global", "some-key", "123"]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False


def test_unset_command():
    app_name = "test-app-1"
    dokku = Dokku()
    command = dokku.letsencrypt.unset(app_name=app_name, key="some-key", execute=False)
    assert command.command == ["dokku", "letsencrypt:set", app_name, "some-key"]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False
    command = dokku.letsencrypt.unset(app_name=None, key="some-key", execute=False)
    assert command.command == ["dokku", "letsencrypt:set", "--global", "some-key"]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False


def test_parse_list():
    stdout = dedent(
        """
        -----> App name           Certificate Expiry        Time before expiry        Time before renewal
        asdfqwertyuiopzxcvbnmlkjhgf 2025-03-23 05:25:43       53d, 23h, 52m, 51s        23d, 23h, 52m, 51s
        poiuytr                   2025-04-04 05:25:44       65d, 23h, 52m, 53s        35d, 23h, 52m, 53s
        ghjklpoiuytrewqzxcvbnmlkjhg 2025-04-28 03:46:30       89d, 22h, 13m, 38s        59d, 22h, 13m, 38s
        test-app-really-long-name-check-how-it-behaves 2025-04-28 04:34:08       89d, 23h, 1m, 16s         59d, 23h, 1m, 16s
        """
    )

    expected = [
        {
            "app_name": "asdfqwertyuiopzxcvbnmlkjhgf",
            "expires_at": datetime.datetime(2025, 3, 23, 5, 25, 43).replace(tzinfo=get_system_tzinfo()),
            "renewals_at": datetime.datetime(2025, 2, 21, 5, 25, 43).replace(tzinfo=get_system_tzinfo()),
        },
        {
            "app_name": "poiuytr",
            "expires_at": datetime.datetime(2025, 4, 4, 5, 25, 44).replace(tzinfo=get_system_tzinfo()),
            "renewals_at": datetime.datetime(2025, 3, 5, 5, 25, 44).replace(tzinfo=get_system_tzinfo()),
        },
        {
            "app_name": "ghjklpoiuytrewqzxcvbnmlkjhg",
            "expires_at": datetime.datetime(2025, 4, 28, 3, 46, 30).replace(tzinfo=get_system_tzinfo()),
            "renewals_at": datetime.datetime(2025, 3, 29, 3, 46, 30).replace(tzinfo=get_system_tzinfo()),
        },
        {
            "app_name": "test-app-really-long-name-check-how-it-behaves",
            "expires_at": datetime.datetime(2025, 4, 28, 4, 34, 8).replace(tzinfo=get_system_tzinfo()),
            "renewals_at": datetime.datetime(2025, 3, 29, 4, 34, 8).replace(tzinfo=get_system_tzinfo()),
        },
    ]
    dokku = Dokku()
    result = dokku.letsencrypt._parse_list(stdout)
    assert result == expected


# TODO: test object_list
# TODO: test object_create
