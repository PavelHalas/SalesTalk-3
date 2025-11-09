"""Configuration management for agents."""

from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml
from pydantic import BaseModel, Field


class AgentConfig(BaseModel):
    """Configuration for an agent."""

    name: str = Field(..., description="Agent name")
    role: str = Field(..., description="Agent role identifier")
    version: str = Field(default="1.0.0", description="Agent version")
    description: str = Field(..., description="Agent description")
    capabilities: List[str] = Field(default_factory=list, description="Agent capabilities")
    responsibilities: List[str] = Field(
        default_factory=list, description="Agent responsibilities"
    )
    settings: Dict[str, Any] = Field(default_factory=dict, description="Agent settings")
    outputs: List[str] = Field(default_factory=list, description="Expected outputs")

    @classmethod
    def from_yaml(cls, path: Path) -> "AgentConfig":
        """Load configuration from YAML file.

        Args:
            path: Path to YAML configuration file

        Returns:
            AgentConfig instance
        """
        with open(path, "r") as f:
            data = yaml.safe_load(f)

        agent_data = data.get("agent", {})
        return cls(
            name=agent_data.get("name", "Unknown"),
            role=agent_data.get("role", "unknown"),
            version=agent_data.get("version", "1.0.0"),
            description=agent_data.get("description", ""),
            capabilities=data.get("capabilities", []),
            responsibilities=data.get("responsibilities", []),
            settings=data.get("settings", {}),
            outputs=data.get("outputs", []),
        )


def load_agent_config(agent_role: str, config_dir: Optional[Path] = None) -> AgentConfig:
    """Load agent configuration by role.

    Args:
        agent_role: Role identifier (e.g., 'product_owner')
        config_dir: Optional custom config directory

    Returns:
        AgentConfig instance
    """
    if config_dir is None:
        # Default to config/agents relative to project root
        config_dir = Path(__file__).parent.parent.parent.parent / "config" / "agents"

    config_path = config_dir / f"{agent_role}.yaml"
    return AgentConfig.from_yaml(config_path)
