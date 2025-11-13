"""Shared pytest fixtures and configuration for all tests."""

import sys
from pathlib import Path

import pytest

# Add src to path so tests can import modules
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


@pytest.fixture(scope="session")
def project_root():
    """Return the project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def data_dir(project_root):
    """Return the data directory path."""
    return project_root / "src" / "modus_comps_tool" / "data"
