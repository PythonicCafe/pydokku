import random
import string

from dokkupy.dokku_cli import Dokku
from tests.utils import random_value, requires_dokku


def random_domains():
    possible_chars = string.ascii_lowercase + string.digits + "-"
    return [f"test-{random_value(10, possible_chars=possible_chars)}.net" for _ in range(random.randint(3, 5))]


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


@requires_dokku
def test_add_list_remove():
    dokku = Dokku()
    app_name_1 = "test-app-domains-1"
    app_name_2 = "test-app-domains-2"
    app_name_3 = None  # Global
    domains_1 = random_domains()
    domains_2 = random_domains()
    domains_3 = random_domains()

    dokku.apps.create(app_name_1)
    dokku.apps.create(app_name_2)

    for app_name, domains in ((app_name_1, domains_1), (app_name_2, domains_2), (app_name_3, domains_3)):
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

    dokku.apps.destroy(app_name_1)
    dokku.apps.destroy(app_name_2)


@requires_dokku
def test_add_set_clear():
    dokku = Dokku()
    app_name_1 = "test-app-domains-1"
    app_name_2 = "test-app-domains-2"
    app_name_3 = None  # Global
    domains_1 = random_domains()
    domains_2 = random_domains()
    domains_3 = random_domains()

    dokku.apps.create(app_name_1)
    dokku.apps.create(app_name_2)

    for app_name, domains in ((app_name_1, domains_1), (app_name_2, domains_2), (app_name_3, domains_3)):
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

    dokku.apps.destroy(app_name_1)
    dokku.apps.destroy(app_name_2)
