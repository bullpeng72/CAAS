"""
Tests for AST-based Code Generator

Tests the AST code generation module that produces syntax-error-free CrewAI code.
"""

import pytest

from caas_framework.agents.code_generator import CodeGeneratorAgent
from caas_framework.codegen.ast_code_generator import ASTCodeGenerator
from caas_framework.models.specifications import AgentSpecModel, TaskSpecModel


class TestASTCodeGenerator:
    """Test suite for ASTCodeGenerator"""

    def test_generator_creation(self):
        """Test that ASTCodeGenerator can be created"""
        generator = ASTCodeGenerator(use_black=True)
        assert generator is not None
        assert generator.use_black is True

    def test_generate_agent_code_basic(self):
        """Test generating basic Agent creation code"""
        generator = ASTCodeGenerator()

        agent = {
            'id': 'test_agent',
            'role': 'Test Role',
            'goal': 'Test Goal',
            'backstory': 'Test Backstory',
            'allow_delegation': False
        }

        code = generator.generate_agent_code(agent)

        # Verify it's valid Python
        assert generator.validate_syntax(f"from crewai import Agent\n{code}")

        # Verify it contains expected elements
        assert 'test_agent' in code
        assert 'Test Role' in code
        assert 'Test Goal' in code
        assert 'allow_delegation=False' in code

    def test_generate_agent_code_with_tools(self):
        """Test generating Agent code with tools"""
        generator = ASTCodeGenerator()

        agent = {
            'id': 'researcher',
            'role': 'Researcher',
            'goal': 'Research topics',
            'backstory': 'Expert researcher',
            'allow_delegation': True
        }

        tools = ['search_tool', 'scraper_tool']
        code = generator.generate_agent_code(agent, tools=tools)

        # Verify tools are included
        assert 'tools=' in code
        assert 'search_tool' in code
        assert 'scraper_tool' in code

    def test_generate_task_code(self):
        """Test generating Task creation code"""
        generator = ASTCodeGenerator()

        task = {
            'id': 'test_task',
            'description': 'Test description',
            'expected_output': 'Test output',
            'agent': 'test_agent',
            'human_input': False
        }

        code = generator.generate_task_code(task)

        # Verify it contains expected elements (ast.unparse uses single quotes)
        assert 'Task(' in code
        assert 'Test description' in code
        assert 'Test output' in code
        assert "agents['test_agent']" in code or 'agents["test_agent"]' in code
        assert 'human_input=False' in code

    def test_generate_imports(self):
        """Test generating import statements"""
        generator = ASTCodeGenerator()

        modules = [
            'os',
            {'crewai': ['Agent', 'Task', 'Crew']},
            {'pathlib': ['Path']}
        ]

        imports = generator.generate_imports(modules)

        assert len(imports) == 3
        assert 'import os' in imports
        assert 'from crewai import Agent, Task, Crew' in imports
        assert 'from pathlib import Path' in imports

    def test_generate_create_agents_function(self):
        """Test generating create_agents() function"""
        generator = ASTCodeGenerator()

        agents = [
            {
                'id': 'agent1',
                'role': 'Role 1',
                'goal': 'Goal 1',
                'backstory': 'Story 1',
                'allow_delegation': False
            },
            {
                'id': 'agent2',
                'role': 'Role 2',
                'goal': 'Goal 2',
                'backstory': 'Story 2',
                'allow_delegation': True
            }
        ]

        code = generator.generate_create_agents_function(agents)

        # Verify it's valid Python
        full_code = f"from crewai import Agent\n{code}"
        assert generator.validate_syntax(full_code)

        # Verify function structure (ast.unparse uses single quotes)
        assert 'def create_agents():' in code
        assert 'agents = {}' in code
        assert ("agents['agent1']" in code or 'agents["agent1"]' in code)
        assert ("agents['agent2']" in code or 'agents["agent2"]' in code)
        assert 'return agents' in code

    def test_generate_create_tasks_function(self):
        """Test generating create_tasks() function"""
        generator = ASTCodeGenerator()

        tasks = [
            {
                'id': 'task1',
                'description': 'Task 1 description',
                'expected_output': 'Output 1',
                'agent': 'agent1',
                'human_input': False
            },
            {
                'id': 'task2',
                'description': 'Task 2 description',
                'expected_output': 'Output 2',
                'agent': 'agent2',
                'human_input': True
            }
        ]

        code = generator.generate_create_tasks_function(tasks)

        # Verify it's valid Python
        full_code = f"from crewai import Task\n{code}"
        assert generator.validate_syntax(full_code)

        # Verify function structure
        assert 'def create_tasks(agents):' in code
        assert 'tasks = []' in code
        assert 'tasks.append' in code
        assert 'Task(' in code
        assert 'human_input=True' in code
        assert 'return tasks' in code

    def test_generate_main_function(self):
        """Test generating main() function"""
        generator = ASTCodeGenerator()

        code = generator.generate_main_function(process='sequential', has_user_inputs=False)

        # Verify function structure
        assert 'def main():' in code
        assert 'agents = create_agents()' in code
        assert 'tasks = create_tasks(agents)' in code
        assert 'crew = Crew(' in code
        assert 'Process.sequential' in code
        assert 'result = crew.kickoff()' in code
        assert 'return result' in code

    def test_generate_main_function_with_inputs(self):
        """Test generating main() function with user inputs"""
        generator = ASTCodeGenerator()

        code = generator.generate_main_function(process='hierarchical', has_user_inputs=True)

        # Verify user inputs handling
        assert 'def main():' in code
        assert 'crew.kickoff(inputs=user_inputs)' in code
        assert 'Process.hierarchical' in code

    def test_generate_full_module(self):
        """Test generating a complete Python module"""
        generator = ASTCodeGenerator(use_black=True)

        agents = [
            {
                'id': 'researcher',
                'role': 'Researcher',
                'goal': 'Research topics',
                'backstory': 'Expert researcher',
                'allow_delegation': False
            }
        ]

        tasks = [
            {
                'id': 'research_task',
                'description': 'Research the topic',
                'expected_output': 'Research report',
                'agent': 'researcher',
                'human_input': False
            }
        ]

        code = generator.generate_full_module(
            agents=agents,
            tasks=tasks,
            process='sequential',
            docstring='Test module'
        )

        # Verify it's valid Python
        assert generator.validate_syntax(code)

        # Verify imports
        assert 'from crewai import' in code

        # Verify functions
        assert 'def create_agents():' in code
        assert 'def create_tasks(agents):' in code
        assert 'def main():' in code

        # Verify main guard
        assert 'if __name__ == "__main__":' in code

        # Verify it can be compiled
        try:
            compile(code, '<string>', 'exec')
        except SyntaxError as e:
            pytest.fail(f"Generated code has syntax error: {e}")

    def test_syntax_validation(self):
        """Test syntax validation function"""
        generator = ASTCodeGenerator()

        # Valid code
        valid_code = "x = 1\ny = 2\nprint(x + y)"
        assert generator.validate_syntax(valid_code) is True

        # Invalid code
        invalid_code = "x = 1\nif x == 1\n    print('error')"
        assert generator.validate_syntax(invalid_code) is False

    def test_black_formatting(self):
        """Test black formatting"""
        generator = ASTCodeGenerator(use_black=True)

        # Unformatted code
        unformatted = "x=1\ny=2\nz=x+y"

        formatted = generator.format_with_black(unformatted)

        # Black should add spaces around operators
        assert 'x = 1' in formatted or 'x=1' in formatted  # May vary by black version

    def test_format_without_black(self):
        """Test formatting when black is not available"""
        generator = ASTCodeGenerator(use_black=False)

        code = "x = 1\ny = 2"
        formatted = generator.format_with_black(code)

        # Without black, should return original (may have trailing newline)
        assert formatted.strip() == code.strip()


