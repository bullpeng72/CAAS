"""
Producer-Critic Pattern

Implements collaborative refinement where a Producer agent creates output
and a Critic agent reviews it, providing feedback for iterative improvement.

This pattern ensures high-quality outputs through peer review and refinement.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from caas_framework.agents.base import (
    AgentPhase,
    AgentWorkResult,
    BaseExpertAgent,
    ValidationIssue,
)
from caas_framework.plugins.llm.base import LLMPlugin
from caas_framework.validation.llm_judge import EvaluationResult, LLMJudge


class CriticRole(str, Enum):
    """Critic agent specialization roles"""

    DESIGN_REVIEWER = "design_reviewer"
    CODE_REVIEWER = "code_reviewer"
    ARCHITECTURE_REVIEWER = "architecture_reviewer"
    QUALITY_ASSURANCE = "quality_assurance"
    GENERAL_CRITIC = "general_critic"


@dataclass
class CriticReview:
    """Result of critic's review"""

    approved: bool
    overall_score: float  # 0.0 to 10.0
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    critical_issues: List[str] = field(default_factory=list)
    feedback: str = ""

    @property
    def needs_revision(self) -> bool:
        """Check if output needs revision"""
        return not self.approved or len(self.critical_issues) > 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "approved": self.approved,
            "overall_score": self.overall_score,
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "suggestions": self.suggestions,
            "critical_issues": self.critical_issues,
            "feedback": self.feedback,
        }


@dataclass
class ProducerCriticResult:
    """Result of Producer-Critic collaboration"""

    final_output: Dict[str, Any]
    iterations: int
    reviews: List[CriticReview]
    success: bool
    producer_work_results: List[AgentWorkResult] = field(default_factory=list)
    total_duration: float = 0.0

    @property
    def improvement_trajectory(self) -> List[float]:
        """Get score improvement over iterations"""
        return [review.overall_score for review in self.reviews]


class CriticAgent:
    """
    Critic Agent - Reviews and provides feedback on producer output

    The Critic specializes in identifying issues, assessing quality,
    and providing actionable feedback for improvement.

    Uses LLM Judge for evaluation with role-specific criteria.
    """

    def __init__(
        self,
        llm_plugin: LLMPlugin,
        role: CriticRole = CriticRole.GENERAL_CRITIC,
        approval_threshold: float = 7.0,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize Critic Agent.

        Args:
            llm_plugin: LLM plugin for critique generation
            role: Critic's specialization role
            approval_threshold: Minimum score for approval (0-10)
            logger: Optional logger
        """
        self.llm = llm_plugin
        self.role = role
        self.approval_threshold = approval_threshold
        self.logger = logger or logging.getLogger(__name__)

        # Use LLM Judge for evaluation
        self.judge = LLMJudge(
            llm_plugin=llm_plugin, approval_threshold=approval_threshold, logger=logger
        )

    async def review(
        self, output: Dict[str, Any], phase: AgentPhase, context: Optional[Dict[str, Any]] = None
    ) -> CriticReview:
        """
        Review producer's output and provide critique.

        Args:
            output: Producer's output to review
            phase: Current phase
            context: Optional context (requirement, previous outputs)

        Returns:
            CriticReview with feedback and approval decision
        """
        self.logger.info(f"🔍 Critic ({self.role.value}) reviewing {phase.name} output...")

        try:
            # Use LLM Judge for evaluation
            evaluation = await self.judge.evaluate_quality(
                output=output, phase=phase, context=context
            )

            # Convert LLM evaluation to CriticReview
            review = self._convert_evaluation_to_review(evaluation)

            if review.approved:
                self.logger.info(f"✅ Critic approved (score: {review.overall_score:.1f}/10.0)")
            else:
                self.logger.warning(
                    f"❌ Critic requests revision (score: {review.overall_score:.1f}/10.0, "
                    f"issues: {len(review.critical_issues)})"
                )

            return review

        except Exception as e:
            self.logger.error(f"Critic review failed: {e}")
            # Return rejection on error
            return CriticReview(
                approved=False,
                overall_score=0.0,
                critical_issues=[f"Review error: {str(e)}"],
                feedback="Review failed due to error",
            )

    def _convert_evaluation_to_review(self, evaluation: EvaluationResult) -> CriticReview:
        """Convert LLM Judge evaluation to CriticReview"""

        # Extract strengths (high scores)
        strengths = []
        weaknesses = []
        suggestions = []

        for dim_score in evaluation.dimension_scores:
            if dim_score.score >= 8.0:
                strengths.append(f"{dim_score.dimension.value.capitalize()}: {dim_score.reasoning}")
            elif dim_score.score < 7.0:
                weaknesses.append(
                    f"{dim_score.dimension.value.capitalize()}: {dim_score.reasoning}"
                )

            # Add suggestions from low-scoring dimensions
            if dim_score.suggestions:
                suggestions.extend(dim_score.suggestions)

        return CriticReview(
            approved=evaluation.approved,
            overall_score=evaluation.overall_score,
            strengths=strengths,
            weaknesses=weaknesses,
            suggestions=suggestions,
            critical_issues=evaluation.critical_issues,
            feedback=evaluation.feedback,
        )


class ProducerCriticPattern:
    """
    Producer-Critic Pattern Implementation

    Orchestrates collaboration between Producer and Critic agents:
    1. Producer creates initial output
    2. Critic reviews and provides feedback
    3. If not approved, Producer refines based on feedback
    4. Repeat until approved or max iterations reached

    This pattern ensures high-quality outputs through iterative refinement.
    """

    def __init__(
        self,
        max_iterations: int = 3,
        timeout_per_iteration: int = 120,  # 2 minutes per iteration
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize Producer-Critic Pattern.

        Args:
            max_iterations: Maximum refinement iterations
            timeout_per_iteration: Timeout per iteration (seconds)
            logger: Optional logger
        """
        self.max_iterations = max_iterations
        self.timeout_per_iteration = timeout_per_iteration
        self.logger = logger or logging.getLogger(__name__)

    async def produce_with_critique(
        self,
        producer: BaseExpertAgent,
        critic: CriticAgent,
        requirement: str,
        phase: AgentPhase,
        context: Optional[Dict[str, Any]] = None,
        previous_outputs: Optional[Dict[AgentPhase, Any]] = None,
    ) -> ProducerCriticResult:
        """
        Execute Producer-Critic collaboration.

        Process:
        1. Producer creates output
        2. Critic reviews output
        3. If approved: done
        4. If not approved: Producer refines based on critique
        5. Repeat steps 2-4 until approved or max iterations

        Args:
            producer: Producer agent (creates output)
            critic: Critic agent (reviews output)
            requirement: Task requirement
            phase: Current phase
            context: Optional context
            previous_outputs: Previous phase outputs

        Returns:
            ProducerCriticResult with final output and review history
        """
        import time

        start_time = time.time()

        reviews: List[CriticReview] = []
        work_results: List[AgentWorkResult] = []
        output = None

        self.logger.info(
            f"🤝 Starting Producer-Critic collaboration for {phase.name} "
            f"(max {self.max_iterations} iterations)"
        )

        for iteration in range(self.max_iterations):
            try:
                # PRODUCER: Create or refine output
                if iteration == 0:
                    # Initial production
                    self.logger.info("📝 Producer creating initial output (iteration 1)...")
                    work_result = await asyncio.wait_for(
                        producer.work(
                            requirement=requirement,
                            context=context,
                            previous_outputs=previous_outputs or {},
                        ),
                        timeout=self.timeout_per_iteration,
                    )
                else:
                    # Refinement based on critique
                    previous_review = reviews[-1]
                    validation_issues = self._convert_review_to_issues(previous_review)

                    self.logger.info(
                        f"🔄 Producer refining based on critique "
                        f"(iteration {iteration + 1}/{self.max_iterations})..."
                    )

                    work_result = await asyncio.wait_for(
                        producer.refine(
                            original_output=output,
                            validation_issues=validation_issues,
                            context=context,
                            max_iterations=1,
                        ),
                        timeout=self.timeout_per_iteration,
                    )

                # Check if production succeeded
                if not work_result.success:
                    self.logger.error(f"❌ Producer failed: {work_result.errors}")
                    break

                output = work_result.output
                work_results.append(work_result)

                # CRITIC: Review output
                self.logger.info(f"🔍 Critic reviewing output (iteration {iteration + 1})...")
                review = await asyncio.wait_for(
                    critic.review(
                        output=output,
                        phase=phase,
                        context={"requirement": requirement, **(context or {})},
                    ),
                    timeout=self.timeout_per_iteration,
                )

                reviews.append(review)

                # Check if approved
                if review.approved:
                    self.logger.info(
                        f"✅ Critic approved after {iteration + 1} iteration(s) "
                        f"(score: {review.overall_score:.1f}/10.0)"
                    )
                    break

                # Check if max iterations reached
                if iteration == self.max_iterations - 1:
                    self.logger.warning(
                        f"⚠️ Max iterations ({self.max_iterations}) reached without approval "
                        f"(final score: {review.overall_score:.1f}/10.0)"
                    )

            except asyncio.TimeoutError:
                self.logger.error(
                    f"⏱️ Iteration {iteration + 1} timed out " f"after {self.timeout_per_iteration}s"
                )
                break

            except Exception as e:
                self.logger.exception(f"❌ Iteration {iteration + 1} failed: {e}")
                break

        # Calculate total duration
        total_duration = time.time() - start_time

        # Determine success
        success = len(reviews) > 0 and reviews[-1].approved

        result = ProducerCriticResult(
            final_output=output or {},
            iterations=len(reviews),
            reviews=reviews,
            success=success,
            producer_work_results=work_results,
            total_duration=total_duration,
        )

        # Log summary
        if success:
            self.logger.info(
                f"🎉 Producer-Critic collaboration successful "
                f"({result.iterations} iterations, {total_duration:.1f}s)"
            )
        else:
            self.logger.warning(
                f"⚠️ Producer-Critic collaboration ended without approval "
                f"({result.iterations} iterations, {total_duration:.1f}s)"
            )

        return result

    def _convert_review_to_issues(self, review: CriticReview) -> List[ValidationIssue]:
        """Convert critic review to validation issues for refinement"""
        issues = []

        # Add critical issues
        for critical in review.critical_issues:
            issues.append(
                ValidationIssue(
                    issue_type="critical", severity="high", message=critical, field="overall"
                )
            )

        # Add weaknesses
        for weakness in review.weaknesses:
            issues.append(
                ValidationIssue(
                    issue_type="weakness", severity="medium", message=weakness, field="quality"
                )
            )

        # Add suggestions
        for suggestion in review.suggestions:
            issues.append(
                ValidationIssue(
                    issue_type="suggestion",
                    severity="low",
                    message=suggestion,
                    field="improvement",
                    suggested_fix=suggestion,
                )
            )

        return issues


# ==================== Convenience Functions ====================


async def collaborate_with_critic(
    producer: BaseExpertAgent,
    critic_llm: LLMPlugin,
    requirement: str,
    phase: AgentPhase,
    context: Optional[Dict[str, Any]] = None,
    previous_outputs: Optional[Dict[AgentPhase, Any]] = None,
    max_iterations: int = 3,
    approval_threshold: float = 7.0,
) -> ProducerCriticResult:
    """
    Convenience function for Producer-Critic collaboration.

    Args:
        producer: Producer agent
        critic_llm: LLM plugin for critic
        requirement: Task requirement
        phase: Current phase
        context: Optional context
        previous_outputs: Previous phase outputs
        max_iterations: Max refinement iterations
        approval_threshold: Critic approval threshold

    Returns:
        ProducerCriticResult
    """
    # Create critic agent
    critic = CriticAgent(
        llm_plugin=critic_llm, role=CriticRole.GENERAL_CRITIC, approval_threshold=approval_threshold
    )

    # Create pattern orchestrator
    pattern = ProducerCriticPattern(max_iterations=max_iterations, timeout_per_iteration=120)

    # Execute collaboration
    return await pattern.produce_with_critique(
        producer=producer,
        critic=critic,
        requirement=requirement,
        phase=phase,
        context=context,
        previous_outputs=previous_outputs,
    )
