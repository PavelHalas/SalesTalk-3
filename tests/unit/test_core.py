"""Unit tests for core functionality."""

import pytest
from pathlib import Path
from salestalk.core.config import AgentConfig, load_agent_config
from salestalk.core.base_agent import BaseAgent


class TestAgentConfig:
    """Tests for AgentConfig class."""

    def test_config_creation(self) -> None:
        """Test creating a config object."""
        config = AgentConfig(
            name="Test Agent",
            role="test",
            description="A test agent",
            capabilities=["testing"],
            responsibilities=["test things"],
        )
        assert config.name == "Test Agent"
        assert config.role == "test"
        assert len(config.capabilities) == 1
        assert len(config.responsibilities) == 1

    def test_load_product_owner_config(self) -> None:
        """Test loading product owner config from YAML."""
        config = load_agent_config("product_owner")
        assert config.name == "Product Owner"
        assert config.role == "product_owner"
        assert "requirement_analysis" in config.capabilities


class TestBaseAgent:
    """Tests for BaseAgent class."""

    def test_base_agent_cannot_be_instantiated(self) -> None:
        """Test that BaseAgent is abstract."""
        with pytest.raises(TypeError):
            BaseAgent()  # type: ignore

    def test_concrete_agent_implementation(self) -> None:
        """Test concrete agent implementation."""
        from salestalk.agents import ProductOwner

        agent = ProductOwner()
        assert isinstance(agent, BaseAgent)
        assert agent.get_role() == "product_owner"
        assert agent.validate_input({}) is True
        assert agent.validate_input("invalid") is False  # type: ignore
