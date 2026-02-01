"""
Expert Agents for BMAD Pipeline

Specialized agents for each phase of the BMAD workflow.

NEW (v2.0): Registry-based agent discovery
- Use get_agent_registry() to discover all agents
- Use create_agent(phase, llm, golden_data) to instantiate agents
- Agents self-register via @register_agent decorator
"""

from caas_framework.agents.base import BaseExpertAgent, AgentPhase

# Registry - NEW PRIMARY INTERFACE
from caas_framework.agents.registry import (
    AgentRegistry,
    get_agent_registry,
    register_agent,
    create_agent,
    discover_agents
)

# Import agent modules to trigger registration
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

    # Registry (NEW - PRIMARY INTERFACE)
    "AgentRegistry",
    "get_agent_registry",
    "register_agent",
    "create_agent",
    "discover_agents",

    # Specialist agents (still exported for backward compatibility)
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
