"""
CAAS Framework Knowledge Module

Ontology-based knowledge management for agent validation and reasoning.
"""

from caas_framework.knowledge.ontology import (
    ROLE_TASK_MAPPINGS,
    TASK_TOOL_MAPPINGS,
    AgentRole,
    OntologyManager,
    TaskType,
    ToolCapability,
)

__all__ = [
    "AgentRole",
    "TaskType",
    "ToolCapability",
    "OntologyManager",
    "ROLE_TASK_MAPPINGS",
    "TASK_TOOL_MAPPINGS",
]
