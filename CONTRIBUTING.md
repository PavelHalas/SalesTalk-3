# Contributing to SalesTalk

Thank you for your interest in contributing to SalesTalk! This document provides guidelines and instructions for contributing.

## Code of Conduct

We are committed to providing a welcoming and inclusive experience for everyone. We expect all contributors to:

- Be respectful and inclusive
- Exercise empathy and kindness
- Accept constructive criticism gracefully
- Focus on what is best for the community
- Show courtesy and respect to other community members

## How to Contribute

### Reporting Issues

If you find a bug or have a suggestion:

1. Check if the issue already exists in the issue tracker
2. If not, create a new issue with:
   - Clear, descriptive title
   - Detailed description of the problem or suggestion
   - Steps to reproduce (for bugs)
   - Expected vs. actual behavior
   - Environment details (OS, Python version, etc.)

### Submitting Pull Requests

1. **Fork the repository** and create a branch from `main`
2. **Make your changes** following our coding standards
3. **Add tests** for any new functionality
4. **Ensure all tests pass** by running `pytest`
5. **Update documentation** as needed
6. **Commit your changes** with clear, descriptive messages
7. **Submit a pull request** with:
   - Description of changes
   - Related issue number (if applicable)
   - Any breaking changes highlighted

### Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/SalesTalk-3.git
cd SalesTalk-3

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -r requirements-dev.txt
pip install -e .
```

### Coding Standards

We follow Python best practices and PEP 8:

```bash
# Format code with Black
black src/ tests/

# Lint with Ruff
ruff check src/ tests/

# Type check with mypy
mypy src/

# Run tests
pytest --cov=salestalk
```

**Code Style Guidelines:**
- Use type hints for all function parameters and returns
- Write docstrings for all public modules, classes, and functions
- Keep functions focused and single-purpose
- Maximum line length: 100 characters
- Use descriptive variable names

### Testing

All contributions should include appropriate tests:

- **Unit tests**: Test individual components in isolation
- **Integration tests**: Test component interactions
- **Test coverage**: Aim for at least 80% coverage

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=salestalk --cov-report=html

# Run specific test file
pytest tests/unit/test_agents.py

# Run tests matching a pattern
pytest -k "test_product_owner"
```

### Documentation

Update documentation when:
- Adding new features
- Changing existing functionality
- Adding new agents or capabilities

Documentation locations:
- `README.md`: Project overview and quick start
- `docs/guides/`: User guides and tutorials
- `docs/agents/`: Agent-specific documentation
- Code docstrings: API documentation

### Commit Messages

Write clear, concise commit messages:

```
Add feature for agent collaboration

- Implement message passing between agents
- Add collaboration workflow examples
- Update documentation with collaboration patterns

Fixes #123
```

Format:
- First line: Brief summary (50 chars or less)
- Blank line
- Detailed description (if needed)
- Reference related issues

### Pull Request Process

1. Update the README.md or documentation with details of changes
2. Update version numbers following [Semantic Versioning](https://semver.org/)
3. The PR will be merged once you have sign-off from maintainers

## Development Workflow

1. **Create an issue** describing the feature or bug
2. **Discuss the approach** in the issue comments
3. **Fork and create a branch** for your work
4. **Develop and test** your changes
5. **Submit a pull request** for review
6. **Address review feedback** as needed
7. **Celebrate** when merged! 🎉

## Agent Development Guidelines

When adding new agents:

1. Create agent class inheriting from `BaseAgent`
2. Implement required methods: `get_role()` and `process()`
3. Add configuration file in `config/agents/`
4. Create documentation in `docs/agents/`
5. Add unit tests in `tests/unit/`
6. Update main README and other relevant docs

Example structure:
```python
from salestalk.core.base_agent import BaseAgent

class NewAgent(BaseAgent):
    def get_role(self) -> str:
        return "new_agent"
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        # Implementation
        pass
```

## Getting Help

- Check existing documentation
- Search existing issues
- Ask questions in discussions
- Reach out to maintainers

## Recognition

Contributors will be recognized in:
- CONTRIBUTORS.md file
- Release notes
- Project documentation

Thank you for contributing to SalesTalk!
