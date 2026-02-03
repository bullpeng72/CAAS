"""
Tool Utilities

Common utilities for generating tools.py files with fallback stub implementations.
This module centralizes tool generation logic to avoid code duplication.
"""

from typing import Dict, Set, Union

from caas_framework.utils.logger import get_logger

logger = get_logger()


def sanitize_tool_name(name: str) -> str:
    """
    Convert tool name to PascalCase class name.

    Args:
        name: Tool name (e.g., 'file_read', 'web_search')

    Returns:
        PascalCase class name (e.g., 'FileReadTool', 'WebSearchTool')

    Examples:
        >>> sanitize_tool_name('file_read')
        'FileReadTool'
        >>> sanitize_tool_name('web-search')
        'WebSearchTool'
        >>> sanitize_tool_name('calculator')
        'CalculatorTool'
    """
    # Remove special characters and split by underscore or hyphen
    parts = name.replace("-", "_").split("_")
    # Capitalize each part
    class_name = "".join(word.capitalize() for word in parts if word)
    # Ensure it ends with 'Tool'
    if not class_name.endswith("Tool"):
        class_name += "Tool"
    return class_name


def generate_fallback_tools_code(
    tools: Union[Set[str], Dict[str, str]],
    include_header: bool = True,
    fallback_warning: bool = False,
    include_helper_functions: bool = True,
    return_type: str = "str",  # "str" or "dict"
) -> str:
    """
    Generate fallback tools.py code with stub implementations.

    This function is the centralized implementation for generating tools.py
    when LLM generation fails or when generating tools via Expert Agents.

    This is the SINGLE SOURCE OF TRUTH for tools.py generation. Both code
    generation paths (Expert Agent Collaboration and Legacy LLM) converge here.

    Args:
        tools: Set of tool names or dict of {class_name: original_name}
               - If set: Will be sanitized internally
               - If dict: Already sanitized, keys are class names
        include_header: Whether to include module docstring (default: True)
        fallback_warning: Whether to add "LLM generation failed" warning (default: False)
        include_helper_functions: Whether to include get_all_tools() and instances (default: True)
        return_type: Return type for _run method - "str" or "dict" (default: "str")

    Returns:
        Python code string for tools.py with BaseTool implementations

    Examples:
        >>> # From set (will sanitize)
        >>> code = generate_fallback_tools_code({'file_read', 'web_search'})

        >>> # From dict (already sanitized)
        >>> code = generate_fallback_tools_code({'FileReadTool': 'file_read'})

        >>> # With fallback warning
        >>> code = generate_fallback_tools_code(
        ...     {'file_read'},
        ...     fallback_warning=True
        ... )

    Call Paths:
        This function is called by both code generation paths:

        Path 1 - Expert Agent Collaboration (DEFAULT, use_expert_agents=True):
            BMADEngine.run()
              → ExpertAgentCollaboration.collaborate()
              → CodeGeneratorAgent._do_work()
              → CodeGeneratorAgent._generate_tools_file_fallback()
              → generate_fallback_tools_code() ← HERE
            Configuration:
              - fallback_warning=False (no LLM failure message)
              - include_helper_functions=True (includes get_all_tools())
              - return_type="str" (string return from _run)
              - Output: files["tools.py"]

        Path 2 - Legacy LLM Generation (use_expert_agents=False):
            BMADEngine.run()
              → BMADEngine._phase_5_delivery()
              → CodeGenerationEngine.generate()
              → LLMCodeGenerator.generate_custom_tools()
              → LLMCodeGenerator._generate_fallback_tools()
              → generate_fallback_tools_code() ← HERE
            Configuration:
              - fallback_warning=True (shows LLM failure message)
              - include_helper_functions=False (no helpers)
              - return_type="dict" (dict return from _run)
              - Output: files["src/tools.py"]

    See Also:
        - sanitize_tool_name(): Converts tool names to PascalCase class names
        - extract_tool_names_from_agents(): Extracts tool names from agent specs
    """
    # Normalize input: convert set to dict if needed
    if isinstance(tools, set):
        logger.info(
            f"Generating tools.py with {len(tools)} tools: {', '.join(sorted(tools))}"
        )
        # Sanitize tool names
        sanitized_tools = {sanitize_tool_name(t): t for t in tools}
    else:
        # Already sanitized dict
        sanitized_tools = tools
        logger.info(f"Generating tools.py with {len(tools)} pre-sanitized tools")

    # Start building code
    code_parts = []

    # 1. Module docstring
    if include_header:
        if fallback_warning:
            header = '''"""
Custom Tools

CrewAI custom tool implementations.
⚠️  Generated using fallback (LLM generation failed)
"""'''
        else:
            header = '''"""
Custom Tools for CrewAI Agents

This file contains tool implementations for the multi-agent system.
Each tool provides specific capabilities to agents.
"""'''
        code_parts.append(header)

    # 2. Imports
    if return_type == "dict":
        imports = """
from crewai.tools import BaseTool
from typing import Any

logger = get_logger()
"""
    else:  # return_type == "str"
        imports = """
from crewai.tools import BaseTool
from typing import Type, Any, Optional
from pydantic import BaseModel, Field
from caas_framework.utils.logger import get_logger
"""
    code_parts.append(imports)

    # 3. Tool class definitions
    for class_name, original_name in sorted(sanitized_tools.items()):
        # Tool docstring
        if fallback_warning:
            tool_doc = f'''
class {class_name}(BaseTool):
    """
    {original_name} tool implementation.

    TODO: Implement the actual logic for this tool.
    This is a fallback stub generated when LLM generation failed.
    """'''
        else:
            tool_doc = f'''
class {class_name}(BaseTool):
    """
    {original_name.replace('_', ' ').title()} Tool

    Provides {original_name.replace('_', ' ')} capabilities to agents.
    """'''

        # Tool implementation
        if return_type == "dict":
            # Dictionary return style (LLMCodeGenerator)
            tool_impl = f'''
    name: str = "{original_name}"
    description: str = "Tool for {original_name} operations"

    def _run(self, input_data: str) -> Any:
        """Execute the tool."""
        logger.warning(f"{{self.name}} called but not fully implemented")

        # TODO: Implement actual tool logic here
        # Example:
        # - Parse input_data
        # - Execute the operation
        # - Return results

        return {{
            "status": "stub",
            "message": "This is a fallback implementation. Please implement the actual logic.",
            "input": input_data
        }}
'''
        else:  # return_type == "str"
            # String return style (CodeGeneratorAgent)
            tool_impl = f'''
    name: str = "{original_name}"
    description: str = "Tool for {original_name.replace('_', ' ')} operations"

    def _run(self, query: str) -> str:
        """
        Execute the tool.

        Args:
            query: Input query or parameters for the tool

        Returns:
            Result of the tool execution
        """
        # TODO: Implement actual {original_name} logic here
        # This is a stub implementation

        return f"{{self.name}} executed with query: {{query}}"
'''

        code_parts.append(tool_doc + tool_impl)

    # 4. Helper functions (optional)
    if include_helper_functions:
        # get_all_tools() function
        tool_classes = sorted(sanitized_tools.keys())
        tool_list_str = ",\n        ".join(f"{cls}()" for cls in tool_classes)

        helper_code = f'''
# Export all tools
def get_all_tools():
    """Get list of all available tool instances."""
    return [
        {tool_list_str}
    ]


# Individual tool instances for easy import
'''
        code_parts.append(helper_code)

        # Individual tool instances
        for class_name, original_name in sorted(sanitized_tools.items()):
            code_parts.append(f"{original_name} = {class_name}()\n")

    # Join all parts
    return "\n".join(code_parts)


def extract_tool_names_from_agents(agents: list) -> Set[str]:
    """
    Extract unique tool names from agent specifications.

    Args:
        agents: List of agent specifications (dicts or AgentSpecModel objects)

    Returns:
        Set of unique tool names used across all agents

    Examples:
        >>> agents = [
        ...     {'tools': ['file_read', 'file_write']},
        ...     {'tools': ['web_search', 'file_read']}
        ... ]
        >>> extract_tool_names_from_agents(agents)
        {'file_read', 'file_write', 'web_search'}
    """
    all_tools = set()

    for agent in agents:
        # Handle both dict and object (AgentSpecModel)
        if isinstance(agent, dict):
            tools = agent.get("tools", [])
        else:
            tools = getattr(agent, "tools", [])

        if tools:
            all_tools.update(tools)

    return all_tools
