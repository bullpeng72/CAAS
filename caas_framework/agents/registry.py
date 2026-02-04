"""
Agent Registry - Dynamic Agent Discovery and Registration

Implements the Registry pattern to eliminate hard-coded agent dependencies.
This is part of the fundamental redesign to apply Dependency Inversion Principle.

The Registry allows:
1. Agents to self-register via decorators
2. Dynamic agent discovery by phase
3. Plugin-based architecture for adding new agents
4. Testability through mocking

Usage:
    >>> from caas_framework.agents.registry import register_agent, AgentRegistry
    >>>
    >>> # Agent self-registers via decorator
    >>> @register_agent(phase=AgentPhase.DISCOVERY)
    >>> class MyAgent(BaseExpertAgent):
    >>>     ...
    >>>
    >>> # Collaboration uses registry instead of hard-coding
    >>> registry = AgentRegistry()
    >>> discovery_agent_class = registry.get_agent_class(AgentPhase.DISCOVERY)
    >>> agent_instance = discovery_agent_class(llm_plugin, golden_data)
"""

from typing import Callable, Dict, List, Optional, Type

from caas_framework.agents.base import AgentPhase, BaseExpertAgent
from caas_framework.utils.logger import get_logger

logger = get_logger()


class AgentRegistry:
    """
    Agent Registry - Central repository for agent discovery.

    Uses singleton pattern to maintain a single source of truth
    for all registered agents.

    Thread-safe for multi-threaded environments.
    """

    _instance: Optional["AgentRegistry"] = None
    _initialized: bool = False

    def __new__(cls):
        """Singleton pattern - only one registry instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize registry (only once due to singleton)."""
        if not AgentRegistry._initialized:
            # Phase -> Agent class mapping
            self._agents_by_phase: Dict[AgentPhase, Type[BaseExpertAgent]] = {}

            # Agent name -> Agent class mapping (for lookup by name)
            self._agents_by_name: Dict[str, Type[BaseExpertAgent]] = {}

            # All registered agent classes
            self._all_agents: List[Type[BaseExpertAgent]] = []

            AgentRegistry._initialized = True
            logger.info("AgentRegistry initialized")

    def register(
        self,
        agent_class: Type[BaseExpertAgent],
        phase: AgentPhase,
        override: bool = False,
    ) -> None:
        """
        Register an agent class.

        Args:
            agent_class: The agent class to register
            phase: The phase this agent is responsible for
            override: If True, allow overriding existing agent for phase

        Raises:
            ValueError: If phase already has an agent and override=False
        """
        # Validate agent class
        if not issubclass(agent_class, BaseExpertAgent):
            raise TypeError(
                f"Agent class {agent_class.__name__} must inherit from BaseExpertAgent"
            )

        # Check for existing registration
        if phase in self._agents_by_phase and not override:
            existing = self._agents_by_phase[phase]
            raise ValueError(
                f"Phase {phase.value} already has registered agent: {existing.__name__}. "
                f"Use override=True to replace."
            )

        # Register
        self._agents_by_phase[phase] = agent_class

        # Also register by class name for lookup
        class_name = agent_class.__name__
        self._agents_by_name[class_name] = agent_class

        # Add to all agents list
        if agent_class not in self._all_agents:
            self._all_agents.append(agent_class)

        logger.info(f"Registered agent {class_name} for phase {phase.value}")

    def get_agent_class(self, phase: AgentPhase) -> Type[BaseExpertAgent]:
        """
        Get agent class for a specific phase.

        Args:
            phase: The phase to get agent for

        Returns:
            Agent class registered for this phase

        Raises:
            KeyError: If no agent registered for phase
        """
        if phase not in self._agents_by_phase:
            raise KeyError(
                f"No agent registered for phase {phase.value}. "
                f"Available phases: {list(self._agents_by_phase.keys())}"
            )

        return self._agents_by_phase[phase]

    def get_agent_by_name(self, name: str) -> Type[BaseExpertAgent]:
        """
        Get agent class by name.

        Args:
            name: Agent class name

        Returns:
            Agent class with matching name

        Raises:
            KeyError: If no agent with that name
        """
        if name not in self._agents_by_name:
            raise KeyError(
                f"No agent registered with name {name}. "
                f"Available agents: {list(self._agents_by_name.keys())}"
            )

        return self._agents_by_name[name]

    def get_all_phases(self) -> List[AgentPhase]:
        """
        Get all phases that have registered agents.

        Returns:
            List of phases with registered agents
        """
        return list(self._agents_by_phase.keys())

    def get_all_agents(self) -> List[Type[BaseExpertAgent]]:
        """
        Get all registered agent classes.

        Returns:
            List of all registered agent classes
        """
        return self._all_agents.copy()

    def is_registered(self, phase: AgentPhase) -> bool:
        """
        Check if a phase has a registered agent.

        Args:
            phase: Phase to check

        Returns:
            True if phase has registered agent
        """
        return phase in self._agents_by_phase

    def clear(self) -> None:
        """
        Clear all registrations.

        Useful for testing. Use with caution in production.
        """
        self._agents_by_phase.clear()
        self._agents_by_name.clear()
        self._all_agents.clear()
        logger.warning("AgentRegistry cleared")

    def get_registry_info(self) -> Dict:
        """
        Get information about current registry state.

        Returns:
            Dictionary with registry statistics
        """
        return {
            "total_agents": len(self._all_agents),
            "phases_covered": len(self._agents_by_phase),
            "registered_phases": [
                phase.value for phase in self._agents_by_phase.keys()
            ],
            "registered_agents": [cls.__name__ for cls in self._all_agents],
        }


