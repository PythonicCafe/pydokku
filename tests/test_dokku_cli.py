import re

from dokkupy.dokku_cli import Dokku

# TODO: may use dokkupy.inspector to assert the result of each command or mock the command execution and check the
# to-be-executed command (list of strings)


def test_version():
    dokku = Dokku()
    version = dokku.version()
    assert re.match(r"[0-9]+\.[0-9]+\.[0-9]+", version) is not None
