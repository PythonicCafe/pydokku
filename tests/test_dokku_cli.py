import re

from dokkupy.dokku_cli import Dokku


def test_version():
    dokku = Dokku()
    version = dokku.version()
    assert re.match(r"[0-9]+\.[0-9]+\.[0-9]+", version) is not None