# Global registry instance (singleton)
_global_registry = AgentRegistry()


def get_agent_registry() -> AgentRegistry:
    """
    Get the global agent registry instance.

    Returns:
        Global AgentRegistry singleton
    """
    return _global_registry


def register_agent(
    phase: AgentPhase, override: bool = False
) -> Callable[[Type[BaseExpertAgent]], Type[BaseExpertAgent]]:
    """
    Decorator to register an agent class.

    Usage:
        >>> @register_agent(phase=AgentPhase.DISCOVERY)
        >>> class RequirementAnalystAgent(BaseExpertAgent):
        >>>     ...

    Args:
        phase: The phase this agent is responsible for
        override: Allow overriding existing agent for phase

    Returns:
        Decorator function
    """

    def decorator(agent_class: Type[BaseExpertAgent]) -> Type[BaseExpertAgent]:
        """Register the agent class."""
        registry = get_agent_registry()
        registry.register(agent_class, phase, override=override)
        return agent_class

    return decorator


def discover_agents() -> AgentRegistry:
    """
    Discover all agents by importing agent modules.

    This function imports all known agent modules to trigger
    their @register_agent decorators.

    Returns:
        AgentRegistry with all discovered agents
    """
    try:
        # Import all agent modules to trigger registration
        from caas_framework.agents import (  # noqa: F401
            agent_designer,
            code_analysis_agent,
            code_generator,
            qa_specialist,
            requirement_analyst,
            system_architect,
        )

        logger.info("Agent discovery completed")

    except ImportError as e:
        logger.warning(f"Some agents could not be imported: {e}")

    return get_agent_registry()


def create_agent(
    phase: AgentPhase, llm_plugin, golden_data=None, **kwargs
) -> BaseExpertAgent:
    """
    Factory function to create agent instance by phase.

    This is a convenience function that combines registry lookup
    with instance creation.

    Args:
        phase: Phase to get agent for
        llm_plugin: LLM plugin for agent
        golden_data: Optional golden data
        **kwargs: Additional arguments for agent constructor

    Returns:
        Instantiated agent for the phase

    Example:
        >>> from caas_framework.agents.registry import create_agent
        >>> agent = create_agent(
        >>>     phase=AgentPhase.DISCOVERY,
        >>>     llm_plugin=my_llm,
        >>>     golden_data=my_golden_data
        >>> )
    """
    registry = get_agent_registry()
    agent_class = registry.get_agent_class(phase)

    # Create instance
    return agent_class(llm_plugin, golden_data, **kwargs)
