"""
Self-Aware Agent (Meta-Cognition)

Implements agents that can assess their own capabilities and limitations,
enabling intelligent delegation and help-seeking behavior.
"""

from dataclasses import dataclass
from typing import Any, Callable, List, Optional, Protocol

from pydantic import BaseModel, Field

from caas_framework.utils.logger import get_logger

logger = get_logger()


class CapabilityAssessment(BaseModel):
    """Assessment of an agent's capability to perform a task."""

    confidence: float = Field(ge=0.0, le=1.0, description="Confidence level (0.0-1.0)")
    reasoning: str = Field(
        description="Explanation of why agent can or cannot perform task"
    )
    missing_capabilities: List[str] = Field(
        default_factory=list, description="Required capabilities that are missing"
    )
    alternative_approach: Optional[str] = Field(
        default=None, description="Suggested alternative if confidence is low"
    )
    estimated_difficulty: Optional[str] = Field(
        default=None, description="Easy, Medium, Hard, or Impossible"
    )


@dataclass
class AgentCapabilities:
    """Defines an agent's capabilities."""

    role: str
    tools: List[str]
    expertise: str
    goal: str
    known_limitations: List[str] = None

    def __post_init__(self):
        if self.known_limitations is None:
            self.known_limitations = []


class SelfAssessmentStrategy(Protocol):
    """Protocol for self-assessment strategies."""

    def assess(
        self, task: str, capabilities: AgentCapabilities
    ) -> CapabilityAssessment:
        """Assess capability to perform task."""
        ...


class RuleBasedAssessment:
    """Rule-based self-assessment strategy."""

    def __init__(self):
        # Common capability patterns
        self.tool_requirements = {
            "search": ["web_search", "http_client"],
            "file": ["file_read", "file_write"],
            "database": ["database"],
            "api": ["http_client"],
            "code": ["code_analysis", "file_write"],
            "git": ["git"],
            "shell": ["shell"],
        }

    def assess(
        self, task: str, capabilities: AgentCapabilities
    ) -> CapabilityAssessment:
        """Rule-based assessment."""
        task_lower = task.lower()
        confidence = 1.0
        missing = []
        reasoning_parts = []
        found_requirements = 0

        # Check if task mentions things outside expertise
        for keyword, required_tools in self.tool_requirements.items():
            if keyword in task_lower:
                found_requirements += 1
                has_tools = any(tool in capabilities.tools for tool in required_tools)
                if not has_tools:
                    confidence -= 0.5  # More aggressive penalty
                    missing.extend(
                        [t for t in required_tools if t not in capabilities.tools]
                    )
                    reasoning_parts.append(
                        f"Task requires {keyword} capability but missing tools: {required_tools}"
                    )

        # Check known limitations
        for limitation in capabilities.known_limitations:
            if limitation.lower() in task_lower:
                confidence -= 0.5  # More aggressive penalty
                reasoning_parts.append(f"Task involves known limitation: {limitation}")
                missing.append(limitation)

        # If no requirements found and agent has few tools, be more cautious
        if found_requirements == 0 and len(capabilities.tools) == 0:
            confidence = 0.3  # Low confidence with no tools
            reasoning_parts.append("No specific tools available for general tasks")

        # Ensure confidence stays in bounds
        confidence = max(0.0, min(1.0, confidence))

        # Build reasoning
        if confidence >= 0.7:
            reasoning = f"Agent '{capabilities.role}' can perform this task. "
            if reasoning_parts:
                reasoning += "Minor concerns: " + "; ".join(reasoning_parts)
            else:
                reasoning += "All required capabilities are available."
        else:
            reasoning = f"Agent '{capabilities.role}' has low confidence. "
            reasoning += "; ".join(reasoning_parts)

        # Suggest alternative if needed
        alternative = None
        if confidence < 0.7 and missing:
            alternative = (
                f"Delegate to agent with capabilities: {', '.join(set(missing))}"
            )

        # Estimate difficulty
        difficulty = "Easy"
        if confidence < 0.9:
            difficulty = "Medium"
        if confidence < 0.7:
            difficulty = "Hard"
        if confidence < 0.3:
            difficulty = "Impossible"

        return CapabilityAssessment(
            confidence=confidence,
            reasoning=reasoning,
            missing_capabilities=list(set(missing)),
            alternative_approach=alternative,
            estimated_difficulty=difficulty,
        )


