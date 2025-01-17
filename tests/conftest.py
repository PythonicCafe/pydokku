import tempfile
from pathlib import Path

import pytest

from pydokku import Dokku


@pytest.fixture
def temp_file():
    """Create and cleanup a temporary file"""
    with tempfile.NamedTemporaryFile() as tmpfile:
        yield Path(tmpfile.name)


@pytest.fixture
def temp_dir():
    """Create and cleanup a temporary directory"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


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
