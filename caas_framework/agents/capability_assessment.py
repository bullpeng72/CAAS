"""
Capability Assessment for Self-Aware Agents

Provides capability self-assessment and delegation mechanisms for agents.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


class CapabilityLevel(str, Enum):
    """Agent capability confidence levels"""
    EXPERT = "expert"          # 0.9-1.0: Highly confident
    PROFICIENT = "proficient"  # 0.7-0.9: Confident
    CAPABLE = "capable"        # 0.5-0.7: Somewhat confident
    LIMITED = "limited"        # 0.3-0.5: Low confidence
    UNABLE = "unable"          # 0.0-0.3: Cannot perform


@dataclass
class CapabilityAssessment:
    """
    Agent's self-assessment of capability to perform a task.

    Represents an agent's analysis of whether it can successfully
    complete a given task based on its tools, expertise, and role.
    """

    # Confidence score (0.0 = cannot do, 1.0 = highly confident)
    confidence: float

    # Agent's reasoning about capability
    reasoning: str

    # Missing capabilities preventing successful execution
    missing_capabilities: List[str] = field(default_factory=list)

    # Alternative approach if confidence is low
    alternative_approach: Optional[str] = None

    # Suggested agent(s) better suited for this task
    suggested_agents: List[str] = field(default_factory=list)

    # Required tools that agent doesn't have
    missing_tools: List[str] = field(default_factory=list)

    # Estimated difficulty (1-10)
    difficulty: Optional[int] = None

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def capability_level(self) -> CapabilityLevel:
        """Get capability level from confidence score"""
        if self.confidence >= 0.9:
            return CapabilityLevel.EXPERT
        elif self.confidence >= 0.7:
            return CapabilityLevel.PROFICIENT
        elif self.confidence >= 0.5:
            return CapabilityLevel.CAPABLE
        elif self.confidence >= 0.3:
            return CapabilityLevel.LIMITED
        else:
            return CapabilityLevel.UNABLE

    @property
    def can_attempt(self) -> bool:
        """Check if agent should attempt task (confidence >= 0.7)"""
        return self.confidence >= 0.7

    @property
    def needs_help(self) -> bool:
        """Check if agent needs help (confidence < 0.5)"""
        return self.confidence < 0.5

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "confidence": self.confidence,
            "capability_level": self.capability_level.value,
            "can_attempt": self.can_attempt,
            "needs_help": self.needs_help,
            "reasoning": self.reasoning,
            "missing_capabilities": self.missing_capabilities,
            "alternative_approach": self.alternative_approach,
            "suggested_agents": self.suggested_agents,
            "missing_tools": self.missing_tools,
            "difficulty": self.difficulty,
            "metadata": self.metadata
        }

    def __repr__(self) -> str:
        return (
            f"CapabilityAssessment("
            f"confidence={self.confidence:.2f}, "
            f"level={self.capability_level.value}, "
            f"can_attempt={self.can_attempt})"
        )


@dataclass
class AgentCapability:
    """
    Defines an agent's capabilities.

    Used to describe what an agent can do, what tools it has,
    and what types of tasks it excels at.
    """

    # Agent role/name
    agent_name: str

    # Agent's primary expertise areas
    expertise: List[str]

    # Available tools
    tools: List[str]

    # Task types this agent excels at
    task_types: List[str] = field(default_factory=list)

    # Confidence threshold for attempting tasks
    min_confidence: float = 0.7

    # Agent's backstory/context
    backstory: str = ""

    # Goal/purpose
    goal: str = ""

    def matches_task(self, task_description: str) -> float:
        """
        Estimate match score for a task (simple keyword matching).

        Args:
            task_description: Description of the task

        Returns:
            Match score 0.0-1.0
        """
        task_lower = task_description.lower()
        matches = 0
        total_checks = 0

        # Check expertise keywords
        for exp in self.expertise:
            total_checks += 1
            if exp.lower() in task_lower:
                matches += 1

        # Check task types
        for task_type in self.task_types:
            total_checks += 1
            if task_type.lower() in task_lower:
                matches += 1

        # Check tools
        for tool in self.tools:
            total_checks += 1
            if tool.lower() in task_lower:
                matches += 1

        if total_checks == 0:
            return 0.5  # Neutral if no keywords to check

        return matches / total_checks

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "agent_name": self.agent_name,
            "expertise": self.expertise,
            "tools": self.tools,
            "task_types": self.task_types,
            "min_confidence": self.min_confidence,
            "backstory": self.backstory,
            "goal": self.goal
        }


class CapabilityRegistry:
    """
    Registry of agent capabilities.

    Maintains a catalog of what each agent can do for task routing
    and capability lookups.
    """

    def __init__(self):
        """Initialize capability registry"""
        self._capabilities: Dict[str, AgentCapability] = {}

    def register(self, capability: AgentCapability):
        """
        Register an agent's capabilities.

        Args:
            capability: Agent capability definition
        """
        self._capabilities[capability.agent_name] = capability

    def get(self, agent_name: str) -> Optional[AgentCapability]:
        """
        Get capabilities for an agent.

        Args:
            agent_name: Name of the agent

        Returns:
            AgentCapability or None if not found
        """
        return self._capabilities.get(agent_name)

    def find_best_agent(self, task_description: str) -> Optional[str]:
        """
        Find the best agent for a task.

        Args:
            task_description: Description of the task

        Returns:
            Name of best-matched agent or None
        """
        if not self._capabilities:
            return None

        best_agent = None
        best_score = 0.0

        for agent_name, capability in self._capabilities.items():
            score = capability.matches_task(task_description)
            if score > best_score:
                best_score = score
                best_agent = agent_name

        return best_agent if best_score > 0.3 else None

    def get_all_capabilities(self) -> Dict[str, AgentCapability]:
        """Get all registered capabilities"""
        return self._capabilities.copy()

    def list_agents(self) -> List[str]:
        """List all registered agent names"""
        return list(self._capabilities.keys())


# Global capability registry
_global_registry = CapabilityRegistry()


def get_capability_registry() -> CapabilityRegistry:
    """Get the global capability registry"""
    return _global_registry


def register_agent_capability(capability: AgentCapability):
    """Register an agent capability in the global registry"""
    _global_registry.register(capability)
