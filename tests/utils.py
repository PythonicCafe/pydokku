import random
import subprocess
from functools import lru_cache
from string import ascii_letters, digits, punctuation

import pytest


def random_value(max_chars: int, possible_chars: str = ascii_letters + digits + punctuation + " ") -> str:
    n_chars = random.randint(3, max_chars)
    return "".join(random.choice(possible_chars) for _ in range(n_chars))


@lru_cache
def is_dokku_installed():
    try:
        result = subprocess.run(["dokku", "help"], capture_output=True)
    except FileNotFoundError:
        return False
    else:
        return result.returncode == 0


requires_dokku = pytest.mark.skipif(not is_dokku_installed(), reason="Dokku command not available")
