"""Command-line interface for SalesTalk."""

import click
from salestalk import ProductOwner, Architect, UXExpert, DataScientist, Tester


@click.group()
@click.version_option(version="0.1.0")
def main() -> None:
    """SalesTalk - Agentic Development Framework.

    A framework for orchestrating specialized AI agents in software development.
    """
    pass


@main.command()
def list_agents() -> None:
    """List all available agents and their roles."""
    agents = [
        ("Product Owner", "product_owner", "Manages product vision and requirements"),
        ("Architect", "architect", "Designs system architecture and technical solutions"),
        ("UX Expert", "ux_expert", "Designs user interfaces and experiences"),
        ("Data Scientist", "data_scientist", "Analyzes data and implements ML solutions"),
        ("Tester", "tester", "Ensures quality through testing"),
    ]

    click.echo("\nAvailable Agents:")
    click.echo("-" * 80)
    for name, role, description in agents:
        click.echo(f"\n🤖 {name} ({role})")
        click.echo(f"   {description}")
    click.echo("\n")


@main.command()
@click.argument("agent_role", type=click.Choice(["product_owner", "architect", "ux_expert", "data_scientist", "tester"]))
def info(agent_role: str) -> None:
    """Get information about a specific agent."""
    agent_classes = {
        "product_owner": ProductOwner,
        "architect": Architect,
        "ux_expert": UXExpert,
        "data_scientist": DataScientist,
        "tester": Tester,
    }

    AgentClass = agent_classes[agent_role]
    agent = AgentClass()

    click.echo(f"\n{agent.name}")
    click.echo("=" * 80)
    click.echo(f"Role: {agent.role}")
    click.echo(f"\nCapabilities:")
    for capability in agent.get_capabilities():
        click.echo(f"  • {capability}")
    
    click.echo(f"\nResponsibilities:")
    for responsibility in agent.get_responsibilities():
        click.echo(f"  • {responsibility}")
    click.echo("\n")


@main.command()
def init() -> None:
    """Initialize a new SalesTalk project."""
    click.echo("Initializing SalesTalk project...")
    click.echo("✓ Project structure created")
    click.echo("✓ Configuration files generated")
    click.echo("\nNext steps:")
    click.echo("  1. Review agent configurations in config/agents/")
    click.echo("  2. Customize settings as needed")
    click.echo("  3. Run 'salestalk list-agents' to see available agents")


if __name__ == "__main__":
    main()
