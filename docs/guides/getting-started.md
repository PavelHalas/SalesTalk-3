# Getting Started with SalesTalk

## Introduction

SalesTalk is an agentic development framework that orchestrates multiple specialized AI agents to collaborate on software development projects. This guide will help you get started with the framework.

## Installation

### Prerequisites

Before you begin, ensure you have:
- Python 3.9 or higher installed
- pip package manager
- Git (for version control)

### Step 1: Clone the Repository

```bash
git clone https://github.com/PavelHalas/SalesTalk-3.git
cd SalesTalk-3
```

### Step 2: Create a Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/Mac:
source venv/bin/activate
# On Windows:
venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
# Install core dependencies
pip install -r requirements.txt

# For development (optional)
pip install -r requirements-dev.txt

# Install package in editable mode
pip install -e .
```

## Quick Start

### Using the CLI

The SalesTalk CLI provides quick access to agent information:

```bash
# List all available agents
salestalk list-agents

# Get information about a specific agent
salestalk info product_owner

# Initialize a new project
salestalk init
```

### Using the Python API

```python
from salestalk import ProductOwner, Architect, UXExpert, DataScientist, Tester

# Initialize agents
product_owner = ProductOwner()
architect = Architect()
ux_expert = UXExpert()
data_scientist = DataScientist()
tester = Tester()

# Example: Product Owner creates a user story
user_story = product_owner.create_user_story(
    title="User Authentication",
    description="As a user, I want to log in securely",
    acceptance_criteria=[
        "Given valid credentials, when I log in, then I access my account",
        "Given invalid credentials, when I log in, then I see an error"
    ]
)

# Example: Architect designs a component
component = architect.design_component(
    name="API Gateway",
    purpose="Route and authenticate API requests",
    dependencies=["Auth Service", "User Service"]
)

# Example: Tester creates a test case
test_case = tester.create_test_case(
    name="Login Success Test",
    description="Verify successful login with valid credentials",
    steps=[
        "Navigate to login page",
        "Enter valid username and password",
        "Click login button"
    ],
    expected_result="User is redirected to dashboard"
)
```

## Agent Roles

### Product Owner 🎯
Manages product vision, requirements, and prioritization.

### Architect 🏗️
Designs system architecture and makes technical decisions.

### UX Expert 🎨
Creates user interfaces and ensures great user experience.

### Data Scientist 📊
Analyzes data and implements ML/AI solutions.

### Tester 🧪
Ensures quality through comprehensive testing.

## Configuration

Each agent can be configured via YAML files in `config/agents/`:

```yaml
# Example: config/agents/product_owner.yaml
agent:
  name: "Product Owner"
  role: "product_owner"
  version: "1.0.0"

settings:
  prioritization_method: "moscow"
  user_story_template: "as_a_want_so_that"
```

## Next Steps

1. **Explore Agent Documentation**: Read detailed docs in `docs/agents/`
2. **Review Examples**: Check out example workflows
3. **Customize Configuration**: Adjust agent settings for your needs
4. **Start Building**: Begin using agents in your projects

## Common Tasks

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=salestalk

# Run specific test file
pytest tests/unit/test_agents.py
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint code
ruff check src/ tests/

# Type check
mypy src/
```

## Troubleshooting

### Import Errors
Make sure you've installed the package in editable mode:
```bash
pip install -e .
```

### Configuration Not Found
Ensure your working directory is the project root, or provide explicit config paths.

## Getting Help

- Check the [full documentation](../README.md)
- Review [agent-specific guides](../agents/)
- Open an issue on GitHub
- Join community discussions

## What's Next?

- Learn about [Architecture](architecture.md)
- Explore the [API Reference](api-reference.md)
- Read about [Agent Collaboration Patterns](collaboration-patterns.md)
