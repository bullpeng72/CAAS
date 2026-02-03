"""
Critic Agent Pattern (Producer-Critic)

Implements the Producer-Critic pattern where a producer agent generates output
and a critic agent reviews it iteratively until approved or max iterations reached.
"""

from dataclasses import dataclass, field
from typing import Any, List, Protocol, Tuple

from pydantic import BaseModel, Field

from caas_framework.utils.logger import get_logger

logger = get_logger()


@dataclass
class Critique:
    """Represents a critique from the critic agent."""

    approved: bool
    score: int  # 1-10 rating
    feedback: str
    suggestions: List[str] = field(default_factory=list)
    issues: List[str] = field(default_factory=list)
    iteration: int = 0


class CritiqueResponse(BaseModel):
    """Pydantic model for structured critique responses."""

    approved: bool = Field(description="Whether the output is approved")
    score: int = Field(ge=1, le=10, description="Quality score from 1 to 10")
    feedback: str = Field(description="Overall feedback on the output")
    suggestions: List[str] = Field(
        default_factory=list, description="Specific suggestions for improvement"
    )
    issues: List[str] = Field(default_factory=list, description="Issues or problems found")


class ProducerAgent(Protocol):
    """Protocol for producer agents that generate output."""

    async def execute(self, task: str) -> Any:
        """Execute the task and produce initial output."""
        ...

    async def refine(self, task: str, previous_output: Any, critique: Critique) -> Any:
        """Refine the previous output based on critique."""
        ...


class CriticAgent(Protocol):
    """Protocol for critic agents that review output."""

    async def review(self, output: Any) -> Critique:
        """Review the output and provide critique."""
        ...


class CriticAgentPattern:
    """
    Producer-Critic pattern implementation.

    A producer agent generates output, which is then reviewed by a critic agent.
    The process iterates until the critic approves or max iterations reached.
    """

    def __init__(
        self,
        producer: ProducerAgent,
        critic: CriticAgent,
        max_iterations: int = 3,
        min_score_threshold: int = 7,
    ):
        """
        Initialize the critic pattern.

        Args:
            producer: Agent that produces output
            critic: Agent that critiques output
            max_iterations: Maximum refinement iterations
            min_score_threshold: Minimum score for auto-approval (1-10)
        """
        self.producer = producer
        self.critic = critic
        self.max_iterations = max_iterations
        self.min_score_threshold = min_score_threshold

    async def produce_with_critique(
        self, task: str, verbose: bool = True
    ) -> Tuple[Any, List[Critique]]:
        """
        Execute producer-critic loop.

        Producer generates output -> Critic reviews -> Producer refines -> repeat

        Args:
            task: The task description
            verbose: Whether to log progress

        Returns:
            Tuple of (final_output, list_of_critiques)
        """
        critiques = []
        output = None

        for iteration in range(self.max_iterations):
            if verbose:
                logger.info(f"\n{'='*70}")
                logger.info(f"🔄 Iteration {iteration + 1}/{self.max_iterations}")
                logger.info(f"{'='*70}")

            # Producer: Generate or refine output
            if iteration == 0:
                if verbose:
                    logger.info("📝 Producer generating initial output...")
                output = await self.producer.execute(task)
            else:
                if verbose:
                    logger.info("📝 Producer refining based on critique...")
                output = await self.producer.refine(
                    task=task, previous_output=output, critique=critiques[-1]
                )

            # Critic: Review output
            if verbose:
                logger.info("🔍 Critic reviewing output...")

            critique = await self.critic.review(output)
            critique.iteration = iteration + 1
            critiques.append(critique)

            # Log critique results
            if verbose:
                self._log_critique(critique, iteration + 1)

            # Check if approved
            if critique.approved or critique.score >= self.min_score_threshold:
                if verbose:
                    logger.info(f"\n✅ Output approved after {iteration + 1} iteration(s)")
                break

            # Check if max iterations reached
            if iteration == self.max_iterations - 1:
                if verbose:
                    logger.warning(
                        f"\n⚠️ Max iterations ({self.max_iterations}) reached. "
                        f"Final score: {critique.score}/10"
                    )

        return output, critiques

    def _log_critique(self, critique: Critique, iteration: int):
        """Log critique details."""
        logger.info(f"\n📊 Critique Results (Iteration {iteration}):")
        logger.info(f"   Score: {critique.score}/10")
        logger.info(f"   Approved: {'✅' if critique.approved else '❌'}")
        logger.info(f"   Feedback: {critique.feedback}")

        if critique.issues:
            logger.info(f"\n   Issues found:")
            for issue in critique.issues:
                logger.info(f"      • {issue}")

        if critique.suggestions:
            logger.info(f"\n   Suggestions:")
            for suggestion in critique.suggestions:
                logger.info(f"      • {suggestion}")

    def get_improvement_summary(self, critiques: List[Critique]) -> dict:
        """
        Generate summary of improvement across iterations.

        Args:
            critiques: List of critiques from iterations

        Returns:
            Dictionary with improvement statistics
        """
        if not critiques:
            return {
                "iterations": 0,
                "initial_score": 0,
                "final_score": 0,
                "improvement": 0,
                "approved": False,
            }

        initial_score = critiques[0].score
        final_score = critiques[-1].score
        improvement = final_score - initial_score

        return {
            "iterations": len(critiques),
            "initial_score": initial_score,
            "final_score": final_score,
            "improvement": improvement,
            "improvement_percent": (improvement / initial_score * 100) if initial_score > 0 else 0,
            "approved": critiques[-1].approved,
            "total_issues_found": sum(len(c.issues) for c in critiques),
            "total_suggestions": sum(len(c.suggestions) for c in critiques),
        }


