"""Pytest configuration and fixtures."""

import pytest
from pathlib import Path


@pytest.fixture
def project_root() -> Path:
    """Get the project root directory.

    Returns:
        Path to project root
    """
    return Path(__file__).parent.parent


@pytest.fixture
def config_dir(project_root: Path) -> Path:
    """Get the config directory.

    Args:
        project_root: Project root fixture

    Returns:
        Path to config directory
    """
    return project_root / "config" / "agents"
