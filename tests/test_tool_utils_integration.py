"""
Integration tests for tool_utils refactoring

Verifies that the refactored code works correctly with the actual
LLMCodeGenerator and CodeGeneratorAgent classes.
"""

from unittest.mock import AsyncMock, Mock

import pytest

from caas_framework.agents.code_generator import CodeGeneratorAgent
from caas_framework.codegen.llm_code_generator import LLMCodeGenerator


class TestLLMCodeGeneratorIntegration:
    """Test LLMCodeGenerator with refactored tool generation"""

    @pytest.fixture
    def llm_plugin(self):
        """Mock LLM plugin"""
        mock = Mock()
        mock.ainvoke = AsyncMock()
        return mock

    def test_generate_fallback_tools_integration(self, llm_plugin):
        """Test that LLMCodeGenerator._generate_fallback_tools() works after refactoring"""
        generator = LLMCodeGenerator(llm_plugin)

        # Simulate sanitized tools (what generate_custom_tools would create)
        sanitized_tools = {
            "FileReadTool": "file_read",
            "WebSearchTool": "web_search",
            "DatabaseTool": "database"
        }

        # Call the refactored method
        code = generator._generate_fallback_tools(sanitized_tools)

        # Verify code structure
        assert "from crewai.tools import BaseTool" in code
        assert "class FileReadTool(BaseTool)" in code
        assert "class WebSearchTool(BaseTool)" in code
        assert "class DatabaseTool(BaseTool)" in code

        # Verify fallback warning is present (LLM path characteristic)
        assert "⚠️  Generated using fallback (LLM generation failed)" in code

        # Verify dict return type (LLM path characteristic)
        assert "def _run(self, input_data: str) -> Any:" in code
        assert '"status": "stub"' in code

        # Verify NO helper functions (LLM path doesn't include them)
        assert "def get_all_tools():" not in code
        assert "file_read = FileReadTool()" not in code

        # Verify it's valid Python
        compile(code, "<string>", "exec")

        # Verify it can be executed
        namespace = {}
        exec(code, namespace)
        assert "FileReadTool" in namespace
        assert "WebSearchTool" in namespace
        assert "DatabaseTool" in namespace


class TestCodeGeneratorAgentIntegration:
    """Test CodeGeneratorAgent with refactored tool generation"""

    @pytest.fixture
    def llm_plugin(self):
        """Mock LLM plugin"""
        mock = Mock()
        mock.ainvoke = AsyncMock()
        return mock

    @pytest.fixture
    def golden_data(self):
        """Mock golden data"""
        from caas_framework.models.specifications import ConcretizedRequirement
        return ConcretizedRequirement(
            project_name="Test Project",
            features=[]
        )

    def test_generate_tools_file_fallback_integration(self, llm_plugin, golden_data):
        """Test that CodeGeneratorAgent._generate_tools_file_fallback() works after refactoring"""
        agent = CodeGeneratorAgent(llm_plugin, golden_data)

        # Simulate tools extracted from agents
        tools = {"file_read", "web_search", "database"}

        # Call the refactored method
        code = agent._generate_tools_file_fallback(tools)

        # Verify code structure
        assert "from crewai.tools import BaseTool" in code
        assert "class FileReadTool(BaseTool)" in code
        assert "class WebSearchTool(BaseTool)" in code
        assert "class DatabaseTool(BaseTool)" in code

        # Verify NO fallback warning (Expert Agent path characteristic)
        assert "⚠️" not in code
        assert "Custom Tools for CrewAI Agents" in code

        # Verify string return type (Expert Agent path characteristic)
        assert "def _run(self, query: str) -> str:" in code
        assert 'return f"{self.name} executed with query: {query}"' in code

        # Verify helper functions ARE included (Expert Agent path includes them)
        assert "def get_all_tools():" in code
        assert "file_read = FileReadTool()" in code
        assert "web_search = WebSearchTool()" in code
        assert "database = DatabaseTool()" in code

        # Verify it's valid Python
        compile(code, "<string>", "exec")

        # Verify it can be executed
        namespace = {}
        exec(code, namespace)
        assert "FileReadTool" in namespace
        assert "WebSearchTool" in namespace
        assert "DatabaseTool" in namespace
        assert "file_read" in namespace  # Instance
        assert "web_search" in namespace  # Instance
        assert "database" in namespace  # Instance
        assert "get_all_tools" in namespace  # Helper function


class TestCrossPathConsistency:
    """Test that both paths generate compatible code"""

    @pytest.fixture
    def llm_plugin(self):
        """Mock LLM plugin"""
        mock = Mock()
        mock.ainvoke = AsyncMock()
        return mock

    @pytest.fixture
    def golden_data(self):
        """Mock golden data"""
        from caas_framework.models.specifications import ConcretizedRequirement
        return ConcretizedRequirement(
            project_name="Test Project",
            features=[]
        )

    def test_both_paths_generate_compatible_classes(self, llm_plugin, golden_data):
        """
        Critical test: Ensure both paths generate classes with compatible interfaces.

        This is important because:
        1. Different execution paths may be used for different projects
        2. Code generated by one path should be understandable by developers
           familiar with the other path
        3. BaseTool interface must be consistent
        """
        tools = {"file_read", "web_search"}

        # Path 1: LLM Code Generator
        llm_gen = LLMCodeGenerator(llm_plugin)
        from caas_framework.codegen.tool_utils import sanitize_tool_name
        sanitized = {sanitize_tool_name(t): t for t in tools}
        code_llm = llm_gen._generate_fallback_tools(sanitized)

        # Path 2: Expert Agent
        code_gen = CodeGeneratorAgent(llm_plugin, golden_data)
        code_expert = code_gen._generate_tools_file_fallback(tools)

        # Execute both
        ns_llm = {}
        ns_expert = {}
        exec(code_llm, ns_llm)
        exec(code_expert, ns_expert)

        # Both should have the same tool classes
        assert "FileReadTool" in ns_llm
        assert "FileReadTool" in ns_expert
        assert "WebSearchTool" in ns_llm
        assert "WebSearchTool" in ns_expert

        # Both classes should be instantiable
        file_read_llm = ns_llm["FileReadTool"]()
        file_read_expert = ns_expert["FileReadTool"]()

        # Both should have the same tool name
        assert file_read_llm.name == "file_read"
        assert file_read_expert.name == "file_read"

        # Both should have BaseTool interface
        assert hasattr(file_read_llm, "_run")
        assert hasattr(file_read_expert, "_run")
        assert hasattr(file_read_llm, "name")
        assert hasattr(file_read_expert, "name")
        assert hasattr(file_read_llm, "description")
        assert hasattr(file_read_expert, "description")

        # Return types differ, but both should return something
        result_llm = file_read_llm._run("test")
        result_expert = file_read_expert._run("test")

        assert result_llm is not None
        assert result_expert is not None

        # LLM returns dict, Expert returns str
        assert isinstance(result_llm, dict)
        assert isinstance(result_expert, str)
