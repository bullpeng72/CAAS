"""
Tests for CodeGeneratorAgent auto-fix functionality.

Validates that common LLM-generated code bugs are automatically fixed.
"""

import pytest
from unittest.mock import Mock
from caas_framework.agents.code_generator import CodeGeneratorAgent


class TestCodeGeneratorAutoFix:
    """Test auto-fix functionality for LLM-generated code."""

    def setup_method(self):
        """Create CodeGeneratorAgent instance for testing."""
        # Create a mock LLM plugin (not needed for auto-fix tests)
        mock_llm_plugin = Mock()
        self.agent = CodeGeneratorAgent(
            llm_plugin=mock_llm_plugin,
            golden_data=None
        )

    def test_fix_agent_id_parameter(self):
        """Test that id='...' parameter is removed from Agent() calls."""
        buggy_code = """from crewai import Agent

task_manager_agent = Agent(
    id='task_manager_agent',
    role='Task Manager',
    goal='Manage tasks',
    backstory='Expert',
    verbose=True
)"""

        files = {"agents.py": buggy_code}
        fixed_files = self.agent._autofix_generated_code(files, [])

        fixed_code = fixed_files["agents.py"]

        # id parameter should be removed
        assert "id=" not in fixed_code
        assert "task_manager_agent" not in fixed_code or "Agent(" in fixed_code
        # Other parameters should remain
        assert "role='Task Manager'" in fixed_code
        assert "goal='Manage tasks'" in fixed_code

    def test_fix_string_tools_list(self):
        """Test that tools=['str'] is converted to tools=[]."""
        buggy_code = """from crewai import Agent

agent = Agent(
    role='Agent',
    goal='Work',
    backstory='Expert',
    tools=['file_read', 'file_write'],
    verbose=True
)"""

        files = {"agents.py": buggy_code}
        fixed_files = self.agent._autofix_generated_code(files, [])

        fixed_code = fixed_files["agents.py"]

        # String list should be converted to empty list
        assert "tools=[]" in fixed_code
        assert "'file_read'" not in fixed_code or "from tools import" in fixed_code

    def test_preserve_variable_tools_list(self):
        """Test that tools=[FileReadTool, FileWriteTool] is preserved."""
        good_code = """from crewai import Agent
from tools import FileReadTool, FileWriteTool

agent = Agent(
    role='Agent',
    goal='Work',
    backstory='Expert',
    tools=[FileReadTool, FileWriteTool],
    verbose=True
)"""

        files = {"agents.py": good_code}
        fixed_files = self.agent._autofix_generated_code(files, [])

        fixed_code = fixed_files["agents.py"]

        # Variable list should be preserved
        assert "tools=[FileReadTool, FileWriteTool]" in fixed_code or "tools=[]" not in fixed_code

    def test_remove_unsupported_parameters(self):
        """Test that unsupported parameters (memory, max_iter) are removed."""
        buggy_code = """from crewai import Agent

agent = Agent(
    role='Agent',
    goal='Work',
    backstory='Expert',
    tools=[],
    verbose=True,
    memory=True,
    max_iter=15,
    allow_delegation=False
)"""

        files = {"agents.py": buggy_code}
        fixed_files = self.agent._autofix_generated_code(files, [])

        fixed_code = fixed_files["agents.py"]

        # Unsupported parameters should be removed
        assert "memory=" not in fixed_code
        assert "max_iter=" not in fixed_code
        # Supported parameters should remain
        assert "allow_delegation=False" in fixed_code
        assert "verbose=True" in fixed_code

    def test_generate_missing_tools_py(self):
        """Test that tools.py is generated when missing but agents have tools."""
        agents_code = """from crewai import Agent

agent = Agent(
    role='Agent',
    goal='Work with files',
    backstory='Expert',
    tools=[],
    verbose=True
)"""

        # Agent spec with tools
        agents = [
            {
                "id": "file_agent",
                "role": "File Agent",
                "goal": "Manage files",
                "backstory": "Expert",
                "tools": ["file_read", "file_write"]
            }
        ]

        files = {"agents.py": agents_code}
        fixed_files = self.agent._autofix_generated_code(files, agents)

        # tools.py should be generated
        assert "tools.py" in fixed_files
        assert "FileReadTool" in fixed_files["tools.py"]
        assert "FileWriteTool" in fixed_files["tools.py"]

        # tools import should be added to agents.py
        fixed_agents = fixed_files["agents.py"]
        assert "from tools import" in fixed_agents
        assert "file_read" in fixed_agents or "file_write" in fixed_agents

    def test_no_changes_for_correct_code(self):
        """Test that correct code is not modified."""
        correct_code = """from crewai import Agent

def create_agents():
    agents = {}

    agents['manager'] = Agent(
        role='Manager',
        goal='Coordinate tasks',
        backstory='Expert coordinator',
        verbose=True,
        allow_delegation=True
    )

    return agents
"""

        files = {"agents.py": correct_code}
        fixed_files = self.agent._autofix_generated_code(files, [])

        # Code should remain unchanged (modulo whitespace)
        assert "role='Manager'" in fixed_files["agents.py"]
        assert "id=" not in fixed_files["agents.py"]
        assert "Agent(" in fixed_files["agents.py"]

    def test_comprehensive_fix(self):
        """Test fixing multiple issues in one file."""
        buggy_code = """from crewai import Agent

task_manager_agent = Agent(
    id='task_manager_agent',
    role='Task Manager',
    goal='Manage tasks',
    backstory='Expert task manager',
    tools=['file_read', 'file_write'],
    verbose=True,
    memory=True,
    allow_delegation=True,
    max_iter=15
)"""

        agents = [
            {
                "id": "task_manager_agent",
                "role": "Task Manager",
                "goal": "Manage tasks",
                "backstory": "Expert",
                "tools": ["file_read", "file_write"]
            }
        ]

        files = {"agents.py": buggy_code}
        fixed_files = self.agent._autofix_generated_code(files, agents)

        fixed_code = fixed_files["agents.py"]

        # All issues should be fixed
        assert "id=" not in fixed_code
        assert "memory=" not in fixed_code
        assert "max_iter=" not in fixed_code
        assert "tools=[]" in fixed_code or "tools=[" not in fixed_code

        # Supported parameters should remain
        assert "role='Task Manager'" in fixed_code
        assert "verbose=True" in fixed_code
        assert "allow_delegation=True" in fixed_code

        # tools.py should be generated
        assert "tools.py" in fixed_files
        assert "from tools import" in fixed_code


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
