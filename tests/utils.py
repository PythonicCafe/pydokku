import random
import subprocess
from functools import lru_cache
from string import ascii_letters, digits, punctuation

import pytest

from pydokku import Dokku


def random_value(max_chars: int, possible_chars: str = ascii_letters + digits + punctuation + " ") -> str:
    n_chars = random.randint(3, max_chars)
    return "".join(random.choice(possible_chars) for _ in range(n_chars))


def command_available(command):
    try:
        subprocess.run(command, capture_output=True)
    except FileNotFoundError:
        return False
    return True


@lru_cache
def is_dokku_installed():
    return command_available(["dokku", "help"])


@lru_cache
def is_ssh_keygen_installed():
    return command_available(["ssh-keygen", "--help"])


@pytest.fixture
def create_apps():
    apps_names = [f"test-app-{n}" for n in range(1, 3 + 1)]
    dokku = Dokku()
    for app_name in apps_names:
        dokku.apps.create(app_name)
    yield dokku, list(apps_names)
    # A copy of the apps names list is passed to the test so it can modify it without affecting this fixture
    for app_name in apps_names:
        dokku.apps.destroy(app_name)


requires_dokku = pytest.mark.skipif(not is_dokku_installed(), reason="`dokku` command not available")
requires_ssh_keygen = pytest.mark.skipif(not is_ssh_keygen_installed(), reason="`ssh-keygen` command not available")
