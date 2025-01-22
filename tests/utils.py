import random
import subprocess
from functools import lru_cache
from string import ascii_letters, digits, punctuation

import pytest


def random_value(max_chars: int, possible_chars: str = ascii_letters + digits + punctuation + " ") -> str:
    n_chars = random.randint(3, max_chars)
    return "".join(random.choice(possible_chars) for _ in range(n_chars))


def random_alphanum(max_chars: int) -> str:
    return random_value(max_chars=max_chars, possible_chars=ascii_letters + digits)


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


requires_dokku = pytest.mark.skipif(not is_dokku_installed(), reason="`dokku` command not available")
requires_ssh_keygen = pytest.mark.skipif(not is_ssh_keygen_installed(), reason="`ssh-keygen` command not available")
