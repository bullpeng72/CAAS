"""
Pytest Configuration and Shared Fixtures

✅ v0.5.1: Standardized fixtures using Factory pattern

Provides reusable fixtures for all tests:
- LLM mocks
- Golden Data
- Agents and Tasks
- Temporary directories
- Validation helpers
"""

import json
import pytest
import sys
from pathlib import Path
from typing import Dict, List
from unittest.mock import AsyncMock, MagicMock

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import factories
from tests.factories import (
    GoldenDataFactory,
    AgentFactory,
    TaskFactory,
    FileArtifactFactory,
)


# ==================== LLM Mocks ====================


@pytest.fixture
def mock_llm_plugin():
    """
    Mock LLM plugin for testing.

    Returns:
        MagicMock with ainvoke method
    """
    llm = MagicMock()
    llm.ainvoke = AsyncMock(return_value='{"result": "success"}')
    llm.invoke = MagicMock(return_value='{"result": "success"}')
    return llm


@pytest.fixture
def mock_llm_response():
    """
    Mock LLMResponse object.

    Returns:
        MockLLMResponse with content attribute
    """

    class MockLLMResponse:
        def __init__(self, content='{"status": "ok"}'):
            self.content = content

    return MockLLMResponse


# ==================== Golden Data Fixtures ====================


@pytest.fixture
def minimal_golden_data():
    """
    Minimal valid Golden Data (empty features).

    Returns:
        Dict ready for ConcretizedRequirement(**data)
    """
    return GoldenDataFactory.create_minimal()


@pytest.fixture
def sample_golden_data():
    """
    Sample Golden Data with 1 feature.

    ✅ v0.5.1: Returns ConcretizedRequirement object (not dict) for compatibility

    Returns:
        ConcretizedRequirement instance with system_scope and 1 test feature
    """
    from caas_framework.models.specifications import ConcretizedRequirement

    golden_dict = GoldenDataFactory.create(
        project_name="sample_app",
        purpose="Sample application for testing",
        features=[
            {
                "id": "feat_sample",
                "name": "Sample Feature",
                "description": "A sample feature for testing",
                "acceptance_criteria": ["Criterion 1", "Criterion 2"],
            }
        ],
    )
    return ConcretizedRequirement(**golden_dict)


@pytest.fixture
def todo_golden_data():
    """
    TODO app Golden Data.

    Returns:
        Dict for TODO application test scenario
    """
    return GoldenDataFactory.create(
        project_name="todo_app",
        purpose="Simple TODO application with task management",
        features=[
            {
                "id": "feat_add_task",
                "name": "Add Task",
                "description": "User can add new tasks",
                "acceptance_criteria": [
                    "Task input field exists",
                    "Add button works",
                    "Task is saved to database",
                ],
            },
            {
                "id": "feat_list_tasks",
                "name": "List Tasks",
                "description": "User can view all tasks",
                "acceptance_criteria": [
                    "Tasks are displayed in a list",
                    "Completed tasks are marked",
                ],
            },
        ],
    )


# ==================== Agent & Task Fixtures ====================


@pytest.fixture
def sample_agent():
    """
    Single sample agent.

    Returns:
        Dict ready for AgentSpecModel(**data)
    """
    return AgentFactory.create(
        agent_id="agent_sample",
        role="Sample Agent",
        goal="Perform sample tasks",
        backstory="A sample agent for testing",
        tools=["SampleTool"],
    )


@pytest.fixture
def sample_agents():
    """
    Multiple sample agents.

    Returns:
        List of 3 agent dicts
    """
    return AgentFactory.create_batch(3, prefix="agent")


@pytest.fixture
def sample_task():
    """
    Single sample task.

    Returns:
        Dict ready for TaskSpecModel(**data)
    """
    return TaskFactory.create(
        task_id="task_sample",
        description="Sample task",
        expected_output="Sample output",
        agent="agent_sample",
    )


@pytest.fixture
def sample_tasks():
    """
    Multiple sample tasks.

    Returns:
        List of 3 task dicts
    """
    return TaskFactory.create_batch(3, agent="agent_1", prefix="task")


# ==================== Backward Compatibility (legacy fixtures) ====================


@pytest.fixture
def sample_agent_dict(sample_agent):
    """Legacy: Use sample_agent instead"""
    return sample_agent


@pytest.fixture
def sample_task_dict(sample_task):
    """Legacy: Use sample_task instead"""
    return sample_task


@pytest.fixture
def sample_agents_list(sample_agents):
    """Legacy: Use sample_agents instead"""
    return sample_agents


@pytest.fixture
def sample_tasks_list(sample_tasks):
    """Legacy: Use sample_tasks instead"""
    return sample_tasks


# ==================== File Artifact Fixtures ====================


@pytest.fixture
def flat_code_artifacts():
    """
    Flat code artifact structure.

    Returns:
        Dict: {"main.py": "...", "agents.py": "..."}
    """
    return FileArtifactFactory.create_flat()


