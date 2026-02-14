"""
Iteration Controller - Main Orchestrator

Coordinates all 3 iteration levels:
- Macro: Epic-level
- Micro: Story-level
- Nano: TDD cycle

Part of CAAS-E Week 6 implementation (Task 6.2).
"""

from typing import Optional, Dict, Any, List
from pathlib import Path
import logging

from caas_framework.models.iteration import (
    IterationConfig,
    IterationLevel,
    IterationResult,
    IterationMetrics,
    IterationStatus,
    FailureReason,
)
from caas_framework.iteration.nano_iterator import NanoIterator
from caas_framework.iteration.micro_iterator import MicroIterator
from caas_framework.iteration.macro_iterator import MacroIterator

logger = logging.getLogger(__name__)


class IterationController:
    """
    Main controller for 3-level iteration system.

    Provides unified interface for:
    - Nano iterations (TDD cycles)
    - Micro iterations (Story-level retry)
    - Macro iterations (Epic-level coordination)
    """

    def __init__(
        self,
        config: Optional[IterationConfig] = None,
        checkpoint_dir: Optional[Path] = None,
    ):
        """
        Initialize iteration controller.

        Args:
            config: Iteration configuration
            checkpoint_dir: Directory for checkpoints
        """
        self.config = config or IterationConfig()
        self.checkpoint_dir = checkpoint_dir or Path("./checkpoints")

        # Initialize iterators
        self.nano_iterator = NanoIterator(
            max_retries=self.config.max_nano_retries,
        )

        self.micro_iterator = MicroIterator(
            max_retries=self.config.max_micro_retries,
            enable_checkpoint=self.config.enable_checkpoint,
            checkpoint_dir=self.checkpoint_dir,
        )

        self.macro_iterator = MacroIterator(
            max_retries=self.config.max_macro_retries,
        )

        # Metrics tracking
        self.metrics = {
            IterationLevel.NANO: [],
            IterationLevel.MICRO: [],
            IterationLevel.MACRO: [],
        }

        self.logger = logging.getLogger(self.__class__.__name__)

    def execute_nano(
        self,
        test_file: Path,
        implementation_file: Path,
        iteration_id: Optional[str] = None,
    ) -> IterationResult:
        """
        Execute nano-level iteration (TDD cycle).

        Args:
            test_file: Test file path
            implementation_file: Implementation file path
            iteration_id: Optional iteration ID

        Returns:
            IterationResult
        """
        self.logger.info(f"Executing NANO iteration: {test_file.name}")

        result = self.nano_iterator.execute(
            test_file=test_file,
            implementation_file=implementation_file,
            iteration_id=iteration_id,
        )

        # Track metrics
        self.metrics[IterationLevel.NANO].append(result)

        return result

    def execute_micro(
        self,
        story_id: str,
        story_name: str,
        phase: str,
        phase_function: callable,
        iteration_id: Optional[str] = None,
        **kwargs,
    ) -> IterationResult:
        """
        Execute micro-level iteration (Story retry).

        Args:
            story_id: Story identifier
            story_name: Story name
            phase: Phase name
            phase_function: Function to execute
            iteration_id: Optional iteration ID
            **kwargs: Phase function arguments

        Returns:
            IterationResult
        """
        self.logger.info(f"Executing MICRO iteration: {story_name} (Phase: {phase})")

        result = self.micro_iterator.execute(
            story_id=story_id,
            story_name=story_name,
            phase=phase,
            phase_function=phase_function,
            iteration_id=iteration_id,
            **kwargs,
        )

        # Track metrics
        self.metrics[IterationLevel.MICRO].append(result)

        return result

    def execute_macro(
        self,
        epic_id: str,
        epic_name: str,
        stories: List[Dict[str, Any]],
        story_executor: callable,
        iteration_id: Optional[str] = None,
    ) -> IterationResult:
        """
        Execute macro-level iteration (Epic coordination).

        Args:
            epic_id: Epic identifier
            epic_name: Epic name
            stories: List of stories
            story_executor: Function to execute a story
            iteration_id: Optional iteration ID

        Returns:
            IterationResult
        """
        self.logger.info(f"Executing MACRO iteration: {epic_name} ({len(stories)} stories)")

        result = self.macro_iterator.execute(
            epic_id=epic_id,
            epic_name=epic_name,
            stories=stories,
            story_executor=story_executor,
            iteration_id=iteration_id,
        )

        # Track metrics
        self.metrics[IterationLevel.MACRO].append(result)

        return result

    def get_metrics(self, level: Optional[IterationLevel] = None) -> IterationMetrics:
        """
        Get iteration metrics.

        Args:
            level: Specific level (None for all)

        Returns:
            IterationMetrics
        """
        if level:
            results = self.metrics[level]
        else:
            # Aggregate all levels
            results = []
            for level_results in self.metrics.values():
                results.extend(level_results)

        if not results:
            return IterationMetrics(
                total_iterations=0,
                successful_iterations=0,
                failed_iterations=0,
                average_attempts=0.0,
                total_retry_time_seconds=0.0,
                success_rate=0.0,
            )

        # Calculate metrics
        total = len(results)
        successful = sum(1 for r in results if r.successful)
        failed = total - successful

        total_attempts = sum(r.total_attempts for r in results)
        avg_attempts = total_attempts / total if total > 0 else 0.0

        total_time = sum(
            r.final_attempt.duration_seconds
            for r in results
            if r.final_attempt
        )

        success_rate = successful / total if total > 0 else 0.0

        # Find most common failure
        failure_reasons = [
            r.final_attempt.failure_reason
            for r in results
            if r.final_attempt and r.final_attempt.failure_reason
        ]

        most_common = None
        if failure_reasons:
            from collections import Counter
            counter = Counter(failure_reasons)
            most_common = counter.most_common(1)[0][0]

        return IterationMetrics(
            total_iterations=total,
            successful_iterations=successful,
            failed_iterations=failed,
            average_attempts=avg_attempts,
            total_retry_time_seconds=total_time,
            success_rate=success_rate,
            most_common_failure=most_common,
        )

    def reset_metrics(self):
        """Reset all metrics"""
        for level in IterationLevel:
            self.metrics[level].clear()

        self.logger.info("Metrics reset")

    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary of all iteration levels.

        Returns:
            Dictionary with metrics for each level
        """
        summary = {}

        for level in IterationLevel:
            metrics = self.get_metrics(level)
            summary[level.value] = {
                "total": metrics.total_iterations,
                "successful": metrics.successful_iterations,
                "failed": metrics.failed_iterations,
                "success_rate": f"{metrics.success_rate * 100:.1f}%",
                "avg_attempts": f"{metrics.average_attempts:.1f}",
            }

        # Overall statistics
        overall_metrics = self.get_metrics()
        summary["overall"] = {
            "total_iterations": overall_metrics.total_iterations,
            "success_rate": f"{overall_metrics.success_rate * 100:.1f}%",
            "total_retry_time_seconds": f"{overall_metrics.total_retry_time_seconds:.1f}",
            "most_common_failure": overall_metrics.most_common_failure.value if overall_metrics.most_common_failure else None,
        }

        return summary
