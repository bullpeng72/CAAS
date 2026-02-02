"""
Tool Ontology Manager

Manages loading, saving, and querying the tool ontology.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from caas_framework.knowledge.ontology.tool_data_generator import generate_initial_ontology
from caas_framework.knowledge.ontology.tool_ontology import (
    ConceptualTool,
    ToolCategory,
    ToolOntology,
)
from caas_framework.utils.logger import get_logger

logger = get_logger("ontology.tool_manager")


class ToolOntologyManager:
    """Manages the tool ontology"""

    def __init__(self, ontology_file: Optional[Path] = None):
        """
        Initialize the tool ontology manager

        Args:
            ontology_file: Path to the ontology JSON file.
                          If None, uses data/ontology/tools.json
        """
        if ontology_file is None:
            # Default location
            project_root = Path(__file__).parent.parent.parent.parent
            ontology_dir = project_root / "data" / "ontology"
            ontology_dir.mkdir(parents=True, exist_ok=True)
            ontology_file = ontology_dir / "tools.json"

        self.ontology_file = ontology_file
        self._ontology: Optional[ToolOntology] = None

    def load(self, force_reload: bool = False) -> ToolOntology:
        """
        Load the tool ontology

        Args:
            force_reload: Force reload from disk even if already loaded

        Returns:
            ToolOntology instance
        """
        if self._ontology and not force_reload:
            return self._ontology

        if not self.ontology_file.exists():
            logger.info("Ontology file not found, generating initial ontology")
            self._ontology = generate_initial_ontology()
            self.save()
        else:
            logger.info(f"Loading ontology from {self.ontology_file}")
            with open(self.ontology_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._ontology = ToolOntology(**data)

        logger.info(f"Loaded {len(self._ontology.tools)} tools")
        return self._ontology

    def save(self) -> None:
        """Save the ontology to disk"""
        if not self._ontology:
            raise ValueError("No ontology loaded")

        logger.info(f"Saving ontology to {self.ontology_file}")
        with open(self.ontology_file, "w", encoding="utf-8") as f:
            json.dump(self._ontology.model_dump(), f, indent=2, ensure_ascii=False)
        logger.info("Ontology saved successfully")

    def get_all_tools(self, enabled_only: bool = True) -> List[ConceptualTool]:
        """
        Get all tools

        Args:
            enabled_only: Only return enabled tools

        Returns:
            List of conceptual tools
        """
        ontology = self.load()
        if enabled_only:
            return ontology.get_enabled_tools()
        return ontology.tools

    def get_tool(self, name: str) -> Optional[ConceptualTool]:
        """Get tool by name"""
        ontology = self.load()
        return ontology.get_tool(name)

    def get_tool_by_id(self, tool_id: str) -> Optional[ConceptualTool]:
        """Get tool by ID"""
        ontology = self.load()
        return ontology.get_tool_by_id(tool_id)

    def get_tools_by_category(self, category: ToolCategory) -> List[ConceptualTool]:
        """Get tools by category"""
        ontology = self.load()
        return ontology.get_tools_by_category(category)

    def search_tools(self, query: str) -> List[ConceptualTool]:
        """Search tools"""
        ontology = self.load()
        return ontology.search_tools(query)

    def add_tool(self, tool: ConceptualTool) -> None:
        """Add a new tool to the ontology"""
        ontology = self.load()

        # Check for duplicates
        if ontology.get_tool(tool.name):
            raise ValueError(f"Tool with name '{tool.name}' already exists")
        if ontology.get_tool_by_id(tool.id):
            raise ValueError(f"Tool with ID '{tool.id}' already exists")

        ontology.tools.append(tool)
        self.save()
        logger.info(f"Added tool: {tool.name}")

    def update_tool(self, tool: ConceptualTool) -> None:
        """Update an existing tool"""
        ontology = self.load()

        for i, existing_tool in enumerate(ontology.tools):
            if existing_tool.id == tool.id:
                ontology.tools[i] = tool
                self.save()
                logger.info(f"Updated tool: {tool.name}")
                return

        raise ValueError(f"Tool with ID '{tool.id}' not found")

    def delete_tool(self, tool_id: str) -> None:
        """Delete a tool"""
        ontology = self.load()

        for i, tool in enumerate(ontology.tools):
            if tool.id == tool_id:
                ontology.tools.pop(i)
                self.save()
                logger.info(f"Deleted tool: {tool.name}")
                return

        raise ValueError(f"Tool with ID '{tool_id}' not found")

    def get_tools_for_api(self) -> List[Dict[str, Any]]:
        """
        Get tools in API-friendly format

        Returns:
            List of tool dictionaries
        """
        tools = self.get_all_tools(enabled_only=True)

        return [
            {
                "id": tool.id,
                "name": tool.name,
                "display_name": tool.display_name,
                "category": tool.category.value,
                "type": tool.type.value,
                "description": tool.description,
                "use_cases": tool.use_cases,
                "implementations": [
                    {
                        "crewai_class": impl.crewai_class,
                        "name": impl.name,
                        "description": impl.description,
                        "requires_api_key": impl.requires_api_key,
                        "api_key_env": impl.api_key_env,
                    }
                    for impl in tool.implementations
                ],
                "default_implementation": tool.default_implementation,
                "compatible_roles": tool.compatible_roles,
                "compatible_tasks": tool.compatible_tasks,
                "usage_count": tool.usage_count,
                "tags": tool.tags,
            }
            for tool in tools
        ]

    def increment_usage(self, tool_name: str) -> None:
        """Increment usage count for a tool"""
        tool = self.get_tool(tool_name)
        if tool:
            tool.usage_count += 1
            self.update_tool(tool)


# Global instance
_manager: Optional[ToolOntologyManager] = None


def get_tool_ontology_manager() -> ToolOntologyManager:
    """Get the global tool ontology manager instance"""
    global _manager
    if _manager is None:
        _manager = ToolOntologyManager()
    return _manager
