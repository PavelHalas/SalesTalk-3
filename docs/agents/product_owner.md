# Product Owner Agent

## Overview

The Product Owner agent is responsible for managing the product vision, defining requirements, and ensuring that development aligns with business goals.

## Capabilities

- **Requirement Analysis**: Analyze and document product requirements
- **Backlog Management**: Prioritize and maintain the product backlog
- **User Story Creation**: Write clear, actionable user stories
- **Stakeholder Communication**: Interface with stakeholders and the development team
- **Priority Management**: Make trade-off decisions and prioritize features
- **Acceptance Criteria Definition**: Define clear success criteria for features

## Responsibilities

1. Define and communicate the product vision
2. Create and prioritize the product backlog
3. Write user stories with acceptance criteria
4. Manage stakeholder expectations
5. Validate delivered features against requirements
6. Make trade-off decisions between features and timeline

## Configuration

The Product Owner agent is configured in `config/agents/product_owner.yaml`. Key settings include:

- **Prioritization Method**: MoSCoW (Must have, Should have, Could have, Won't have)
- **User Story Template**: "As a [user], I want [feature], so that [benefit]"
- **Acceptance Criteria Format**: Gherkin (Given-When-Then)

## Outputs

- Product backlog (prioritized list of features)
- User stories with acceptance criteria
- Requirements documentation
- Feature specifications

## Example Usage

```python
from salestalk.agents import ProductOwner

# Initialize the agent
po = ProductOwner()

# Create a user story
story = po.create_user_story(
    title="User Login",
    description="As a user, I want to log in securely, so that I can access my account",
    acceptance_criteria=[
        "Given valid credentials, when user logs in, then access is granted",
        "Given invalid credentials, when user logs in, then error message is shown"
    ]
)

# Process requirements
result = po.process({
    "project": "E-commerce Platform",
    "requirements": ["user authentication", "product catalog", "shopping cart"]
})
```

## Collaboration

The Product Owner works closely with:
- **Architect**: To understand technical constraints and possibilities
- **UX Expert**: To ensure features align with user needs
- **Tester**: To define acceptance criteria and validate features

## Best Practices

1. Keep user stories small and focused
2. Include clear acceptance criteria for every story
3. Prioritize based on business value and dependencies
4. Regularly groom the backlog
5. Maintain open communication with all stakeholders
6. Validate features against the original vision
