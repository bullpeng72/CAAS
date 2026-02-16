"""
Micro Iterator - Story-level Iteration

Implements story-level retry logic:
- Phase-level rollback
- Incremental fixes
- State preservation

Part of CAAS-E Week 6 implementation (Task 6.2).
"""

import time
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging

from caas_framework.models.iteration import (
    MicroIteration,
    IterationAttempt,
    IterationStatus,
    FailureReason,
    IterationResult,
    IterationLevel,
)
from caas_framework.iteration.nano_iterator import NanoIterator

logger = logging.getLogger(__name__)


class MicroIterator:
    """
    Micro-level iterator for story-level retry.

    Handles:
    - Phase execution with retry
    - Checkpoint/rollback
    - Incremental error fixing
    - State preservation
    """

    def __init__(
        self,
        max_retries: int = 3,
        enable_checkpoint: bool = True,
        checkpoint_dir: Optional[Path] = None,
    ):
        """
        Initialize micro iterator.

        Args:
            max_retries: Maximum retry attempts for story
            enable_checkpoint: Enable checkpointing
            checkpoint_dir: Directory for checkpoint files
        """
        self.max_retries = max_retries
        self.enable_checkpoint = enable_checkpoint
        self.checkpoint_dir = checkpoint_dir or Path("./checkpoints")
        self.nano_iterator = NanoIterator()
        self.logger = logging.getLogger(self.__class__.__name__)

    def execute(
        self,
        story_id: str,
        story_name: str,
        phase: str,
        phase_function: callable,
        iteration_id: Optional[str] = None,
        **kwargs,
    ) -> IterationResult:
        """
        Execute story iteration with retry.

        Args:
            story_id: Unique story identifier
            story_name: Human-readable story name
            phase: Phase name ("discovery", "architecture", etc.)
            phase_function: Function to execute for phase
            iteration_id: Optional iteration ID
            **kwargs: Arguments for phase_function

        Returns:
            IterationResult with final status
        """
        iteration_id = iteration_id or f"micro_{story_id}_{int(time.time())}"

        self.logger.info(f"Starting micro iteration: {iteration_id} (Story: {story_name}, Phase: {phase})")

        # Create iteration object
        iteration = MicroIteration(
            iteration_id=iteration_id,
            story_id=story_id,
            story_name=story_name,
            phase=phase,
            max_retries=self.max_retries,
        )

        # Load checkpoint if exists
        if self.enable_checkpoint:
            checkpoint = self._load_checkpoint(story_id, phase)
            if checkpoint:
                iteration.checkpoint_data = checkpoint
                self.logger.info("Loaded checkpoint data")

        iteration.status = IterationStatus.IN_PROGRESS

        # Execute with retry
        for attempt in range(1, self.max_retries + 1):
            self.logger.info(f"Micro attempt {attempt}/{self.max_retries}")

            start_time = time.time()
            iteration.current_attempt = attempt

            try:
                # Execute phase function
                result = phase_function(**kwargs)

                duration = time.time() - start_time

                # Validate result
                is_valid, failure_reason = self._validate_result(result, phase)

                # Record attempt
                attempt_obj = IterationAttempt(
                    attempt_number=attempt,
                    timestamp=datetime.now(),
                    status=IterationStatus.SUCCESS if is_valid else IterationStatus.FAILED,
                    duration_seconds=duration,
                    failure_reason=failure_reason,
                    artifacts={"result": result} if result else {},
                )
                iteration.attempts.append(attempt_obj)

                if is_valid:
                    self.logger.info(f"Micro iteration succeeded on attempt {attempt}")
                    iteration.status = IterationStatus.SUCCESS

                    # Save successful checkpoint
                    if self.enable_checkpoint:
                        self._save_checkpoint(story_id, phase, result)

                    return self._create_result(iteration, successful=True)

                # Attempt failed
                self.logger.warning(f"Micro attempt {attempt} failed: {failure_reason}")

                # Try to fix incrementally
                if attempt < self.max_retries:
                    self.logger.info("Attempting incremental fix...")
                    kwargs = self._apply_incremental_fix(kwargs, failure_reason, result)

                    # Exponential backoff
                    delay = 1.0 * (2 ** (attempt - 1))  # 1s, 2s, 4s
                    time.sleep(min(delay, 10.0))  # Cap at 10s

            except Exception as e:
                duration = time.time() - start_time
                self.logger.error(f"Micro attempt {attempt} exception: {e}")

                # Record failed attempt
                attempt_obj = IterationAttempt(
                    attempt_number=attempt,
                    timestamp=datetime.now(),
                    status=IterationStatus.FAILED,
                    duration_seconds=duration,
                    failure_reason=FailureReason.RUNTIME_ERROR,
                    error_message=str(e),
                )
                iteration.attempts.append(attempt_obj)

                if attempt < self.max_retries:
                    time.sleep(1.0)

        # All retries exhausted
        self.logger.error("Micro iteration: Max retries exhausted")
        iteration.status = IterationStatus.EXHAUSTED

        # Rollback to last checkpoint
        if self.enable_checkpoint and iteration.checkpoint_data:
            self.logger.info("Rolling back to last checkpoint")
            self._rollback_to_checkpoint(story_id, phase)

        return self._create_result(iteration, successful=False)

    def execute_with_tdd(
        self,
        story_id: str,
        story_name: str,
        test_files: List[Path],
        implementation_files: List[Path],
        iteration_id: Optional[str] = None,
    ) -> IterationResult:
        """
        Execute story with TDD (multiple nano iterations).

        Args:
            story_id: Story identifier
            story_name: Story name
            test_files: List of test files
            implementation_files: Corresponding implementation files
            iteration_id: Optional iteration ID

        Returns:
            IterationResult
        """
        iteration_id = iteration_id or f"micro_tdd_{story_id}_{int(time.time())}"

        self.logger.info(f"Starting TDD micro iteration: {iteration_id}")

        iteration = MicroIteration(
            iteration_id=iteration_id,
            story_id=story_id,
            story_name=story_name,
            phase="tdd",
            max_retries=self.max_retries,
        )

        all_passed = True

        # Execute nano iteration for each test/implementation pair
        for test_file, impl_file in zip(test_files, implementation_files):
            self.logger.info(f"Nano iteration: {test_file.name} → {impl_file.name}")

            nano_result = self.nano_iterator.execute(
                test_file=test_file,
                implementation_file=impl_file,
            )

            # Track nano iteration
            # (In real implementation, would store full NanoIteration object)

            if not nano_result.successful:
                all_passed = False
                self.logger.error(f"Nano iteration failed: {nano_result.error_summary}")
                break

        if all_passed:
            iteration.status = IterationStatus.SUCCESS
            return self._create_result(iteration, successful=True)
        else:
            iteration.status = IterationStatus.FAILED
            return self._create_result(iteration, successful=False)

    def _validate_result(
        self,
        result: Any,
        phase: str
    ) -> tuple[bool, Optional[FailureReason]]:
        """
        Validate phase result.

        Returns:
            (is_valid, failure_reason)
        """
        if result is None:
            return False, FailureReason.UNKNOWN

        # Phase-specific validation
        if phase == "discovery":
            # Check for required fields in discovery result
            if isinstance(result, dict):
                if "features" not in result:
                    return False, FailureReason.VALIDATION_ERROR
                if len(result.get("features", [])) == 0:
                    return False, FailureReason.VALIDATION_ERROR

        elif phase == "architecture":
            # Check architecture design
            if isinstance(result, dict):
                if "components" not in result and "agents" not in result:
                    return False, FailureReason.VALIDATION_ERROR

        elif phase == "design":
            # Check agent/task design
            if isinstance(result, dict):
                if "agents" not in result or "tasks" not in result:
                    return False, FailureReason.VALIDATION_ERROR

        # Default: assume valid if result exists
        return True, None

    def _apply_incremental_fix(
        self,
        kwargs: Dict[str, Any],
        failure_reason: Optional[FailureReason],
        previous_result: Any,
    ) -> Dict[str, Any]:
        """
        Apply incremental fix to inputs based on failure.

        Returns:
            Updated kwargs
        """
        # Add context from previous attempt
        if "context" not in kwargs:
            kwargs["context"] = {}

        kwargs["context"]["previous_failure"] = failure_reason.value if failure_reason else "unknown"
        kwargs["context"]["retry_attempt"] = True

        # Failure-specific fixes
        if failure_reason == FailureReason.VALIDATION_ERROR:
            kwargs["context"]["hint"] = "Ensure all required fields are present"

        elif failure_reason == FailureReason.TEST_FAILURE:
            kwargs["context"]["hint"] = "Review test assertions and fix logic"

        elif failure_reason == FailureReason.QUALITY_GATE_FAILURE:
            kwargs["context"]["hint"] = "Improve code quality metrics"

        return kwargs

    def _save_checkpoint(self, story_id: str, phase: str, data: Any):
        """Save checkpoint data to disk"""
        if not self.checkpoint_dir.exists():
            self.checkpoint_dir.mkdir(parents=True)

        checkpoint_file = self.checkpoint_dir / f"{story_id}_{phase}.json"

        try:
            # Convert data to JSON-serializable format
            checkpoint_data = {
                "story_id": story_id,
                "phase": phase,
                "timestamp": datetime.now().isoformat(),
                "data": self._serialize(data),
            }

            with open(checkpoint_file, "w") as f:
                json.dump(checkpoint_data, f, indent=2)

            self.logger.debug(f"Checkpoint saved: {checkpoint_file}")

        except Exception as e:
            self.logger.warning(f"Failed to save checkpoint: {e}")

    def _load_checkpoint(self, story_id: str, phase: str) -> Optional[Dict]:
        """Load checkpoint data from disk"""
        checkpoint_file = self.checkpoint_dir / f"{story_id}_{phase}.json"

        if not checkpoint_file.exists():
            return None

        try:
            with open(checkpoint_file, "r") as f:
                checkpoint_data = json.load(f)

            self.logger.debug(f"Checkpoint loaded: {checkpoint_file}")
            return checkpoint_data.get("data")

        except Exception as e:
            self.logger.warning(f"Failed to load checkpoint: {e}")
            return None

    def _rollback_to_checkpoint(self, story_id: str, phase: str):
        """Rollback to checkpoint state"""
        self.logger.info(f"Rolling back story {story_id} phase {phase}")
        # In real implementation, would restore checkpoint state
        # For now, just log the action

    def _serialize(self, data: Any) -> Any:
        """Convert data to JSON-serializable format"""
        if isinstance(data, dict):
            return {k: self._serialize(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._serialize(item) for item in data]
        elif isinstance(data, (str, int, float, bool, type(None))):
            return data
        else:
            # Convert to string for other types
            return str(data)

    def _create_result(
        self,
        iteration: MicroIteration,
        successful: bool,
    ) -> IterationResult:
        """Create iteration result"""
        final_attempt = iteration.attempts[-1] if iteration.attempts else None

        recovery_actions = []
        if not successful:
            recovery_actions = [
                "Review and fix validation errors",
                "Check phase dependencies",
                "Rollback to previous checkpoint",
                "Manual intervention required",
            ]

        return IterationResult(
            level=IterationLevel.MICRO,
            iteration_id=iteration.iteration_id,
            status=iteration.status,
            total_attempts=iteration.current_attempt,
            successful=successful,
            final_attempt=final_attempt,
            error_summary=final_attempt.error_message if final_attempt and final_attempt.error_message else None,
            recovery_actions=recovery_actions,
        )
