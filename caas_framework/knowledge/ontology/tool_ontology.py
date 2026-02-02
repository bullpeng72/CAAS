"""
Tool Ontology Model

Manages the ontology of available tools, including conceptual tools
and their CrewAI implementations.
"""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class ToolType(str, Enum):
    """Tool type classification"""

    BUILT_IN = "built_in"  # CrewAI built-in tools
    CUSTOM = "custom"  # User-defined custom tools
    MCP = "mcp"  # Model Context Protocol tools


class ToolCategory(str, Enum):
    """Tool category for organization"""

    FILE = "file"
    SEARCH = "search"
    DOCUMENT = "document"
    CODE = "code"
    DATABASE = "database"
    WEB_SCRAPING = "web_scraping"
    VISION = "vision"
    YOUTUBE = "youtube"
    COMMUNICATION = "communication"
    AI = "ai"
    OTHER = "other"


class ToolImplementation(BaseModel):
    """
    A specific implementation of a conceptual tool

    Example: "web_search" can be implemented by SerperDevTool, BraveSearchTool, etc.
    """

    crewai_class: str = Field(..., description="CrewAI tool class name (e.g., 'SerperDevTool')")
    name: str = Field(..., description="Human-readable name (e.g., 'Google Search via Serper')")
    description: str = Field(default="", description="Detailed description of this implementation")
    requires_api_key: bool = Field(
        default=False, description="Whether this implementation requires an API key"
    )
    api_key_env: Optional[str] = Field(
        default=None, description="Environment variable name for API key (e.g., 'SERPER_API_KEY')"
    )
    pros: List[str] = Field(default_factory=list, description="Advantages of this implementation")
    cons: List[str] = Field(default_factory=list, description="Disadvantages or limitations")


class ConceptualTool(BaseModel):
    """
    A conceptual tool representing a capability/function

    A conceptual tool can have multiple implementations.
    Example: "web_search" is a concept that can be implemented by
    SerperDevTool, BraveSearchTool, TavilySearchTool, etc.
    """

    id: str = Field(..., description="Unique tool ID (e.g., 'tool_web_search')")
    name: str = Field(..., description="Conceptual tool name (e.g., 'web_search')")
    display_name: str = Field(..., description="Display name (e.g., 'Web Search')")
    category: ToolCategory = Field(..., description="Tool category")
    type: ToolType = Field(default=ToolType.BUILT_IN, description="Tool type")

    description: str = Field(..., description="Description of what this tool does")
    use_cases: List[str] = Field(default_factory=list, description="Common use cases for this tool")

    # Multiple implementations
    implementations: List[ToolImplementation] = Field(
        default_factory=list, description="Available implementations of this conceptual tool"
    )
    default_implementation: Optional[str] = Field(
        default=None,
        description="Default CrewAI class to use (should match one in implementations)",
    )

    # Compatibility
    compatible_roles: List[str] = Field(
        default_factory=list, description="Agent roles that commonly use this tool"
    )
    compatible_tasks: List[str] = Field(
        default_factory=list, description="Task types that commonly use this tool"
    )

    # Usage statistics
    usage_count: int = Field(default=0, description="Number of times used")
    success_rate: float = Field(default=0.0, description="Success rate (0.0-1.0)")

    # Metadata
    tags: List[str] = Field(default_factory=list, description="Tags for search")
    enabled: bool = Field(default=True, description="Whether this tool is enabled")

    def get_implementation(
        self, crewai_class: Optional[str] = None
    ) -> Optional[ToolImplementation]:
        """
        Get a specific implementation or the default one

        Args:
            crewai_class: Specific CrewAI class to get, or None for default

        Returns:
            ToolImplementation or None if not found
        """
        if not self.implementations:
            return None

        if crewai_class:
            for impl in self.implementations:
                if impl.crewai_class == crewai_class:
                    return impl
            return None

        # Return default implementation
        if self.default_implementation:
            for impl in self.implementations:
                if impl.crewai_class == self.default_implementation:
                    return impl

        # Fallback to first implementation
        return self.implementations[0] if self.implementations else None

    def get_crewai_class(self, preferred: Optional[str] = None) -> Optional[str]:
        """
        Get the CrewAI class name to use

        Args:
            preferred: Preferred CrewAI class, or None for default

        Returns:
            CrewAI class name or None
        """
        impl = self.get_implementation(preferred)
        return impl.crewai_class if impl else None


class ToolOntology(BaseModel):
    """
    Collection of conceptual tools
    """

    version: str = Field(default="1.0.0", description="Ontology version")
    tools: List[ConceptualTool] = Field(
        default_factory=list, description="List of conceptual tools"
    )

    def get_tool(self, name: str) -> Optional[ConceptualTool]:
        """Get tool by name"""
        for tool in self.tools:
            if tool.name == name:
                return tool
        return None

    def get_tool_by_id(self, tool_id: str) -> Optional[ConceptualTool]:
        """Get tool by ID"""
        for tool in self.tools:
            if tool.id == tool_id:
                return tool
        return None

    def get_tools_by_category(self, category: ToolCategory) -> List[ConceptualTool]:
        """Get all tools in a category"""
        return [tool for tool in self.tools if tool.category == category]

    def get_enabled_tools(self) -> List[ConceptualTool]:
        """Get all enabled tools"""
        return [tool for tool in self.tools if tool.enabled]

    def search_tools(self, query: str) -> List[ConceptualTool]:
        """Search tools by name, description, or tags"""
        query_lower = query.lower()
        results = []

        for tool in self.tools:
            if (
                query_lower in tool.name.lower()
                or query_lower in tool.display_name.lower()
                or query_lower in tool.description.lower()
                or any(query_lower in tag.lower() for tag in tool.tags)
            ):
                results.append(tool)

        return results
