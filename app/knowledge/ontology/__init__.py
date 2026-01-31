"""
CAAS Ontology Package

에이전트 개발을 위한 온톨로지 관리를 제공합니다.

주요 구성요소:
- OntologyManager: 온톨로지 관리자
- OntologyReasoner: 온톨로지 기반 추론기
"""

from app.knowledge.ontology.manager import (
    AgentRole,
    TaskType,
    ToolCapability,
    DomainCategory,
    OntologyEntity,
    OntologyRelation,
    OntologyManager,
    ROLE_TASK_MAPPINGS,
    TASK_TOOL_MAPPINGS,
    # TOOL_CAPABILITIES removed - now dynamically generated in OntologyManager
)
from app.knowledge.ontology.reasoner import (
    OntologyReasoner,
    InferenceType,
    InferenceResult,
    ReasoningRule,
)

__all__ = [
    # Manager
    "AgentRole",
    "TaskType",
    "ToolCapability",
    "DomainCategory",
    "OntologyEntity",
    "OntologyRelation",
    "OntologyManager",
    "ROLE_TASK_MAPPINGS",
    "TASK_TOOL_MAPPINGS",
    # TOOL_CAPABILITIES removed - now dynamically generated
    # Reasoner
    "OntologyReasoner",
    "InferenceType",
    "InferenceResult",
    "ReasoningRule",
]
