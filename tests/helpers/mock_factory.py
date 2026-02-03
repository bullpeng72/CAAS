"""
Test Mock Factory

Provides reusable mock objects to avoid duplication across test files.
Centralized mock creation reduces technical debt and ensures consistency.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

from caas_framework.agents.base import AgentPhase
from caas_framework.models.specifications import (
    ConcretizedRequirement,
    FeatureSpec,
    SystemScope,
)


class MockFactory:
    """
    Factory for creating consistent mock objects across tests.

    Benefits:
    - Eliminates duplicate mock setup code
    - Ensures consistency across test suites
    - Single source of truth for mock data
    - Easy to update when models change
    """

    @staticmethod
    def create_golden_data(
        project_name: str = "Test Project",
        features: Optional[List[FeatureSpec]] = None,
        minimal: bool = False
    ) -> ConcretizedRequirement:
        """
        Create mock Golden Data with proper structure.

        Args:
            project_name: Name of the project
            features: Custom features (auto-generated if None)
            minimal: If True, creates minimal Golden Data

        Returns:
            ConcretizedRequirement with all required fields
        """
        # Default features if not provided
        if features is None:
            features = [
                FeatureSpec(
                    id="feat_001",
                    name="User Registration",
                    description="Allow users to register with email and password",
                    priority="high",
                    acceptance_criteria=[
                        "User can register with valid email",
                        "Password must be at least 8 characters",
                        "Duplicate emails are rejected"
                    ]
                ),
                FeatureSpec(
                    id="feat_002",
                    name="User Login",
                    description="Allow users to log in with credentials",
                    priority="high",
                    acceptance_criteria=[
                        "User can login with valid credentials",
                        "Invalid credentials show error",
                        "Session is created on successful login"
                    ]
                )
            ]

        # System scope
        system_scope = SystemScope(
            project_name=project_name,
            purpose="Test project for automated testing",
            target_users=["developers", "testers"],
            system_type="rest_api",
            domain="testing"
        )

        if minimal:
            return ConcretizedRequirement(
                system_scope=system_scope,
                features=features,
                constraints=[],
                assumptions=[]
            )

        # Full Golden Data (with only available fields)
        return ConcretizedRequirement(
            system_scope=system_scope,
            features=features,
            constraints=[
                "Must use Python 3.11+",
                "Must follow PEP 8 style guide"
            ],
            assumptions=[
                "Users have valid email addresses",
                "System is deployed on cloud infrastructure"
            ]
        )

    @staticmethod
    def create_llm_plugin(
        model_name: str = "mock-gpt-4",
        delay_ms: int = 100,
        responses: Optional[Dict[AgentPhase, str]] = None
    ) -> MagicMock:
        """
        Create mock LLM plugin with configurable responses.

        Args:
            model_name: Name of the model
            delay_ms: Simulated delay in milliseconds
            responses: Custom responses per phase

        Returns:
            Mock LLM plugin
        """
        import asyncio
        import json

        # Default responses
        default_responses = {
            AgentPhase.DISCOVERY: {
                "domain": "TODO_MANAGEMENT",
                "requirements": ["Create tasks", "List tasks", "Delete tasks"],
                "quality_score": 8.5
            },
            AgentPhase.ARCHITECTURE: {
                "architecture": {
                    "agents": ["TaskManager", "DataStore"],
                    "components": ["API", "Database"]
                },
                "quality_score": 8.0
            },
            AgentPhase.DESIGN: {
                "agents": [
                    {"name": "TaskAgent", "role": "task_management"}
                ],
                "tasks": [
                    {"name": "CreateTask", "agent": "TaskAgent"}
                ],
                "quality_score": 7.5
            },
            AgentPhase.DELIVERY: {
                "code_generated": True,
                "files": ["main.py", "agents.py"],
                "quality_score": 8.5
            }
        }

        if responses:
            default_responses.update(responses)

        async def mock_ainvoke(messages, temperature=None, max_tokens=None,
                               response_format=None, phase=None):
            """Simulate LLM call"""
            await asyncio.sleep(delay_ms / 1000)

            response_data = default_responses.get(phase, {"result": "success"})

            return {
                "content": json.dumps(response_data),
                "usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 50,
                    "total_tokens": 150
                },
                "model": model_name
            }

        llm = MagicMock()
        llm.model_name = model_name
        llm.model = model_name
        llm.ainvoke = AsyncMock(side_effect=mock_ainvoke)
        llm.generate = AsyncMock(return_value=default_responses[AgentPhase.DESIGN])

        return llm

    @staticmethod
    def create_validation_result(
        needs_fixing: bool = False,
        missing_items: Optional[List[str]] = None,
        issues: Optional[List[str]] = None
    ) -> MagicMock:
        """
        Create mock validation result.

        Args:
            needs_fixing: Whether validation failed
            missing_items: List of missing item names
            issues: List of issue descriptions

        Returns:
            Mock validation result
        """
        class MockMissingItem:
            def __init__(self, name: str):
                self.item_type = "feature"
                self.item_name = name
                self.severity = "high"
                self.description = f"Missing {name}"

        class MockGoldenResult:
            def __init__(self):
                self.missing_items = [
                    MockMissingItem(name) for name in (missing_items or [])
                ]
                self.extra_items = []
                self.mismatched_items = []

        result = MagicMock()
        result.needs_fixing = needs_fixing
        result.golden_result = MockGoldenResult() if needs_fixing else None
        result.issues = issues or []

        return result

    @staticmethod
    def create_agent_work_result(
        success: bool = True,
        output: Optional[Dict[str, Any]] = None,
        issues: Optional[List[str]] = None
    ) -> MagicMock:
        """
        Create mock agent work result.

        Args:
            success: Whether work succeeded
            output: Work output
            issues: List of issues

        Returns:
            Mock agent work result
        """
        result = MagicMock()
        result.success = success
        result.output = output or {"agents": [], "tasks": []}
        result.issues = issues or []
        result.duration = 1.5

        return result

    @staticmethod
    def create_collaboration_context(
        golden_data: Optional[ConcretizedRequirement] = None,
        requirement: str = "Build a test application"
    ) -> MagicMock:
        """
        Create mock collaboration context.

        Args:
            golden_data: Golden data (auto-created if None)
            requirement: User requirement

        Returns:
            Mock collaboration context
        """
        if golden_data is None:
            golden_data = MockFactory.create_golden_data()

        context = MagicMock()
        context.golden_data = golden_data
        context.requirement = requirement
        context.requirement_analysis = None
        context.architecture_design = None
        context.agent_task_design = None
        context.validation_results = {}
        context.agent_results = {}
        context.start_time = datetime.now()
        context.phases_completed = []
        context.feedback_loops_executed = 0

        return context


class LLMResponseBuilder:
    """
    Builder for creating LLM responses with fluent API.

    Usage:
        response = (LLMResponseBuilder()
            .with_agents([{"name": "TestAgent", "role": "testing"}])
            .with_tasks([{"name": "TestTask"}])
            .with_quality_score(8.5)
            .build())
    """

    def __init__(self):
        self._data = {}

    def with_agents(self, agents: List[Dict[str, Any]]) -> "LLMResponseBuilder":
        self._data["agents"] = agents
        return self

    def with_tasks(self, tasks: List[Dict[str, Any]]) -> "LLMResponseBuilder":
        self._data["tasks"] = tasks
        return self

    def with_quality_score(self, score: float) -> "LLMResponseBuilder":
        self._data["quality_score"] = score
        return self

    def with_field(self, key: str, value: Any) -> "LLMResponseBuilder":
        self._data[key] = value
        return self

    def build(self) -> Dict[str, Any]:
        return self._data.copy()


# Convenience functions
def golden_data(project_name: str = "Test Project", **kwargs) -> ConcretizedRequirement:
    """Shorthand for creating golden data"""
    return MockFactory.create_golden_data(project_name=project_name, **kwargs)


def llm_plugin(model_name: str = "mock-gpt-4", **kwargs) -> MagicMock:
    """Shorthand for creating LLM plugin"""
    return MockFactory.create_llm_plugin(model_name=model_name, **kwargs)


def validation_result(needs_fixing: bool = False, **kwargs) -> MagicMock:
    """Shorthand for creating validation result"""
    return MockFactory.create_validation_result(needs_fixing=needs_fixing, **kwargs)
