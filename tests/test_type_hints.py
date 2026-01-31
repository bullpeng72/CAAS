"""
Test Type Hints (Phase 1 - P1)

Verifies that:
1. Type helpers module provides useful type aliases
2. Type guards work correctly
3. Runtime type checking validates structures
4. Mypy configuration is correct
"""

import pytest
from caas_framework.utils.type_helpers import (
    AgentDict,
    TaskDict,
    DesignOutput,
    is_agent_dict,
    is_task_dict,
    validate_design_output,
    assert_agent_dict,
    assert_task_dict,
    PhaseStatus
)


def test_agent_dict_validation():
    """Test agent dictionary validation."""

    # Valid agent
    valid_agent: AgentDict = {
        "id": "researcher",
        "role": "Researcher",
        "goal": "Research topics",
        "backstory": "Expert researcher",
        "tools": ["web_search"],
        "verbose": True
    }

    assert is_agent_dict(valid_agent) is True

    # Invalid agent (missing required field)
    invalid_agent = {
        "id": "agent1",
        "role": "Agent"
        # Missing 'goal' and 'backstory'
    }

    assert is_agent_dict(invalid_agent) is False


def test_task_dict_validation():
    """Test task dictionary validation."""

    # Valid task
    valid_task: TaskDict = {
        "id": "task1",
        "description": "Research a topic",
        "expected_output": "Research report",
        "agent": "researcher"
    }

    assert is_task_dict(valid_task) is True

    # Invalid task (missing required field)
    invalid_task = {
        "id": "task1",
        "description": "Do something"
        # Missing 'expected_output' and 'agent'
    }

    assert is_task_dict(invalid_task) is False


def test_design_output_validation():
    """Test design output validation."""

    # Valid design output
    valid_design: DesignOutput = {
        "agents": [
            {
                "id": "agent1",
                "role": "Agent",
                "goal": "Goal",
                "backstory": "Story",
                "tools": []
            }
        ],
        "tasks": [
            {
                "id": "task1",
                "description": "Task",
                "expected_output": "Output",
                "agent": "agent1"
            }
        ]
    }

    assert validate_design_output(valid_design) is True

    # Invalid design (missing agents)
    invalid_design = {
        "tasks": []
    }

    assert validate_design_output(invalid_design) is False


def test_type_guards():
    """Test type guard functions."""

    valid_agent = {
        "id": "agent1",
        "role": "Role",
        "goal": "Goal",
        "backstory": "Story"
    }

    # Should not raise
    result = assert_agent_dict(valid_agent)
    assert result == valid_agent

    # Should raise TypeError
    with pytest.raises(TypeError):
        assert_agent_dict({"id": "incomplete"})


def test_phase_status_enum():
    """Test PhaseStatus enum."""
    assert PhaseStatus.PENDING.value == "pending"
    assert PhaseStatus.IN_PROGRESS.value == "in_progress"
    assert PhaseStatus.COMPLETED.value == "completed"
    assert PhaseStatus.FAILED.value == "failed"
    assert PhaseStatus.SKIPPED.value == "skipped"


def test_type_annotations_present():
    """Test that key modules have type annotations."""

    # Check collaboration module
    from caas_framework.agents.collaboration import SafeFeedbackLoop

    # Check if __init__ has return type annotation
    init_annotations = SafeFeedbackLoop.__init__.__annotations__
    assert 'return' in init_annotations
    assert init_annotations['return'] is None

    # Check plan_mode module
    from caas_framework.execution.plan_mode import PlanMode

    init_annotations = PlanMode.__init__.__annotations__
    assert 'return' in init_annotations
    assert init_annotations['return'] is None

    # Check auto_approve is annotated
    assert 'auto_approve' in init_annotations
    assert init_annotations['auto_approve'] == bool


def test_mypy_config_exists():
    """Test that mypy.ini configuration file exists."""
    import os

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    mypy_config = os.path.join(project_root, 'mypy.ini')

    assert os.path.exists(mypy_config), "mypy.ini should exist"

    # Check content
    with open(mypy_config) as f:
        content = f.read()

    assert '[mypy]' in content
    assert 'python_version' in content
    assert 'warn_return_any' in content


if __name__ == "__main__":
    test_agent_dict_validation()
    test_task_dict_validation()
    test_design_output_validation()
    test_type_guards()
    test_phase_status_enum()
    test_type_annotations_present()
    test_mypy_config_exists()

    print("\n" + "=" * 70)
    print("✅ All Type Hints tests passed!")
    print("=" * 70)
    print("\nSummary:")
    print("- Type Helpers: ✅ Provides useful type aliases and protocols")
    print("- Type Guards: ✅ Runtime validation works correctly")
    print("- Type Annotations: ✅ Key classes have proper annotations")
    print("- Mypy Config: ✅ Configuration file exists and is valid")
    print("- AgentDict/TaskDict: ✅ Validation functions work")
    print("- DesignOutput: ✅ Complex structure validation works")
    print("\n🎉 Phase 1 - Task #4 (P1) COMPLETE: Type hints added!")
