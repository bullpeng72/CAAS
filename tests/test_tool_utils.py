"""
Unit tests for tool_utils module

Tests the centralized tool generation utilities to ensure consistency
across different code generation paths.
"""

from caas_framework.codegen.tool_utils import (
    extract_tool_names_from_agents,
    generate_fallback_tools_code,
    sanitize_tool_name,
)


class TestSanitizeToolName:
    """Test tool name sanitization"""

    def test_simple_name(self):
        """Test simple tool name"""
        assert sanitize_tool_name("calculator") == "CalculatorTool"

    def test_underscore_name(self):
        """Test tool name with underscores"""
        assert sanitize_tool_name("file_read") == "FileReadTool"
        assert sanitize_tool_name("web_search") == "WebSearchTool"

    def test_hyphen_name(self):
        """Test tool name with hyphens"""
        assert sanitize_tool_name("web-search") == "WebSearchTool"

    def test_already_ends_with_tool(self):
        """Test name that already ends with 'Tool'"""
        assert (
            sanitize_tool_name("FileReadTool") == "FilereadtoolTool"
        )  # Note: This might need fixing

    def test_empty_parts(self):
        """Test name with empty parts"""
        assert sanitize_tool_name("__test__") == "TestTool"


class TestGenerateFallbackToolsCode:
    """Test fallback tools code generation"""

    def test_from_set(self):
        """Test generation from set of tool names"""
        tools = {"file_read", "web_search"}
        code = generate_fallback_tools_code(tools)

        # Check that code is valid Python
        assert "from crewai.tools import BaseTool" in code
        assert "class FileReadTool(BaseTool)" in code
        assert "class WebSearchTool(BaseTool)" in code

        # Should be compilable
        compile(code, "<string>", "exec")

    def test_from_dict(self):
        """Test generation from dict (pre-sanitized)"""
        tools = {"FileReadTool": "file_read", "WebSearchTool": "web_search"}
        code = generate_fallback_tools_code(tools)

        assert "class FileReadTool(BaseTool)" in code
        assert "class WebSearchTool(BaseTool)" in code

        # Should be compilable
        compile(code, "<string>", "exec")

    def test_fallback_warning(self):
        """Test generation with fallback warning"""
        tools = {"file_read"}
        code = generate_fallback_tools_code(tools, fallback_warning=True)

        assert "⚠️  Generated using fallback (LLM generation failed)" in code

    def test_no_fallback_warning(self):
        """Test generation without fallback warning"""
        tools = {"file_read"}
        code = generate_fallback_tools_code(tools, fallback_warning=False)

        assert "⚠️" not in code
        assert "Custom Tools for CrewAI Agents" in code

    def test_return_type_str(self):
        """Test generation with string return type"""
        tools = {"file_read"}
        code = generate_fallback_tools_code(tools, return_type="str")

        assert "def _run(self, query: str) -> str:" in code
        assert 'return f"{self.name} executed with query: {query}"' in code

    def test_return_type_dict(self):
        """Test generation with dict return type"""
        tools = {"file_read"}
        code = generate_fallback_tools_code(tools, return_type="dict")

        assert "def _run(self, input_data: str) -> Any:" in code
        assert '"status": "stub"' in code

    def test_helper_functions_included(self):
        """Test generation with helper functions"""
        tools = {"file_read", "web_search"}
        code = generate_fallback_tools_code(tools, include_helper_functions=True)

        assert "def get_all_tools():" in code
        assert "file_read = FileReadTool()" in code
        assert "web_search = WebSearchTool()" in code

    def test_helper_functions_excluded(self):
        """Test generation without helper functions"""
        tools = {"file_read"}
        code = generate_fallback_tools_code(tools, include_helper_functions=False)

        assert "def get_all_tools():" not in code
        assert "file_read = FileReadTool()" not in code

    def test_no_header(self):
        """Test generation without header"""
        tools = {"file_read"}
        code = generate_fallback_tools_code(tools, include_header=False)

        # Should still have imports but no docstring
        assert "from crewai.tools import BaseTool" in code
        assert (
            '"""' not in code.split("from crewai.tools")[0]
        )  # No docstring before imports

    def test_empty_tools(self):
        """Test generation with empty tools"""
        tools = set()
        code = generate_fallback_tools_code(tools)

        # Should still have valid structure
        assert "from crewai.tools import BaseTool" in code
        compile(code, "<string>", "exec")

    def test_execution(self):
        """Test that generated code can be executed"""
        tools = {"file_read", "calculator"}
        code = generate_fallback_tools_code(tools, return_type="str")

        # Execute the generated code
        namespace = {}
        exec(code, namespace)

        # Check that classes were created
        assert "FileReadTool" in namespace
        assert "CalculatorTool" in namespace

        # Check that instances work
        file_read_tool = namespace["FileReadTool"]()
        result = file_read_tool._run("test query")
        assert "file_read" in result.lower()


