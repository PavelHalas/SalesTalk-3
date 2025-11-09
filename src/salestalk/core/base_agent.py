"""Base agent class for all specialized agents."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pathlib import Path

from salestalk.core.config import AgentConfig, load_agent_config


class BaseAgent(ABC):
    """Base class for all agents in the SalesTalk framework.

    This abstract class defines the common interface and functionality
    that all specialized agents must implement.
    """

    def __init__(self, config: Optional[AgentConfig] = None, config_path: Optional[Path] = None):
        """Initialize the agent.

        Args:
            config: Agent configuration object
            config_path: Path to configuration file (if config not provided)
        """
        if config is None and config_path is None:
            # Load default config based on agent role
            config = load_agent_config(self.get_role())
        elif config is None:
            config = AgentConfig.from_yaml(config_path)

        self.config = config
        self.name = config.name
        self.role = config.role
        self.capabilities = config.capabilities
        self.responsibilities = config.responsibilities
        self.settings = config.settings

    @abstractmethod
    def get_role(self) -> str:
        """Get the agent's role identifier.

        Returns:
            Role identifier string
        """
        pass

    @abstractmethod
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process input and generate output.

        Args:
            input_data: Input data for the agent to process

        Returns:
            Processed output data
        """
        pass

    def get_capabilities(self) -> List[str]:
        """Get list of agent capabilities.

        Returns:
            List of capability strings
        """
        return self.capabilities

    def get_responsibilities(self) -> List[str]:
        """Get list of agent responsibilities.

        Returns:
            List of responsibility strings
        """
        return self.responsibilities

    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate input data.

        Args:
            input_data: Input data to validate

        Returns:
            True if valid, False otherwise
        """
        return isinstance(input_data, dict)

    def __repr__(self) -> str:
        """String representation of the agent."""
        return f"{self.__class__.__name__}(name='{self.name}', role='{self.role}')"
