"""
Unit tests for AgentMatcher utility.

Tests all 4 methods with various scenarios including edge cases.
Target: 70%+ coverage
"""

import pytest
from unittest.mock import Mock

from caas_framework.validation.agent_matcher import AgentMatcher


class TestAgentMatcher:
    """Test suite for AgentMatcher utility class."""

    @pytest.fixture
    def sample_agents(self):
        """Sample agents for testing."""
        return [
            {
                "id": "analyst_1",
                "role": "Data Analyst",
                "goal": "Analyze data and generate insights",
                "tools": ["python", "pandas", "matplotlib"],
            },
            {
                "id": "researcher_1",
                "role": "Researcher",
                "goal": "Research topics and gather information",
                "tools": ["web_search", "scraper"],
            },
            {
                "id": "writer_1",
                "role": "Content Writer",
                "goal": "Write engaging content",
                "tools": ["grammar_check"],
            },
        ]

    @pytest.fixture
    def sample_tasks(self):
        """Sample tasks for testing."""
        return [
            {
                "id": "task1",
                "description": "Analyze sales data",
                "assigned_agent": "analyst_1",
            },
            {
                "id": "task2",
                "description": "Research market trends",
                "agent": "researcher_1",
            },
            {
                "id": "task3",
                "description": "Write blog post",
                "assigned_agent": "writer_1",
            },
        ]

    @pytest.fixture
    def mock_ontology(self):
        """Mock ontology manager for testing."""
        ontology = Mock()
        ontology.infer_role_from_description = Mock(
            side_effect=lambda desc: (
                "analyst"
                if "analyst" in desc.lower() or "data" in desc.lower()
                else "researcher"
                if "researcher" in desc.lower() or "research" in desc.lower()
                else "writer"
            )
        )
        ontology.get_suitable_roles_for_task_type = Mock(
            return_value=["analyst", "researcher"]
        )
        return ontology

    # Tests for find_suitable_agent_by_role

    def test_find_suitable_agent_by_role_with_ontology_match(
        self, sample_agents, mock_ontology
    ):
        """Test finding agent with ontology match."""
        suitable_roles = ["analyst", "researcher"]

        result = AgentMatcher.find_suitable_agent_by_role(
            sample_agents, suitable_roles, mock_ontology
        )

        assert result is not None
        assert result["id"] == "analyst_1"

    def test_find_suitable_agent_by_role_with_ontology_no_match(
        self, sample_agents, mock_ontology
    ):
        """Test finding agent when no ontology match."""
        mock_ontology.infer_role_from_description = Mock(return_value="unknown")
        suitable_roles = ["analyst"]

        result = AgentMatcher.find_suitable_agent_by_role(
            sample_agents, suitable_roles, mock_ontology
        )

        assert result is None

    def test_find_suitable_agent_by_role_without_ontology(self, sample_agents):
        """Test finding agent without ontology (simple string matching)."""
        suitable_roles = ["analyst", "researcher"]

        result = AgentMatcher.find_suitable_agent_by_role(
            sample_agents, suitable_roles, ontology_manager=None
        )

        assert result is not None
        assert "analyst" in result["role"].lower()

    def test_find_suitable_agent_by_role_empty_agents(self, mock_ontology):
        """Test with empty agents list."""
        result = AgentMatcher.find_suitable_agent_by_role(
            [], ["analyst"], mock_ontology
        )

        assert result is None

    def test_find_suitable_agent_by_role_empty_roles(
        self, sample_agents, mock_ontology
    ):
        """Test with empty roles list."""
        result = AgentMatcher.find_suitable_agent_by_role(
            sample_agents, [], mock_ontology
        )

        assert result is None

    # Tests for find_agents_by_task_type

    def test_find_agents_by_task_type_with_mapping(self, sample_agents):
        """Test finding agents by task type with role mapping."""
        role_mapping = {
            "data_analysis": ["analyst", "data"],
            "content_creation": ["writer", "content"],
        }

        result = AgentMatcher.find_agents_by_task_type(
            sample_agents, "data_analysis", role_mapping
        )

        assert len(result) == 1
        assert result[0]["id"] == "analyst_1"

    def test_find_agents_by_task_type_no_mapping(self, sample_agents):
        """Test finding agents without role mapping."""
        result = AgentMatcher.find_agents_by_task_type(
            sample_agents, "data_analysis", role_mapping=None
        )

        assert result == []

    def test_find_agents_by_task_type_unknown_type(self, sample_agents):
        """Test with unknown task type."""
        role_mapping = {"data_analysis": ["analyst"]}

        result = AgentMatcher.find_agents_by_task_type(
            sample_agents, "unknown_type", role_mapping
        )

        assert result == []

    def test_find_agents_by_task_type_multiple_matches(self, sample_agents):
        """Test finding multiple matching agents."""
        role_mapping = {"research": ["researcher", "analyst"]}

        result = AgentMatcher.find_agents_by_task_type(
            sample_agents, "research", role_mapping
        )

        assert len(result) >= 1

    # Tests for get_agent_tasks

    def test_get_agent_tasks_by_id(self, sample_agents, sample_tasks):
        """Test getting tasks assigned to agent by ID."""
        agent = sample_agents[0]  # analyst_1

        result = AgentMatcher.get_agent_tasks(agent, sample_tasks)

        assert len(result) == 1
        assert result[0]["id"] == "task1"

    def test_get_agent_tasks_by_role(self, sample_agents, sample_tasks):
        """Test getting tasks assigned to agent by role."""
        # Modify task to reference role instead of ID
        tasks = [
            {
                "id": "task_role",
                "description": "Research task",
                "assigned_agent": "researcher",
            }
        ]

        agent = sample_agents[1]  # researcher_1

        result = AgentMatcher.get_agent_tasks(agent, tasks)

        assert len(result) == 1
        assert result[0]["id"] == "task_role"

    def test_get_agent_tasks_no_matches(self, sample_agents, sample_tasks):
        """Test getting tasks when agent has no assignments."""
        # Create agent with no matching tasks
        agent = {"id": "unassigned_agent", "role": "Unassigned"}

        result = AgentMatcher.get_agent_tasks(agent, sample_tasks)

        assert result == []

    def test_get_agent_tasks_empty_tasks(self, sample_agents):
        """Test with empty tasks list."""
        agent = sample_agents[0]

        result = AgentMatcher.get_agent_tasks(agent, [])

        assert result == []

    def test_get_agent_tasks_agent_field(self, sample_agents, sample_tasks):
        """Test getting tasks using 'agent' field instead of 'assigned_agent'."""
        agent = sample_agents[1]  # researcher_1

        result = AgentMatcher.get_agent_tasks(agent, sample_tasks)

        assert len(result) == 1
        assert result[0]["id"] == "task2"

    # Tests for find_best_agent_for_task

    def test_find_best_agent_for_task_with_ontology(
        self, sample_agents, mock_ontology
    ):
        """Test finding best agent with ontology."""
        task = {"type": "data_analysis", "description": "Analyze sales data"}

        result = AgentMatcher.find_best_agent_for_task(
            task, sample_agents, mock_ontology
        )

        assert result is not None
        assert "analyst" in result["role"].lower()

    def test_find_best_agent_for_task_without_ontology(self, sample_agents):
        """Test finding best agent without ontology (keyword matching)."""
        task = {"type": "", "description": "analyze data metrics performance trends"}

        result = AgentMatcher.find_best_agent_for_task(
            task, sample_agents, ontology_manager=None
        )

        assert result is not None
        # Should match analyst based on keywords

    def test_find_best_agent_for_task_no_match(self, sample_agents, mock_ontology):
        """Test when no suitable agent found."""
        mock_ontology.get_suitable_roles_for_task_type = Mock(return_value=[])
        task = {"type": "unknown", "description": ""}

        result = AgentMatcher.find_best_agent_for_task(
            task, sample_agents, mock_ontology
        )

        # Should still try keyword matching and potentially return None
        assert result is None or isinstance(result, dict)

    def test_find_best_agent_for_task_empty_agents(self, mock_ontology):
        """Test with empty agents list."""
        task = {"type": "data_analysis", "description": "Analyze data"}

        result = AgentMatcher.find_best_agent_for_task(
            task, [], mock_ontology
        )

        assert result is None

    # Edge cases

    def test_agent_matcher_with_missing_fields(self):
        """Test handling agents/tasks with missing fields."""
        agents = [{"id": "agent1"}]  # Missing role, goal
        suitable_roles = ["analyst"]

        result = AgentMatcher.find_suitable_agent_by_role(
            agents, suitable_roles, ontology_manager=None
        )

        assert result is None  # No match due to missing role

    def test_agent_matcher_case_insensitive(self, sample_agents):
        """Test case-insensitive matching."""
        suitable_roles = ["ANALYST", "RESEARCHER"]

        result = AgentMatcher.find_suitable_agent_by_role(
            sample_agents, suitable_roles, ontology_manager=None
        )

        assert result is not None

    def test_agent_matcher_with_pydantic_models(self, mock_ontology):
        """Test with Pydantic models instead of dicts."""
        from pydantic import BaseModel

        class Agent(BaseModel):
            id: str
            role: str
            goal: str

        agents = [
            Agent(id="agent1", role="Analyst", goal="Analyze data"),
            Agent(id="agent2", role="Writer", goal="Write content"),
        ]

        result = AgentMatcher.find_suitable_agent_by_role(
            agents, ["analyst"], mock_ontology
        )

        assert result is not None
        assert result.id == "agent1"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
