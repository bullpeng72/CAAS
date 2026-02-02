"""
Ontology Module

Tool and domain ontology management.
"""

from caas_framework.knowledge.ontology.manager import (
    ROLE_TASK_MAPPINGS,
    TASK_TOOL_MAPPINGS,
    AgentRole,
    OntologyManager,
    TaskType,
    ToolCapability,
)
from caas_framework.knowledge.ontology.tool_manager import (
    ToolOntologyManager,
    get_tool_ontology_manager,
)
from caas_framework.knowledge.ontology.tool_ontology import (
    ConceptualTool,
    ToolCategory,
    ToolImplementation,
    ToolOntology,
    ToolType,
)

__all__ = [
    "ToolOntology",
    "ConceptualTool",
    "ToolImplementation",
    "ToolCategory",
    "ToolType",
    "ToolOntologyManager",
    "get_tool_ontology_manager",
    "OntologyManager",
    "AgentRole",
    "TaskType",
    "ToolCapability",
    "ROLE_TASK_MAPPINGS",
    "TASK_TOOL_MAPPINGS",
]