class TestExtractToolNamesFromAgents:
    """Test tool name extraction from agent specifications"""

    def test_extract_from_dicts(self):
        """Test extraction from dict-based agent specs"""
        agents = [
            {"tools": ["file_read", "file_write"]},
            {"tools": ["web_search", "file_read"]},  # file_read duplicated
            {"tools": []},  # No tools
        ]

        tools = extract_tool_names_from_agents(agents)

        assert tools == {"file_read", "file_write", "web_search"}

    def test_extract_from_objects(self):
        """Test extraction from object-based agent specs"""
        from caas_framework.models.specifications import AgentSpecModel

        agents = [
            AgentSpecModel(
                id="agent1",
                role="Reader",
                goal="Read files",
                backstory="...",
                tools=["file_read", "file_write"],
            ),
            AgentSpecModel(
                id="agent2",
                role="Searcher",
                goal="Search web",
                backstory="...",
                tools=["web_search"],
            ),
        ]

        tools = extract_tool_names_from_agents(agents)

        assert tools == {"file_read", "file_write", "web_search"}

    def test_extract_from_mixed(self):
        """Test extraction from mixed dict/object specs"""
        from caas_framework.models.specifications import AgentSpecModel

        agents = [
            {"tools": ["file_read"]},
            AgentSpecModel(
                id="agent1",
                role="Searcher",
                goal="Search",
                backstory="...",
                tools=["web_search"],
            ),
        ]

        tools = extract_tool_names_from_agents(agents)

        assert tools == {"file_read", "web_search"}

    def test_extract_from_empty(self):
        """Test extraction from empty agent list"""
        agents = []
        tools = extract_tool_names_from_agents(agents)

        assert tools == set()

    def test_extract_with_no_tools(self):
        """Test extraction when agents have no tools"""
        agents = [
            {"tools": None},
            {"tools": []},
            {},  # No tools key
        ]

        tools = extract_tool_names_from_agents(agents)

        assert tools == set()


class TestConsistencyAcrossPaths:
    """Test consistency between different code generation paths"""

    def test_llm_vs_expert_agent_path(self):
        """
        Test that LLM path and Expert Agent path generate compatible code.

        This is a critical test to ensure both paths can work together.
        """
        tools = {"file_read", "web_search", "database"}

        # Simulate LLM path (dict input, dict return, no helpers)
        from caas_framework.codegen.tool_utils import sanitize_tool_name

        sanitized = {sanitize_tool_name(t): t for t in tools}

        code_llm_style = generate_fallback_tools_code(
            tools=sanitized,
            fallback_warning=True,
            include_helper_functions=False,
            return_type="dict",
        )

        # Simulate Expert Agent path (set input, str return, with helpers)
        code_expert_style = generate_fallback_tools_code(
            tools=tools,
            fallback_warning=False,
            include_helper_functions=True,
            return_type="str",
        )

        # Both should be valid Python
        compile(code_llm_style, "<string>", "exec")
        compile(code_expert_style, "<string>", "exec")

        # Both should define the same classes
        namespace_llm = {}
        namespace_expert = {}
        exec(code_llm_style, namespace_llm)
        exec(code_expert_style, namespace_expert)

        assert "FileReadTool" in namespace_llm
        assert "FileReadTool" in namespace_expert
        assert "WebSearchTool" in namespace_llm
        assert "WebSearchTool" in namespace_expert
        assert "DatabaseTool" in namespace_llm
        assert "DatabaseTool" in namespace_expert

        # Expert path should have helper functions, LLM path should not
        assert "get_all_tools" in namespace_expert
        assert "get_all_tools" not in namespace_llm

        # Expert path should have instances, LLM path should not
        assert "file_read" in namespace_expert
        assert "file_read" not in namespace_llm

    def test_class_interface_consistency(self):
        """
        Test that all generated classes have consistent interface.
        """
        tools = {"test_tool"}

        # Generate with different options
        code_dict_return = generate_fallback_tools_code(tools, return_type="dict")
        code_str_return = generate_fallback_tools_code(tools, return_type="str")

        # Execute both
        ns_dict = {}
        ns_str = {}
        exec(code_dict_return, ns_dict)
        exec(code_str_return, ns_str)

        # Both should have the same class (sanitize_tool_name converts "test_tool" to "TestTool")
        assert "TestTool" in ns_dict
        assert "TestTool" in ns_str

        # Both should be instantiable
        tool_dict = ns_dict["TestTool"]()
        tool_str = ns_str["TestTool"]()

        # Both should have _run method
        assert hasattr(tool_dict, "_run")
        assert hasattr(tool_str, "_run")

        # Both should have name and description
        assert tool_dict.name == "test_tool"
        assert tool_str.name == "test_tool"
        assert hasattr(tool_dict, "description")
        assert hasattr(tool_str, "description")
