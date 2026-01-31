"""
Expert Agents for BMAD Pipeline

Specialized agents for each phase of the BMAD workflow.
"""

from caas_framework.agents.base import BaseExpertAgent, AgentPhase
from caas_framework.agents.requirement_analyst import RequirementAnalystAgent
from caas_framework.agents.system_architect import SystemArchitectAgent
from caas_framework.agents.agent_designer import AgentDesignerAgent
from caas_framework.agents.code_generator import CodeGeneratorAgent
from caas_framework.agents.qa_specialist import QASpecialistAgent
from caas_framework.agents.capability_assessment import (
    CapabilityAssessment,
    CapabilityLevel,
    AgentCapability,
    CapabilityRegistry,
    get_capability_registry,
    register_agent_capability
)
from caas_framework.agents.self_aware import (
    SelfAwareMixin,
    SelfAwareAgent
)

__all__ = [
    # Base classes
    "BaseExpertAgent",
    "AgentPhase",
    # Specialist agents
    "RequirementAnalystAgent",
    "SystemArchitectAgent",
    "AgentDesignerAgent",
    "CodeGeneratorAgent",
    "QASpecialistAgent",
    # Self-aware agents
    "SelfAwareMixin",
    "SelfAwareAgent",
    # Capability assessment
    "CapabilityAssessment",
    "CapabilityLevel",
    "AgentCapability",
    "CapabilityRegistry",
    "get_capability_registry",
    "register_agent_capability",
]