class LLMBasedAssessment:
    """LLM-based self-assessment strategy."""

    def __init__(self, llm_provider):
        """
        Initialize LLM-based assessment.

        Args:
            llm_provider: LLM provider with generate_structured method
        """
        self.llm = llm_provider

    def assess(
        self, task: str, capabilities: AgentCapabilities
    ) -> CapabilityAssessment:
        """LLM-based assessment."""
        prompt = f"""You are {capabilities.role}.

Your capabilities:
- Tools: {', '.join(capabilities.tools)}
- Expertise: {capabilities.expertise}
- Goal: {capabilities.goal}
- Known limitations: {', '.join(capabilities.known_limitations) if capabilities.known_limitations else 'None'}

Task to evaluate: {task}

Assess whether you can perform this task:
- confidence: 0.0-1.0 (1.0 = very confident you can do it)
- reasoning: Explain why you can or cannot perform this task
- missing_capabilities: List what capabilities you're missing (if any)
- alternative_approach: If confidence < 0.7, suggest an alternative
- estimated_difficulty: Easy, Medium, Hard, or Impossible

Be honest about your limitations. It's better to admit you can't do something
than to fail at it.
"""

        try:
            response = self.llm.generate_structured(prompt, schema=CapabilityAssessment)
            return response
        except Exception as e:
            logger.warning(f"LLM assessment failed: {e}, falling back to rule-based")
            # Fallback to rule-based
            rule_based = RuleBasedAssessment()
            return rule_based.assess(task, capabilities)


