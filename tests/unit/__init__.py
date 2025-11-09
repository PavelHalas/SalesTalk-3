"""Test __init__ files to ensure proper package structure."""

import pytest


def test_salestalk_package_import() -> None:
    """Test that salestalk package can be imported."""
    import salestalk

    assert hasattr(salestalk, "__version__")
    assert salestalk.__version__ == "0.1.0"


def test_all_agents_importable() -> None:
    """Test that all agents can be imported from main package."""
    from salestalk import ProductOwner, Architect, UXExpert, DataScientist, Tester

    assert ProductOwner is not None
    assert Architect is not None
    assert UXExpert is not None
    assert DataScientist is not None
    assert Tester is not None


def test_core_module_import() -> None:
    """Test that core module can be imported."""
    from salestalk.core import BaseAgent, AgentConfig

    assert BaseAgent is not None
    assert AgentConfig is not None


def test_agents_module_import() -> None:
    """Test that agents module can be imported."""
    from salestalk import agents

    assert hasattr(agents, "ProductOwner")
    assert hasattr(agents, "Architect")
    assert hasattr(agents, "UXExpert")
    assert hasattr(agents, "DataScientist")
    assert hasattr(agents, "Tester")
