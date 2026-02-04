"""
Pytest configuration and shared fixtures for CAAS tests.
"""

import pytest
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def sample_agent_dict():
    """Sample agent as dictionary."""
    return {
        "id": "analyst_1",
        "role": "Data Analyst",
        "goal": "Analyze data and generate insights",
        "backstory": "Expert in data analysis",
        "tools": ["python", "pandas"],
    }


@pytest.fixture
def sample_task_dict():
    """Sample task as dictionary."""
    return {
        "id": "task_1",
        "description": "Analyze sales data",
        "expected_output": "Sales analysis report",
        "assigned_agent": "analyst_1",
        "agent": "analyst_1",
    }


@pytest.fixture
def sample_agents_list():
    """List of sample agents."""
    return [
        {
            "id": "analyst_1",
            "role": "Data Analyst",
            "goal": "Analyze data",
            "tools": ["python"],
        },
        {
            "id": "researcher_1",
            "role": "Researcher",
            "goal": "Research topics",
            "tools": ["web_search"],
        },
    ]


@pytest.fixture
def sample_tasks_list():
    """List of sample tasks."""
    return [
        {
            "id": "task_1",
            "description": "Analyze data",
            "assigned_agent": "analyst_1",
        },
        {
            "id": "task_2",
            "description": "Research topic",
            "agent": "researcher_1",
        },
    ]