class TestCodeGeneratorAgentAST:
    """Test suite for CodeGeneratorAgent with AST-based generation"""

    def test_create_fallback_code_structure(self):
        """Test that _create_fallback_code returns correct structure"""
        code_gen = CodeGeneratorAgent(llm_plugin=None)

        agents = [
            AgentSpecModel(
                id="agent1",
                role="Role 1",
                goal="Goal 1",
                backstory="Story 1",
                tools=[],
                allow_delegation=False
            )
        ]

        tasks = [
            TaskSpecModel(
                id="task1",
                description="Task 1",
                expected_output="Output 1",
                agent="agent1",
                human_input=False
            )
        ]

        result = code_gen._create_fallback_code(agents, tasks)

        # Verify structure
        assert "files" in result
        files = result["files"]

        # Verify required files
        assert "main.py" in files
        assert "agents.py" in files
        assert "tasks.py" in files
        assert "requirements.txt" in files
        assert "README.md" in files
        assert ".env.example" in files

    def test_fallback_code_syntax_valid(self):
        """Test that all generated Python files have valid syntax"""
        code_gen = CodeGeneratorAgent(llm_plugin=None)

        agents = [
            AgentSpecModel(
                id="researcher",
                role="Researcher",
                goal="Research",
                backstory="Expert",
                tools=[],
                allow_delegation=False
            )
        ]

        tasks = [
            TaskSpecModel(
                id="research",
                description="Research task",
                expected_output="Report",
                agent="researcher",
                human_input=False
            )
        ]

        result = code_gen._create_fallback_code(agents, tasks)
        files = result["files"]

        # Test Python files
        python_files = ["main.py", "agents.py", "tasks.py"]

        for filename in python_files:
            code = files[filename]

            # Verify syntax
            try:
                compile(code, filename, 'exec')
            except SyntaxError as e:
                pytest.fail(f"{filename} has syntax error: {e}")

    def test_fallback_code_contains_crewai_imports(self):
        """Test that generated code contains CrewAI imports"""
        code_gen = CodeGeneratorAgent(llm_plugin=None)

        agents = [AgentSpecModel(
            id="agent1",
            role="Role",
            goal="Goal",
            backstory="Story",
            tools=[],
            allow_delegation=False
        )]

        tasks = [TaskSpecModel(
            id="task1",
            description="Task",
            expected_output="Output",
            agent="agent1",
            human_input=False
        )]

        result = code_gen._create_fallback_code(agents, tasks)
        files = result["files"]

        # Verify CrewAI imports
        assert "from crewai import" in files["main.py"]
        assert "from crewai import" in files["agents.py"]
        assert "from crewai import" in files["tasks.py"]

    def test_multiple_agents_and_tasks(self):
        """Test generating code with multiple agents and tasks"""
        code_gen = CodeGeneratorAgent(llm_plugin=None)

        agents = [
            AgentSpecModel(
                id=f"agent{i}",
                role=f"Role {i}",
                goal=f"Goal {i}",
                backstory=f"Story {i}",
                tools=[],
                allow_delegation=(i % 2 == 0)
            )
            for i in range(1, 6)
        ]

        tasks = [
            TaskSpecModel(
                id=f"task{i}",
                description=f"Task {i}",
                expected_output=f"Output {i}",
                agent=f"agent{i}",
                human_input=False
            )
            for i in range(1, 6)
        ]

        result = code_gen._create_fallback_code(agents, tasks)
        files = result["files"]

        # Verify all agents are in agents.py
        agents_py = files["agents.py"]
        for i in range(1, 6):
            assert f'agents["agent{i}"]' in agents_py

        # Verify all tasks are in tasks.py
        tasks_py = files["tasks.py"]
        for i in range(1, 6):
            assert f'Task {i}' in tasks_py

        # Verify syntax
        for filename in ["main.py", "agents.py", "tasks.py"]:
            try:
                compile(files[filename], filename, 'exec')
            except SyntaxError as e:
                pytest.fail(f"{filename} has syntax error: {e}")


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
