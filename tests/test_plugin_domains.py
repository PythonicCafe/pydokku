import random
import string

from pydokku.dokku_cli import Dokku
from pydokku.models import Domain
from tests.utils import create_apps, random_value, requires_dokku  # noqa


def random_domains():
    possible_chars = string.ascii_lowercase + string.digits + "-"
    return [f"test-{random_value(10, possible_chars=possible_chars)}.net" for _ in range(random.randint(3, 5))]


def test_object_classes():
    dokku = Dokku()
    assert dokku.domains.object_classes == (Domain,)


def test_add_command():
    dokku = Dokku()
    app_name = "test-app-domains"
    domains = random_domains()
    command = dokku.domains.add(app_name, domains, execute=False)
    assert command.command == ["dokku", "domains:add", app_name] + domains
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False
    command = dokku.domains.add(None, domains, execute=False)
    assert command.command == ["dokku", "domains:add-global"] + domains
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False


def test_set_command():
    dokku = Dokku()
    app_name = "test-app-domains"
    domains = random_domains()
    command = dokku.domains.set(app_name, domains, execute=False)
    assert command.command == ["dokku", "domains:set", app_name] + domains
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False
    command = dokku.domains.set(None, domains, execute=False)
    assert command.command == ["dokku", "domains:set-global"] + domains
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False


def test_remove_command():
    dokku = Dokku()
    app_name = "test-app-domains"
    domains = random_domains()
    command = dokku.domains.remove(app_name, domains, execute=False)
    assert command.command == ["dokku", "domains:remove", app_name] + domains
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False
    command = dokku.domains.remove(None, domains, execute=False)
    assert command.command == ["dokku", "domains:remove-global"] + domains
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False


def test_clear_command():
    dokku = Dokku()
    app_name = "test-app-domains"
    command = dokku.domains.clear(app_name, execute=False)
    assert command.command == ["dokku", "domains:clear", app_name]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False


def test_enable_command():
    dokku = Dokku()
    app_name = "test-app-domains"
    command = dokku.domains.enable(app_name, execute=False)
    assert command.command == ["dokku", "domains:enable", app_name]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False


def test_disable_command():
    dokku = Dokku()
    app_name = "test-app-domains"
    command = dokku.domains.disable(app_name, execute=False)
    assert command.command == ["dokku", "domains:disable", app_name]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False


def test_parse_report():
    stdout = """
        =====> Global domains information
            Domains global enabled:        true
            Domains global vhosts:         dokku.example.net
        =====> test-app-7 domains information
            Domains app enabled:           true
            Domains app vhosts:
            Domains global enabled:        true
            Domains global vhosts:         dokku.example.net
        =====> test-app-8 domains information
            Domains app enabled:           true
            Domains app vhosts:            test-app-8.dokku.example.net
            Domains global enabled:        true
            Domains global vhosts:         dokku.example.net
        =====> test-app-9 domains information
            Domains app enabled:           true
            Domains app vhosts:            app9.example.com app9.example.net
            Domains global enabled:        true
            Domains global vhosts:         dokku.example.net
    """
    expected = [
        {
            "app_name": "Global",
            "app_enabled": None,
            "app_domains": None,
            "global_enabled": True,
            "global_domains": ["dokku.example.net"],
        },
        {
            "app_name": "test-app-7",
            "app_enabled": True,
            "app_domains": [],
            "global_enabled": True,
            "global_domains": ["dokku.example.net"],
        },
        {
            "app_name": "test-app-8",
            "app_enabled": True,
            "app_domains": ["test-app-8.dokku.example.net"],
            "global_enabled": True,
            "global_domains": ["dokku.example.net"],
        },
        {
            "app_name": "test-app-9",
            "app_enabled": True,
            "app_domains": ["app9.example.com", "app9.example.net"],
            "global_enabled": True,
            "global_domains": ["dokku.example.net"],
        },
    ]
    dokku = Dokku()
    rows_parser = dokku.domains._get_rows_parser()
    result = rows_parser(stdout)
    assert result == expected


def test_convert_rows():
    input_rows = [
        {
            "app_name": "Global",
            "app_enabled": None,
            "app_domains": None,
            "global_enabled": True,
            "global_domains": ["dokku.example.net"],
        },
        {
            "app_name": "test-app-7",
            "app_enabled": True,
            "app_domains": [],
            "global_enabled": True,
            "global_domains": ["dokku.example.net"],
        },
        {
            "app_name": "test-app-8",
            "app_enabled": True,
            "app_domains": ["test-app-8.dokku.example.net"],
            "global_enabled": True,
            "global_domains": ["dokku.example.net"],
        },
        {
            "app_name": "test-app-9",
            "app_enabled": True,
            "app_domains": ["app9.example.com", "app9.example.net"],
            "global_enabled": True,
            "global_domains": ["dokku.example.net"],
        },
    ]
    all_domains = [
        Domain(
            app_name=None,
            enabled=True,
            domains=["dokku.example.net"],
        ),
        Domain(
            app_name="test-app-7",
            enabled=True,
            domains=[],
        ),
        Domain(
            app_name="test-app-8",
            enabled=True,
            domains=["test-app-8.dokku.example.net"],
        ),
        Domain(
            app_name="test-app-9",
            enabled=True,
            domains=["app9.example.com", "app9.example.net"],
        ),
    ]
    dokku = Dokku()
    result = dokku.domains._convert_rows(input_rows)
    assert result == all_domains


@requires_dokku
def test_add_list_remove(create_apps):
    dokku, apps_names = create_apps
    apps_names.append(None)  # Global
    apps_domains = [random_domains() for _ in range(4)]

    try:
        for app_name, domains in zip(apps_names, apps_domains):
            before = dokku.domains.list(app_name)[0].domains
            dokku.domains.add(app_name, domains)
            after = dokku.domains.list(app_name)[0].domains
            assert len(after) == len(before) + len(domains)
            assert set(before).issubset(set(after))
            random_domain = random.choice(domains)
            dokku.domains.remove(app_name, [random_domain])
            final = dokku.domains.list(app_name)[0].domains
            assert len(final) == len(after) - 1
            assert random_domain not in final
    finally:
        dokku.domains.set(app_name=None, domains=["dokku.example.net"])


@requires_dokku
def test_add_set_clear(create_apps):
    dokku, apps_names = create_apps
    apps_names.append(None)  # Global
    apps_domains = [random_domains() for _ in range(4)]

    try:
        for app_name, domains in zip(apps_names, apps_domains):
            # The first domain will be added after, then we set (overwrite) with the remaining ones
            old_domain = domains[0]
            new_domains = domains[1:]
            dokku.domains.add(app_name, [old_domain])
            before = dokku.domains.list(app_name)[0].domains
            assert old_domain in before
            dokku.domains.set(app_name, new_domains)
            after = dokku.domains.list(app_name)[0].domains
            assert old_domain not in after
            assert sorted(after) == sorted(new_domains)

            dokku.domains.clear(app_name)  # This WON'T remove ALL domains! Will restore to global ones
            after_clear_1 = dokku.domains.list(app_name)[0].domains
            dokku.domains.add(app_name, [f"test-{app_name}.custom.com"])
            after_add = dokku.domains.list(app_name)[0].domains
            assert len(after_add) == len(after_clear_1) + 1  # New custom domain added
            dokku.domains.clear(app_name)
            after_clear_2 = dokku.domains.list(app_name)[0].domains
            assert sorted(after_clear_2) == sorted(after_clear_1)  # Only the custom was "cleared"
    finally:
        dokku.domains.set(app_name=None, domains=["dokku.example.net"])
