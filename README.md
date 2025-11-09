# SalesTalk-3

An agentic development framework featuring specialized AI agents for comprehensive software development.

## Overview

SalesTalk-3 is a Python-based framework that orchestrates multiple specialized AI agents to collaborate on software development projects. Each agent has specific expertise and responsibilities, working together to deliver high-quality software solutions.

## Agent Roles

### 🎯 Product Owner
- Defines product vision and requirements
- Manages backlog and prioritization
- Creates user stories and acceptance criteria
- Stakeholder communication

### 🏗️ Architect
- Designs system architecture and technical solutions
- Makes technology stack decisions
- Ensures scalability and maintainability
- Creates technical documentation

### 🎨 UX Expert
- Designs user interfaces and experiences
- Creates wireframes and mockups
- Ensures accessibility and usability
- Conducts user research

### 📊 Data Scientist
- Analyzes data requirements and patterns
- Designs data models and pipelines
- Implements ML/AI solutions
- Provides insights and metrics

### 🧪 Tester
- Creates test strategies and plans
- Writes automated tests
- Performs quality assurance
- Reports and tracks issues

## Project Structure

```
salestalk/
├── src/salestalk/          # Main package source code
│   ├── agents/             # Agent implementations
│   ├── core/               # Core framework functionality
│   └── utils/              # Utility functions
├── tests/                  # Test suite
│   ├── unit/               # Unit tests
│   └── integration/        # Integration tests
├── docs/                   # Documentation
│   ├── agents/             # Agent-specific documentation
│   └── guides/             # User and developer guides
├── config/                 # Configuration files
│   └── agents/             # Agent configuration files
└── .github/                # GitHub workflows and actions
```

## Installation

### Prerequisites
- Python 3.9 or higher
- pip or poetry

### Basic Installation

```bash
# Clone the repository
git clone https://github.com/PavelHalas/SalesTalk-3.git
cd SalesTalk-3

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Development Installation

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Install package in editable mode
pip install -e .
```

## Quick Start

```python
from salestalk.agents import ProductOwner, Architect, UXExpert, DataScientist, Tester

# Initialize agents
product_owner = ProductOwner()
architect = Architect()
ux_expert = UXExpert()
data_scientist = DataScientist()
tester = Tester()

# Start collaboration workflow
# (Implementation details in docs/guides/getting-started.md)
```

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=salestalk --cov-report=html

# Run specific test file
pytest tests/unit/test_agents.py
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint code
ruff check src/ tests/

# Type checking
mypy src/
```

## Configuration

Agent configurations are stored in `config/agents/` directory. Each agent has its own YAML configuration file:

- `product_owner.yaml` - Product Owner agent configuration
- `architect.yaml` - Architect agent configuration
- `ux_expert.yaml` - UX Expert agent configuration
- `data_scientist.yaml` - Data Scientist agent configuration
- `tester.yaml` - Tester agent configuration

## Documentation

Comprehensive documentation is available in the `docs/` directory:

- [Getting Started Guide](docs/guides/getting-started.md)
- [Agent Documentation](docs/agents/)
- [Architecture Overview](docs/guides/architecture.md)
- [API Reference](docs/guides/api-reference.md)

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details on:
- Code of conduct
- Development workflow
- Coding standards
- Pull request process

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Roadmap

- [ ] Core agent framework implementation
- [ ] Agent communication protocol
- [ ] CLI interface
- [ ] Web UI dashboard
- [ ] Integration with popular development tools
- [ ] Plugin system for custom agents
- [ ] Multi-project orchestration

## Support

For questions, issues, or suggestions:
- Open an issue on GitHub
- Check the documentation
- Join our community discussions

## Acknowledgments

Built with modern Python best practices and designed for scalability and extensibility.