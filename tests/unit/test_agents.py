"""Unit tests for agent implementations."""

import pytest
from salestalk import ProductOwner, Architect, UXExpert, DataScientist, Tester


class TestProductOwner:
    """Tests for ProductOwner agent."""

    def test_initialization(self) -> None:
        """Test ProductOwner initialization."""
        agent = ProductOwner()
        assert agent.role == "product_owner"
        assert agent.name == "Product Owner"

    def test_create_user_story(self) -> None:
        """Test user story creation."""
        agent = ProductOwner()
        story = agent.create_user_story(
            title="Test Story",
            description="As a user, I want to test",
            acceptance_criteria=["Given X, when Y, then Z"],
        )
        assert story["title"] == "Test Story"
        assert story["status"] == "backlog"
        assert len(story["acceptance_criteria"]) == 1

    def test_process(self) -> None:
        """Test processing input."""
        agent = ProductOwner()
        result = agent.process({"requirements": ["feature1", "feature2"]})
        assert result["agent"] == "product_owner"
        assert "user_stories" in result


class TestArchitect:
    """Tests for Architect agent."""

    def test_initialization(self) -> None:
        """Test Architect initialization."""
        agent = Architect()
        assert agent.role == "architect"
        assert agent.name == "Architect"

    def test_design_component(self) -> None:
        """Test component design."""
        agent = Architect()
        component = agent.design_component(
            name="API Gateway", purpose="Route requests", dependencies=["Auth Service"]
        )
        assert component["name"] == "API Gateway"
        assert "dependencies" in component
        assert len(component["dependencies"]) == 1

    def test_process(self) -> None:
        """Test processing input."""
        agent = Architect()
        result = agent.process({"requirements": {"users": 1000}})
        assert result["agent"] == "architect"
        assert "technology_stack" in result


class TestUXExpert:
    """Tests for UXExpert agent."""

    def test_initialization(self) -> None:
        """Test UXExpert initialization."""
        agent = UXExpert()
        assert agent.role == "ux_expert"
        assert agent.name == "UX Expert"

    def test_create_wireframe(self) -> None:
        """Test wireframe creation."""
        agent = UXExpert()
        wireframe = agent.create_wireframe(
            screen_name="Login", elements=["username_field", "password_field", "submit_button"]
        )
        assert wireframe["screen_name"] == "Login"
        assert wireframe["responsive"] is True
        assert len(wireframe["elements"]) == 3

    def test_process(self) -> None:
        """Test processing input."""
        agent = UXExpert()
        result = agent.process({"screens": ["login", "dashboard"]})
        assert result["agent"] == "ux_expert"
        assert "wireframes" in result


class TestDataScientist:
    """Tests for DataScientist agent."""

    def test_initialization(self) -> None:
        """Test DataScientist initialization."""
        agent = DataScientist()
        assert agent.role == "data_scientist"
        assert agent.name == "Data Scientist"

    def test_design_data_pipeline(self) -> None:
        """Test data pipeline design."""
        agent = DataScientist()
        pipeline = agent.design_data_pipeline(
            source="Database",
            transformations=["clean", "transform", "aggregate"],
            destination="Data Warehouse",
        )
        assert pipeline["source"] == "Database"
        assert pipeline["destination"] == "Data Warehouse"
        assert pipeline["monitoring"] is True

    def test_process(self) -> None:
        """Test processing input."""
        agent = DataScientist()
        result = agent.process({"data_requirements": ["user_behavior", "sales_data"]})
        assert result["agent"] == "data_scientist"
        assert "analysis_results" in result


class TestTester:
    """Tests for Tester agent."""

    def test_initialization(self) -> None:
        """Test Tester initialization."""
        agent = Tester()
        assert agent.role == "tester"
        assert agent.name == "Tester"

    def test_create_test_case(self) -> None:
        """Test case creation."""
        agent = Tester()
        test_case = agent.create_test_case(
            name="Login Test",
            description="Test login functionality",
            steps=["Navigate to login", "Enter credentials", "Click submit"],
            expected_result="User logged in successfully",
        )
        assert test_case["name"] == "Login Test"
        assert test_case["status"] == "pending"
        assert len(test_case["steps"]) == 3

    def test_process(self) -> None:
        """Test processing input."""
        agent = Tester()
        result = agent.process({"features": ["login", "signup"]})
        assert result["agent"] == "tester"
        assert "test_cases" in result