@pytest.fixture
def nested_code_artifacts():
    """
    Nested code artifact structure.

    Returns:
        Dict: {"files": {"main.py": "...", ...}}
    """
    return FileArtifactFactory.create_nested()


# ==================== Temporary Directory Fixtures ====================


@pytest.fixture
def project_dir(tmp_path):
    """
    Temporary project directory with standard structure.

    Creates:
        tmp_path/
        ├── input/
        ├── output/
        └── artifacts/

    Returns:
        Dict with paths
    """
    dirs = {
        "root": tmp_path,
        "input": tmp_path / "input",
        "output": tmp_path / "output",
        "artifacts": tmp_path / "artifacts",
    }

    for path in dirs.values():
        if path != tmp_path:
            path.mkdir(parents=True, exist_ok=True)

    return dirs


@pytest.fixture
def phase_input_dir(tmp_path, todo_golden_data, sample_agents, sample_tasks):
    """
    Phase input directory with golden_data.json, agents.json, tasks.json.

    Creates complete Phase 5 input directory.

    Returns:
        Path to input directory
    """
    input_dir = tmp_path / "phase_input"
    input_dir.mkdir()

    # golden_data.json
    with open(input_dir / "golden_data.json", "w") as f:
        json.dump(todo_golden_data, f, indent=2)

    # agents.json
    with open(input_dir / "agents.json", "w") as f:
        json.dump({"agents": sample_agents}, f, indent=2)

    # tasks.json
    with open(input_dir / "tasks.json", "w") as f:
        json.dump({"tasks": sample_tasks}, f, indent=2)

    return input_dir


# ==================== Validation Helpers ====================


@pytest.fixture
def validation_helper():
    """
    Helper class for validation assertions.

    Returns:
        ValidationHelper instance
    """

    class ValidationHelper:
        """Helper for common validation assertions"""

        @staticmethod
        def assert_valid_golden_data(data: Dict):
            """Assert Golden Data has required fields"""
            assert "system_scope" in data, "Missing system_scope"
            assert "project_name" in data["system_scope"], "Missing project_name"
            assert "purpose" in data["system_scope"], "Missing purpose"
            assert "features" in data, "Missing features"

        @staticmethod
        def assert_valid_agent(agent: Dict):
            """Assert Agent has required fields"""
            required = ["id", "role", "goal", "backstory"]
            for field in required:
                assert field in agent, f"Missing required field: {field}"

        @staticmethod
        def assert_valid_task(task: Dict):
            """Assert Task has required fields"""
            required = ["id", "description", "expected_output", "agent"]
            for field in required:
                assert field in task, f"Missing required field: {field}"

        @staticmethod
        def assert_file_exists(path: Path, message: str = None):
            """Assert file exists"""
            assert path.exists(), message or f"File not found: {path}"

        @staticmethod
        def assert_valid_python(code: str):
            """Assert Python code is syntactically valid"""
            try:
                compile(code, "<test>", "exec")
            except SyntaxError as e:
                pytest.fail(f"Invalid Python syntax: {e}")

    return ValidationHelper()


# ==================== Model Fixtures ====================


@pytest.fixture
def concretized_requirement(sample_golden_data):
    """
    ConcretizedRequirement model instance.

    Returns:
        ConcretizedRequirement with sample data
    """
    from caas_framework.models.specifications import ConcretizedRequirement

    return ConcretizedRequirement(**sample_golden_data)


@pytest.fixture
def agent_spec_model(sample_agent):
    """
    AgentSpecModel instance.

    Returns:
        AgentSpecModel with sample data
    """
    from caas_framework.models.specifications import AgentSpecModel

    return AgentSpecModel(**sample_agent)


@pytest.fixture
def task_spec_model(sample_task):
    """
    TaskSpecModel instance.

    Returns:
        TaskSpecModel with sample data
    """
    from caas_framework.models.specifications import TaskSpecModel

    return TaskSpecModel(**sample_task)


# ==================== Engine & Collaboration Fixtures ====================


@pytest.fixture
def six_phase_engine(mock_llm_plugin):
    """
    SixPhaseEngine instance with mocked LLM.

    Returns:
        SixPhaseEngine for testing
    """
    from caas_framework.methodology.engine import SixPhaseEngine

    return SixPhaseEngine(
        llm_plugin=mock_llm_plugin,
        enable_validation=False,  # Disable for faster tests
    )


@pytest.fixture
def expert_collaboration(mock_llm_plugin, concretized_requirement):
    """
    ExpertAgentCollaboration instance.

    Returns:
        ExpertAgentCollaboration for testing
    """
    from caas_framework.agents.collaboration import ExpertAgentCollaboration

    return ExpertAgentCollaboration(
        llm_plugin=mock_llm_plugin,
        golden_data=concretized_requirement,
        enable_validation=False,
        enable_frontend=False,
    )


# ==================== Pytest Configuration ====================


def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "e2e: marks tests as end-to-end tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )
