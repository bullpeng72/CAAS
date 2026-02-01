"""
Base Expert Agent

Abstract base class for all expert agents in the BMAD pipeline.
Provides common functionality for agent collaboration and feedback loops.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import traceback

from caas_framework.models.specifications import ConcretizedRequirement
from caas_framework.models.validation import ValidationIssue
from caas_framework.plugins.llm.base import LLMPlugin
from caas_framework.utils import ResponseParser
from caas_framework.config.settings import LLMConstants


class AgentPhase(str, Enum):
    """Agent responsibility phases"""
    DISCOVERY = "discovery"
    ARCHITECTURE = "architecture"
    DESIGN = "design"
    DEVELOPMENT = "development"
    DELIVERY = "delivery"
    QUALITY_ASSURANCE = "quality_assurance"


@dataclass
class AgentWorkResult:
    """Result of agent work"""
    success: bool
    output: Any
    phase: AgentPhase
    agent_name: str
    duration: float = 0.0
    iterations: int = 1
    feedback_applied: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseExpertAgent(ABC):
    """
    Base Expert Agent

    Abstract base class for specialized agents in BMAD pipeline.
    Each agent is responsible for a specific phase and can:
    - Work on its assigned phase
    - Receive feedback from validation
    - Refine its output based on feedback
    - Collaborate with other agents through context
    """

    def __init__(
        self,
        llm_plugin: LLMPlugin,
        golden_data: Optional[ConcretizedRequirement] = None,
        phase: AgentPhase = AgentPhase.DISCOVERY
    ):
        """
        Initialize expert agent.

        Args:
            llm_plugin: LLM plugin for generation
            golden_data: Golden Data as reference
            phase: Agent's responsibility phase
        """
        self.llm = llm_plugin
        self.golden_data = golden_data
        self.phase = phase
        self.work_history: List[AgentWorkResult] = []

    @property
    @abstractmethod
    def agent_name(self) -> str:
        """Agent's name/identifier"""

    @property
    @abstractmethod
    def agent_role(self) -> str:
        """Agent's role description"""

    @property
    @abstractmethod
    def agent_expertise(self) -> List[str]:
        """Agent's areas of expertise"""

    async def work(
        self,
        requirement: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        previous_outputs: Optional[Dict[AgentPhase, Any]] = None
    ) -> AgentWorkResult:
        """
        Execute agent's primary work.

        Args:
            requirement: Original requirement text
            context: Additional context from other agents
            previous_outputs: Outputs from previous phases

        Returns:
            AgentWorkResult with output and metadata
        """
        start_time = datetime.now()

        try:
            # Perform agent-specific work
            output = await self._do_work(requirement, context, previous_outputs)

            duration = (datetime.now() - start_time).total_seconds()

            result = AgentWorkResult(
                success=True,
                output=output,
                phase=self.phase,
                agent_name=self.agent_name,
                duration=duration,
                iterations=1
            )

            self.work_history.append(result)
            return result

        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()

            # Capture full stack trace for debugging
            error_msg = f"{str(e)}\n{traceback.format_exc()}"

            result = AgentWorkResult(
                success=False,
                output=None,
                phase=self.phase,
                agent_name=self.agent_name,
                duration=duration,
                errors=[error_msg]
            )

            self.work_history.append(result)
            return result

    @abstractmethod
    async def _do_work(
        self,
        requirement: Optional[str],
        context: Optional[Dict[str, Any]],
        previous_outputs: Optional[Dict[AgentPhase, Any]]
    ) -> Any:
        """
        Agent-specific work implementation.

        This method must be implemented by each expert agent.

        Args:
            requirement: Original requirement
            context: Context from collaboration
            previous_outputs: Previous phase outputs

        Returns:
            Agent's output (structure depends on agent type)
        """

    async def refine(
        self,
        original_output: Any,
        validation_issues: List[ValidationIssue],
        context: Optional[Dict[str, Any]] = None,
        max_iterations: int = 3
    ) -> AgentWorkResult:
        """
        Refine output based on validation feedback.

        This is the core of the feedback loop mechanism.
        Agent receives validation issues and improves its output.

        Args:
            original_output: Original output to refine
            validation_issues: Issues identified by validation
            context: Additional context
            max_iterations: Maximum refinement iterations

        Returns:
            AgentWorkResult with refined output
        """
        start_time = datetime.now()
        current_output = original_output
        feedback_applied = []

        for iteration in range(max_iterations):
            # Filter issues that still apply
            remaining_issues = await self._filter_resolved_issues(
                current_output,
                validation_issues
            )

            if not remaining_issues:
                # All issues resolved
                break

            # Attempt refinement
            try:
                refined_output = await self._refine_implementation(
                    current_output,
                    remaining_issues,
                    context,
                    iteration + 1
                )

                feedback_applied.append(
                    f"Iteration {iteration + 1}: Addressed {len(remaining_issues)} issues"
                )

                current_output = refined_output

            except Exception as e:
                result = AgentWorkResult(
                    success=False,
                    output=current_output,
                    phase=self.phase,
                    agent_name=self.agent_name,
                    duration=(datetime.now() - start_time).total_seconds(),
                    iterations=iteration + 1,
                    feedback_applied=feedback_applied,
                    errors=[f"Refinement failed: {str(e)}"]
                )
                self.work_history.append(result)
                return result

        duration = (datetime.now() - start_time).total_seconds()

        result = AgentWorkResult(
            success=True,
            output=current_output,
            phase=self.phase,
            agent_name=self.agent_name,
            duration=duration,
            iterations=len(feedback_applied),
            feedback_applied=feedback_applied
        )

        self.work_history.append(result)
        return result

    async def _filter_resolved_issues(
        self,
        current_output: Any,
        issues: List[ValidationIssue]
    ) -> List[ValidationIssue]:
        """
        Filter out issues that have been resolved.

        Default implementation returns all issues.
        Subclasses can override for smarter filtering.
        """
        return issues

    @abstractmethod
    async def _refine_implementation(
        self,
        output: Any,
        issues: List[ValidationIssue],
        context: Optional[Dict[str, Any]],
        iteration: int
    ) -> Any:
        """
        Agent-specific refinement implementation.

        This method must be implemented by each expert agent.

        Args:
            output: Current output to refine
            issues: Validation issues to address
            context: Additional context
            iteration: Current iteration number

        Returns:
            Refined output
        """

    def _build_context_summary(
        self,
        context: Optional[Dict[str, Any]],
        previous_outputs: Optional[Dict[AgentPhase, Any]]
    ) -> str:
        """
        Build context summary for LLM prompts.

        Args:
            context: Context dictionary
            previous_outputs: Previous phase outputs

        Returns:
            Formatted context string
        """
        lines = []

        if self.golden_data:
            lines.append("## Golden Data (Reference)")
            lines.append(f"Domain: {self.golden_data.domain}")
            lines.append(f"Project: {self.golden_data.project_name}")

            features = self.golden_data.features if self.golden_data.features else []
            lines.append(f"Features: {len(features)}")

            for feature in features[:3]:  # Top 3
                lines.append(f"  - {feature.name}: {feature.description[:100]}")

        if previous_outputs:
            lines.append("\n## Previous Phase Outputs")
            for phase, output in previous_outputs.items():
                lines.append(f"{phase.value}: {type(output).__name__}")

        if context:
            lines.append("\n## Additional Context")
            for key, value in context.items():
                lines.append(f"{key}: {str(value)[:100]}")

        return "\n".join(lines)

    def _format_validation_issues(
        self,
        issues: List[ValidationIssue]
    ) -> str:
        """
        Format validation issues for LLM prompts.

        Args:
            issues: List of validation issues

        Returns:
            Formatted issues string
        """
        if not issues:
            return "No issues identified."

        lines = ["## Validation Issues to Address"]

        for i, issue in enumerate(issues, 1):
            lines.append(f"\n{i}. [{issue.severity.upper()}] {issue.issue_type}")
            lines.append(f"   Message: {issue.message}")
            if issue.field:
                lines.append(f"   Field: {issue.field}")
            if issue.suggested_fix:
                lines.append(f"   Suggested fix: {issue.suggested_fix}")

        return "\n".join(lines)

    def get_work_summary(self) -> Dict[str, Any]:
        """
        Get summary of agent's work history.

        Returns:
            Summary dictionary
        """
        total_iterations = sum(r.iterations for r in self.work_history)
        total_duration = sum(r.duration for r in self.work_history)
        success_rate = (
            sum(1 for r in self.work_history if r.success) / len(self.work_history)
            if self.work_history else 0.0
        )

        return {
            "agent_name": self.agent_name,
            "phase": self.phase.value,
            "total_work_sessions": len(self.work_history),
            "total_iterations": total_iterations,
            "total_duration": total_duration,
            "success_rate": success_rate,
            "expertise": self.agent_expertise
        }

    # ==================== LLM Helper Methods ====================

    async def _invoke_llm_structured(
        self,
        prompt: str,
        expected_fields: List[str],
        fallback_factory: Callable[[], Dict[str, Any]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Unified LLM invocation with structured parsing.

        Consolidates the repeated pattern of:
        1. Call LLM with JSON format
        2. Parse response
        3. Validate fields
        4. Return with fallback

        Args:
            prompt: Prompt string to send to LLM
            expected_fields: List of expected field names in response
            fallback_factory: Factory function to create fallback response
            temperature: Optional temperature (uses default if None)
            max_tokens: Optional max tokens limit

        Returns:
            Parsed structured response as dict

        Example:
            >>> result = await self._invoke_llm_structured(
            ...     prompt=prompt,
            ...     expected_fields=['functional_requirements', 'constraints'],
            ...     fallback_factory=self._create_fallback_analysis,
            ...     temperature=0.7
            ... )
        """
        # Use default temperature if not provided
        temp = temperature if temperature is not None else self._get_default_temperature()

        # Prepare invocation kwargs
        invoke_kwargs = {
            "messages": [{"role": "user", "content": prompt}],
            "response_format": LLMConstants.RESPONSE_FORMAT_JSON,
            "temperature": temp
        }

        if max_tokens:
            invoke_kwargs["max_tokens"] = max_tokens

        # Call LLM
        response = await self.llm.ainvoke(**invoke_kwargs)

        # Parse response with fallback
        result = ResponseParser.parse_structured_response(
            response,
            expected_fields=expected_fields,
            fallback_factory=fallback_factory
        )

        return result

    def _get_default_temperature(self) -> float:
        """
        Get default temperature for this agent's phase.

        Subclasses can override to customize temperature per phase.

        Returns:
            Default temperature value

        Default mapping:
        - DISCOVERY: TEMPERATURE_PRECISE (0.3) - Accurate requirements
        - ARCHITECTURE: TEMPERATURE_CREATIVE (0.7) - Design creativity
        - DESIGN: TEMPERATURE_BALANCED (0.5) - Balance
        - DELIVERY: TEMPERATURE_PRECISE (0.3) - Code accuracy
        - QUALITY_ASSURANCE: TEMPERATURE_PRECISE (0.3) - Rigorous QA
        """
        phase_temperatures = {
            AgentPhase.DISCOVERY: LLMConstants.TEMPERATURE_PRECISE,
            AgentPhase.ARCHITECTURE: LLMConstants.TEMPERATURE_CREATIVE,
            AgentPhase.DESIGN: LLMConstants.TEMPERATURE_BALANCED,
            AgentPhase.DELIVERY: LLMConstants.TEMPERATURE_PRECISE,
            AgentPhase.QUALITY_ASSURANCE: LLMConstants.TEMPERATURE_PRECISE,
            AgentPhase.DEVELOPMENT: LLMConstants.TEMPERATURE_BALANCED
        }

        return phase_temperatures.get(self.phase, LLMConstants.TEMPERATURE_BALANCED)

    @staticmethod
    def _merge_outputs(
        refined: Dict[str, Any],
        original: Dict[str, Any],
        exclude_keys: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Merge refined output with original to preserve missing keys.

        Consolidates the repeated pattern of merging outputs to avoid data loss.

        Args:
            refined: New refined output
            original: Original output
            exclude_keys: Optional list of keys to exclude from merge

        Returns:
            Merged dictionary

        Example:
            >>> refined = {"field1": "new_value"}
            >>> original = {"field1": "old_value", "field2": "preserved"}
            >>> result = BaseExpertAgent._merge_outputs(refined, original)
            >>> # result = {"field1": "new_value", "field2": "preserved"}
        """
        exclude_set = set(exclude_keys) if exclude_keys else set()

        # Copy refined output
        merged = refined.copy()

        # Add missing keys from original
        for key, value in original.items():
            if key not in merged and key not in exclude_set:
                merged[key] = value

        return merged
