"""Integration tests for agent collaboration."""

import pytest
from salestalk import ProductOwner, Architect, UXExpert, DataScientist, Tester


class TestAgentCollaboration:
    """Tests for agent collaboration workflows."""

    def test_product_development_workflow(self) -> None:
        """Test a complete product development workflow."""
        # Product Owner defines requirements
        po = ProductOwner()
        user_story = po.create_user_story(
            title="User Dashboard",
            description="As a user, I want a dashboard to see my activity",
            acceptance_criteria=["Dashboard shows user stats", "Data is updated in real-time"],
        )
        assert user_story["title"] == "User Dashboard"

        # Architect designs the system
        architect = Architect()
        component = architect.design_component(
            name="Dashboard Service",
            purpose="Provide dashboard data",
            dependencies=["User Service", "Analytics Service"],
        )
        assert component["name"] == "Dashboard Service"

        # UX Expert creates wireframe
        ux = UXExpert()
        wireframe = ux.create_wireframe(
            screen_name="Dashboard", elements=["stats_panel", "activity_feed", "charts"]
        )
        assert wireframe["screen_name"] == "Dashboard"

        # Data Scientist designs analytics pipeline
        ds = DataScientist()
        pipeline = ds.design_data_pipeline(
            source="User Events",
            transformations=["aggregate", "calculate_metrics"],
            destination="Analytics DB",
        )
        assert pipeline["source"] == "User Events"

        # Tester creates test cases
        tester = Tester()
        test_case = tester.create_test_case(
            name="Dashboard Load Test",
            description="Verify dashboard loads correctly",
            steps=["Login", "Navigate to dashboard", "Verify data displays"],
            expected_result="Dashboard shows current user data",
        )
        assert test_case["name"] == "Dashboard Load Test"

    def test_all_agents_initialized(self) -> None:
        """Test that all agents can be initialized."""
        agents = [
            ProductOwner(),
            Architect(),
            UXExpert(),
            DataScientist(),
            Tester(),
        ]
        assert len(agents) == 5
        assert all(hasattr(agent, "role") for agent in agents)
        assert all(hasattr(agent, "process") for agent in agents)