class SimpleSyncCriticPattern:
    """
    Synchronous version of CriticAgentPattern for non-async environments.

    Same functionality as CriticAgentPattern but uses sync methods.
    """

    def __init__(self, producer, critic, max_iterations: int = 3, min_score_threshold: int = 7):
        """Initialize sync critic pattern."""
        self.producer = producer
        self.critic = critic
        self.max_iterations = max_iterations
        self.min_score_threshold = min_score_threshold

    def produce_with_critique(self, task: str, verbose: bool = True) -> Tuple[Any, List[Critique]]:
        """
        Execute producer-critic loop synchronously.

        Args:
            task: The task description
            verbose: Whether to log progress

        Returns:
            Tuple of (final_output, list_of_critiques)
        """
        critiques = []
        output = None

        for iteration in range(self.max_iterations):
            if verbose:
                logger.info(f"\n{'='*70}")
                logger.info(f"🔄 Iteration {iteration + 1}/{self.max_iterations}")
                logger.info(f"{'='*70}")

            # Producer: Generate or refine output
            if iteration == 0:
                if verbose:
                    logger.info("📝 Producer generating initial output...")
                output = self.producer.execute(task)
            else:
                if verbose:
                    logger.info("📝 Producer refining based on critique...")
                output = self.producer.refine(
                    task=task, previous_output=output, critique=critiques[-1]
                )

            # Critic: Review output
            if verbose:
                logger.info("🔍 Critic reviewing output...")

            critique = self.critic.review(output)
            critique.iteration = iteration + 1
            critiques.append(critique)

            # Log critique results
            if verbose:
                self._log_critique(critique, iteration + 1)

            # Check if approved
            if critique.approved or critique.score >= self.min_score_threshold:
                if verbose:
                    logger.info(f"\n✅ Output approved after {iteration + 1} iteration(s)")
                break

            # Check if max iterations reached
            if iteration == self.max_iterations - 1:
                if verbose:
                    logger.warning(
                        f"\n⚠️ Max iterations ({self.max_iterations}) reached. "
                        f"Final score: {critique.score}/10"
                    )

        return output, critiques

    def _log_critique(self, critique: Critique, iteration: int):
        """Log critique details."""
        logger.info(f"\n📊 Critique Results (Iteration {iteration}):")
        logger.info(f"   Score: {critique.score}/10")
        logger.info(f"   Approved: {'✅' if critique.approved else '❌'}")
        logger.info(f"   Feedback: {critique.feedback}")

        if critique.issues:
            logger.info(f"\n   Issues found:")
            for issue in critique.issues:
                logger.info(f"      • {issue}")

        if critique.suggestions:
            logger.info(f"\n   Suggestions:")
            for suggestion in critique.suggestions:
                logger.info(f"      • {suggestion}")

    def get_improvement_summary(self, critiques: List[Critique]) -> dict:
        """Generate summary of improvement across iterations."""
        if not critiques:
            return {
                "iterations": 0,
                "initial_score": 0,
                "final_score": 0,
                "improvement": 0,
                "approved": False,
            }

        initial_score = critiques[0].score
        final_score = critiques[-1].score
        improvement = final_score - initial_score

        return {
            "iterations": len(critiques),
            "initial_score": initial_score,
            "final_score": final_score,
            "improvement": improvement,
            "improvement_percent": (improvement / initial_score * 100) if initial_score > 0 else 0,
            "approved": critiques[-1].approved,
            "total_issues_found": sum(len(c.issues) for c in critiques),
            "total_suggestions": sum(len(c.suggestions) for c in critiques),
        }


def create_critic_pattern(
    producer, critic, max_iterations: int = 3, min_score_threshold: int = 7, async_mode: bool = True
) -> Any:
    """
    Factory function to create appropriate critic pattern.

    Args:
        producer: Producer agent
        critic: Critic agent
        max_iterations: Maximum refinement iterations
        min_score_threshold: Minimum score for auto-approval
        async_mode: Use async version if True

    Returns:
        CriticAgentPattern or SimpleSyncCriticPattern instance
    """
    if async_mode:
        return CriticAgentPattern(
            producer=producer,
            critic=critic,
            max_iterations=max_iterations,
            min_score_threshold=min_score_threshold,
        )
    else:
        return SimpleSyncCriticPattern(
            producer=producer,
            critic=critic,
            max_iterations=max_iterations,
            min_score_threshold=min_score_threshold,
        )
