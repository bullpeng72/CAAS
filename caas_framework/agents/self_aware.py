"""
Self-Aware Agent Implementation

Provides self-awareness capabilities for agents to assess their own
ability to complete tasks and delegate when necessary.
"""

import logging
from typing import Any, Dict, Optional, List
from abc import ABC, abstractmethod

from caas_framework.agents.capability_assessment import (
    CapabilityAssessment,
    AgentCapability,
    CapabilityLevel,
    get_capability_registry
)
from caas_framework.plugins.llm.base import LLMPlugin

logger = logging.getLogger(__name__)


class SelfAwareMixin:
    """
    Mixin to add self-awareness capabilities to agents.

    Provides methods for capability self-assessment and delegation.
    Agents can use this to determine if they should attempt a task
    or request help from others.
    """

    def __init__(self, *args, **kwargs):
        """Initialize self-aware mixin"""
        super().__init__(*args, **kwargs)
        self._capability_cache: Dict[str, CapabilityAssessment] = {}

    async def can_perform(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None
    ) -> CapabilityAssessment:
        """
        Assess if this agent can perform a task.

        Uses LLM to analyze the task against the agent's role,
        tools, and expertise to determine confidence level.

        Args:
            task: Task description
            context: Optional context information

        Returns:
            CapabilityAssessment with confidence and reasoning
        """
        # Check cache first
        cache_key = f"{task}:{str(context)}"
        if cache_key in self._capability_cache:
            logger.debug(f"[{self.agent_name}] Using cached capability assessment")
            return self._capability_cache[cache_key]

        # Get agent's capabilities
        agent_role = getattr(self, 'role', self.agent_name)
        agent_goal = getattr(self, 'goal', '')
        agent_backstory = getattr(self, 'backstory', '')
        agent_tools = getattr(self, 'tools', [])

        # Build assessment prompt
        prompt = self._build_capability_prompt(
            task=task,
            agent_role=agent_role,
            agent_goal=agent_goal,
            agent_backstory=agent_backstory,
            agent_tools=agent_tools,
            context=context
        )

        # Use LLM to assess capability
        try:
            llm = getattr(self, 'llm', None)
            if not llm:
                logger.warning(f"[{self.agent_name}] No LLM available for capability assessment")
                # Fallback: assume capable
                return CapabilityAssessment(
                    confidence=0.7,
                    reasoning="No LLM available for assessment, assuming capable",
                    missing_capabilities=[],
                    alternative_approach=None
                )

            response = await llm.generate(prompt, temperature=0.3)

            # Parse response
            assessment = self._parse_capability_response(response)

            # Cache assessment
            self._capability_cache[cache_key] = assessment

            logger.info(
                f"[{self.agent_name}] Capability assessment: "
                f"confidence={assessment.confidence:.2f}, "
                f"level={assessment.capability_level.value}"
            )

            return assessment

        except Exception as e:
            logger.error(f"[{self.agent_name}] Error in capability assessment: {e}")
            # Fallback: assume capable but with reduced confidence
            return CapabilityAssessment(
                confidence=0.6,
                reasoning=f"Error during assessment: {str(e)}. Assuming moderate capability.",
                missing_capabilities=[],
                alternative_approach=None
            )

    def _build_capability_prompt(
        self,
        task: str,
        agent_role: str,
        agent_goal: str,
        agent_backstory: str,
        agent_tools: List[str],
        context: Optional[Dict[str, Any]]
    ) -> str:
        """Build prompt for capability assessment"""

        tools_str = ", ".join(agent_tools) if agent_tools else "No tools"

        prompt = f"""You are assessing your own capability to perform a task.

Your Role: {agent_role}
Your Goal: {agent_goal}
Your Backstory: {agent_backstory}
Your Available Tools: {tools_str}

Task to Assess: {task}

"""

        if context:
            prompt += f"\nContext: {context}\n"

        prompt += """
Analyze whether you can successfully complete this task given your role, goal, expertise, and available tools.

Provide your assessment in the following format:

CONFIDENCE: <0.0-1.0>
REASONING: <Explain why you can or cannot do this task>
MISSING_CAPABILITIES: <List any missing capabilities, separated by semicolons, or "None">
ALTERNATIVE_APPROACH: <Suggest an alternative if confidence < 0.7, or "None">
SUGGESTED_AGENTS: <List agents better suited for this task, separated by semicolons, or "None">
MISSING_TOOLS: <List tools you need but don't have, separated by semicolons, or "None">
DIFFICULTY: <1-10, where 1 is trivial and 10 is extremely difficult>

Guidelines:
- Be honest about your limitations
- Confidence >= 0.9: You are an expert at this
- Confidence >= 0.7: You can do this well
- Confidence >= 0.5: You can try but may struggle
- Confidence < 0.5: You should request help
- Consider if the task matches your role and expertise
- Consider if you have the necessary tools
- Consider if the task is within your domain

Assessment:
"""

        return prompt

    def _parse_capability_response(self, response: str) -> CapabilityAssessment:
        """Parse LLM response into CapabilityAssessment"""

        lines = response.strip().split('\n')
        data = {}

        for line in lines:
            line = line.strip()
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().upper()
                value = value.strip()
                data[key] = value

        # Extract confidence
        confidence_str = data.get('CONFIDENCE', '0.7')
        try:
            confidence = float(confidence_str)
            confidence = max(0.0, min(1.0, confidence))  # Clamp to 0-1
        except ValueError:
            confidence = 0.7

        # Extract reasoning
        reasoning = data.get('REASONING', 'No reasoning provided')

        # Extract missing capabilities
        missing_cap_str = data.get('MISSING_CAPABILITIES', 'None')
        if missing_cap_str.lower() == 'none':
            missing_capabilities = []
        else:
            missing_capabilities = [c.strip() for c in missing_cap_str.split(';') if c.strip()]

        # Extract alternative approach
        alt_approach = data.get('ALTERNATIVE_APPROACH', None)
        if alt_approach and alt_approach.lower() == 'none':
            alt_approach = None

        # Extract suggested agents
        suggested_str = data.get('SUGGESTED_AGENTS', 'None')
        if suggested_str.lower() == 'none':
            suggested_agents = []
        else:
            suggested_agents = [a.strip() for a in suggested_str.split(';') if a.strip()]

        # Extract missing tools
        missing_tools_str = data.get('MISSING_TOOLS', 'None')
        if missing_tools_str.lower() == 'none':
            missing_tools = []
        else:
            missing_tools = [t.strip() for t in missing_tools_str.split(';') if t.strip()]

        # Extract difficulty
        difficulty_str = data.get('DIFFICULTY', None)
        difficulty = None
        if difficulty_str:
            try:
                difficulty = int(difficulty_str)
                difficulty = max(1, min(10, difficulty))  # Clamp to 1-10
            except ValueError:
                pass

        return CapabilityAssessment(
            confidence=confidence,
            reasoning=reasoning,
            missing_capabilities=missing_capabilities,
            alternative_approach=alt_approach,
            suggested_agents=suggested_agents,
            missing_tools=missing_tools,
            difficulty=difficulty
        )

    async def execute_or_delegate(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
        force_execute: bool = False
    ) -> Any:
        """
        Execute task if confident, otherwise delegate or request help.

        Args:
            task: Task description
            context: Optional context
            force_execute: Force execution even if low confidence

        Returns:
            Task result or delegation message
        """
        # Assess capability
        assessment = await self.can_perform(task, context)

        logger.info(
            f"[{self.agent_name}] Capability assessment for task: "
            f"confidence={assessment.confidence:.2f}"
        )

        # High confidence: execute
        if assessment.can_attempt or force_execute:
            logger.info(f"[{self.agent_name}] Executing task (confidence={assessment.confidence:.2f})")
            return await self._execute_task(task, context)

        # Low confidence: delegate or request help
        else:
            logger.warning(
                f"[{self.agent_name}] Low confidence ({assessment.confidence:.2f}), "
                f"requesting help"
            )
            return await self.request_help(task, assessment, context)

    @abstractmethod
    async def _execute_task(
        self,
        task: str,
        context: Optional[Dict[str, Any]]
    ) -> Any:
        """
        Execute the task (to be implemented by subclass).

        Args:
            task: Task description
            context: Optional context

        Returns:
            Task result
        """
        raise NotImplementedError("Subclass must implement _execute_task")

    async def request_help(
        self,
        task: str,
        assessment: CapabilityAssessment,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Request help from other agents.

        Args:
            task: Task description
            assessment: Capability assessment explaining why help is needed
            context: Optional context

        Returns:
            Help request result
        """
        logger.info(
            f"[{self.agent_name}] Requesting help: {assessment.reasoning}"
        )

        # Find better suited agents
        registry = get_capability_registry()
        suggested = assessment.suggested_agents

        if not suggested:
            # Try to find best agent from registry
            best_agent = registry.find_best_agent(task)
            if best_agent and best_agent != self.agent_name:
                suggested = [best_agent]

        help_request = {
            "status": "help_requested",
            "requesting_agent": self.agent_name,
            "task": task,
            "reason": assessment.reasoning,
            "confidence": assessment.confidence,
            "missing_capabilities": assessment.missing_capabilities,
            "missing_tools": assessment.missing_tools,
            "suggested_agents": suggested,
            "alternative_approach": assessment.alternative_approach,
            "context": context
        }

        logger.debug(f"[{self.agent_name}] Help request: {help_request}")

        return help_request

    def clear_capability_cache(self):
        """Clear the capability assessment cache"""
        self._capability_cache.clear()
        logger.debug(f"[{self.agent_name}] Cleared capability cache")


class SelfAwareAgent(SelfAwareMixin, ABC):
    """
    Base class for self-aware agents.

    Combines SelfAwareMixin with a base structure for agents.
    Subclasses must implement _execute_task.
    """

    def __init__(
        self,
        agent_name: str,
        llm: LLMPlugin,
        role: str = "",
        goal: str = "",
        backstory: str = "",
        tools: Optional[List[str]] = None
    ):
        """
        Initialize self-aware agent.

        Args:
            agent_name: Name of the agent
            llm: LLM plugin
            role: Agent's role
            goal: Agent's goal
            backstory: Agent's backstory
            tools: List of available tool names
        """
        self.agent_name = agent_name
        self.llm = llm
        self.role = role
        self.goal = goal
        self.backstory = backstory
        self.tools = tools or []

        super().__init__()

        # Register capabilities
        capability = AgentCapability(
            agent_name=agent_name,
            expertise=[role] if role else [],
            tools=self.tools,
            task_types=[],
            backstory=backstory,
            goal=goal
        )
        get_capability_registry().register(capability)

    @abstractmethod
    async def _execute_task(
        self,
        task: str,
        context: Optional[Dict[str, Any]]
    ) -> Any:
        """Execute the task (implement in subclass)"""
        pass