class SelfAwareAgent:
    """
    Agent with meta-cognitive capabilities.

    Can assess its own ability to perform tasks and make intelligent
    decisions about execution vs delegation.
    """

    def __init__(
        self,
        capabilities: AgentCapabilities,
        assessment_strategy: Optional[SelfAssessmentStrategy] = None,
        confidence_threshold: float = 0.7,
        delegate_handler: Optional[Callable] = None,
    ):
        """
        Initialize self-aware agent.

        Args:
            capabilities: Agent's capabilities definition
            assessment_strategy: Strategy for self-assessment (defaults to rule-based)
            confidence_threshold: Minimum confidence to execute (0.7 default)
            delegate_handler: Optional callback for delegation
        """
        self.capabilities = capabilities
        self.assessment_strategy = assessment_strategy or RuleBasedAssessment()
        self.confidence_threshold = confidence_threshold
        self.delegate_handler = delegate_handler
        self.assessment_history: List[tuple] = []

    def can_perform(self, task: str) -> CapabilityAssessment:
        """
        Assess whether agent can perform the given task.

        Args:
            task: Task description

        Returns:
            CapabilityAssessment with confidence and details
        """
        assessment = self.assessment_strategy.assess(task, self.capabilities)

        # Store in history
        self.assessment_history.append((task, assessment))

        logger.info(
            f"Self-assessment for '{self.capabilities.role}': "
            f"confidence={assessment.confidence:.2f}, "
            f"difficulty={assessment.estimated_difficulty}"
        )

        return assessment

    async def execute_or_delegate(
        self, task: str, executor: Optional[Callable] = None, verbose: bool = True
    ) -> tuple[Any, CapabilityAssessment]:
        """
        Execute task if confident, otherwise delegate.

        Args:
            task: Task to perform
            executor: Optional executor function (async)
            verbose: Whether to log decisions

        Returns:
            Tuple of (result, assessment)
        """
        # Assess capability
        assessment = self.can_perform(task)

        if assessment.confidence >= self.confidence_threshold:
            # Confident - execute
            if verbose:
                logger.info(
                    f"✅ {self.capabilities.role} executing task "
                    f"(confidence: {assessment.confidence:.2%})"
                )

            if executor:
                result = await executor(task)
            else:
                result = f"Task executed by {self.capabilities.role}"

            return result, assessment
        else:
            # Not confident - delegate or request help
            if verbose:
                logger.warning(
                    f"⚠️ {self.capabilities.role} has low confidence "
                    f"({assessment.confidence:.2%}) for task: {task}"
                )
                logger.info(f"   Reason: {assessment.reasoning}")

                if assessment.missing_capabilities:
                    logger.info(
                        f"   Missing: {', '.join(assessment.missing_capabilities)}"
                    )

                if assessment.alternative_approach:
                    logger.info(f"   💡 Alternative: {assessment.alternative_approach}")

            # Attempt delegation
            if self.delegate_handler:
                if verbose:
                    logger.info("   🔄 Delegating task...")
                result = await self.delegate_handler(
                    task=task,
                    reason=assessment.reasoning,
                    missing_capabilities=assessment.missing_capabilities,
                )
            else:
                result = {
                    "status": "needs_delegation",
                    "assessment": assessment,
                    "message": f"{self.capabilities.role} cannot perform this task",
                }

            return result, assessment

    def execute_or_delegate_sync(
        self, task: str, executor: Optional[Callable] = None, verbose: bool = True
    ) -> tuple[Any, CapabilityAssessment]:
        """
        Synchronous version of execute_or_delegate.

        Args:
            task: Task to perform
            executor: Optional executor function (sync)
            verbose: Whether to log decisions

        Returns:
            Tuple of (result, assessment)
        """
        # Assess capability
        assessment = self.can_perform(task)

        if assessment.confidence >= self.confidence_threshold:
            # Confident - execute
            if verbose:
                logger.info(
                    f"✅ {self.capabilities.role} executing task "
                    f"(confidence: {assessment.confidence:.2%})"
                )

            if executor:
                result = executor(task)
            else:
                result = f"Task executed by {self.capabilities.role}"

            return result, assessment
        else:
            # Not confident - delegate or request help
            if verbose:
                logger.warning(
                    f"⚠️ {self.capabilities.role} has low confidence "
                    f"({assessment.confidence:.2%}) for task: {task}"
                )
                logger.info(f"   Reason: {assessment.reasoning}")

                if assessment.missing_capabilities:
                    logger.info(
                        f"   Missing: {', '.join(assessment.missing_capabilities)}"
                    )

                if assessment.alternative_approach:
                    logger.info(f"   💡 Alternative: {assessment.alternative_approach}")

            # Attempt delegation
            if self.delegate_handler:
                if verbose:
                    logger.info("   🔄 Delegating task...")
                # For sync, delegate_handler should be sync too
                result = self.delegate_handler(
                    task=task,
                    reason=assessment.reasoning,
                    missing_capabilities=assessment.missing_capabilities,
                )
            else:
                result = {
                    "status": "needs_delegation",
                    "assessment": assessment,
                    "message": f"{self.capabilities.role} cannot perform this task",
                }

            return result, assessment

    def get_assessment_statistics(self) -> dict:
        """
        Get statistics about past assessments.

        Returns:
            Dictionary with assessment statistics
        """
        if not self.assessment_history:
            return {
                "total_assessments": 0,
                "avg_confidence": 0.0,
                "tasks_within_capability": 0,
                "tasks_requiring_delegation": 0,
            }

        confidences = [a.confidence for _, a in self.assessment_history]
        avg_confidence = sum(confidences) / len(confidences)

        within_capability = sum(
            1
            for _, a in self.assessment_history
            if a.confidence >= self.confidence_threshold
        )

        return {
            "total_assessments": len(self.assessment_history),
            "avg_confidence": avg_confidence,
            "tasks_within_capability": within_capability,
            "tasks_requiring_delegation": len(self.assessment_history)
            - within_capability,
            "delegation_rate": (len(self.assessment_history) - within_capability)
            / len(self.assessment_history),
        }


def create_self_aware_agent(
    role: str,
    tools: List[str],
    expertise: str,
    goal: str,
    known_limitations: Optional[List[str]] = None,
    llm_provider: Optional[Any] = None,
    confidence_threshold: float = 0.7,
) -> SelfAwareAgent:
    """
    Factory function to create a self-aware agent.

    Args:
        role: Agent role name
        tools: List of available tools
        expertise: Agent expertise description
        goal: Agent goal
        known_limitations: Known limitations
        llm_provider: Optional LLM for advanced assessment
        confidence_threshold: Minimum confidence to execute

    Returns:
        SelfAwareAgent instance
    """
    capabilities = AgentCapabilities(
        role=role,
        tools=tools,
        expertise=expertise,
        goal=goal,
        known_limitations=known_limitations or [],
    )

    # Choose assessment strategy
    if llm_provider:
        strategy = LLMBasedAssessment(llm_provider)
    else:
        strategy = RuleBasedAssessment()

    return SelfAwareAgent(
        capabilities=capabilities,
        assessment_strategy=strategy,
        confidence_threshold=confidence_threshold,
    )
