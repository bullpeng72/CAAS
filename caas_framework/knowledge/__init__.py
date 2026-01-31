"""
CAAS Framework Knowledge Module

Ontology-based knowledge management for agent validation and reasoning.
"""

from caas_framework.knowledge.ontology import (
    AgentRole,
    TaskType,
    ToolCapability,
    OntologyManager,
    ROLE_TASK_MAPPINGS,
    TASK_TOOL_MAPPINGS,
    TOOL_CAPABILITIES,
)

__all__ = [
    "AgentRole",
    "TaskType",
    "ToolCapability",
    "OntologyManager",
    "ROLE_TASK_MAPPINGS",
    "TASK_TOOL_MAPPINGS",
    "TOOL_CAPABILITIES",
]
