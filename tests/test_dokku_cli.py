import re

from dokkupy.dokku_cli import Dokku
from tests.utils import requires_dokku


@requires_dokku
def test_version():
    dokku = Dokku()
    version = dokku.version()
    assert re.match(r"[0-9]+\.[0-9]+\.[0-9]+", version) is not None


# TODO: implement tests for SSH (key without passphrase)
# TODO: implement tests for SSH (key with passphrase)
