import tempfile
from pathlib import Path

import pytest


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
