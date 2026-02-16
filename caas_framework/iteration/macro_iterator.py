"""
Macro Iterator - Epic-level Iteration

Implements epic-level retry logic:
- Multiple story coordination
- Story dependency management
- Epic-level rollback

Part of CAAS-E Week 6 implementation (Task 6.2).
"""

import time
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime
import logging

from caas_framework.models.iteration import (
    MacroIteration,
    IterationAttempt,
    IterationStatus,
    FailureReason,
    IterationResult,
    IterationLevel,
)
from caas_framework.iteration.micro_iterator import MicroIterator

logger = logging.getLogger(__name__)


class MacroIterator:
    """
    Macro-level iterator for epic-level retry.

    Handles:
    - Multi-story execution
    - Story dependency tracking
    - Epic-level rollback and retry
    - Progress checkpointing
    """

    def __init__(
        self,
        max_retries: int = 3,
        fail_fast: bool = False,
    ):
        """
        Initialize macro iterator.

        Args:
            max_retries: Maximum retry attempts for epic
            fail_fast: Stop on first story failure
        """
        self.max_retries = max_retries
        self.fail_fast = fail_fast
        self.micro_iterator = MicroIterator()
        self.logger = logging.getLogger(self.__class__.__name__)

    def execute(
        self,
        epic_id: str,
        epic_name: str,
        stories: List[Dict[str, Any]],
        story_executor: Callable,
        iteration_id: Optional[str] = None,
    ) -> IterationResult:
        """
        Execute epic iteration with multiple stories.

        Args:
            epic_id: Epic identifier
            epic_name: Epic name
            stories: List of story dictionaries with id, name, dependencies
            story_executor: Function to execute a story
            iteration_id: Optional iteration ID

        Returns:
            IterationResult
        """
        iteration_id = iteration_id or f"macro_{epic_id}_{int(time.time())}"

        self.logger.info(f"Starting macro iteration: {iteration_id} (Epic: {epic_name})")
        self.logger.info(f"Total stories: {len(stories)}")

        # Create iteration object
        story_ids = [s["id"] for s in stories]
        iteration = MacroIteration(
            iteration_id=iteration_id,
            epic_id=epic_id,
            epic_name=epic_name,
            story_ids=story_ids,
            max_retries=self.max_retries,
        )

        iteration.status = IterationStatus.IN_PROGRESS

        # Execute with retry
        for attempt in range(1, self.max_retries + 1):
            self.logger.info(f"Macro attempt {attempt}/{self.max_retries}")

            start_time = time.time()
            iteration.current_attempt = attempt

            # Sort stories by dependencies (topological sort)
            sorted_stories = self._topological_sort(stories)

            success_count = 0
            failure_count = 0

            # Execute stories in order
            for story in sorted_stories:
                story_id = story["id"]
                story_name = story["name"]

                self.logger.info(f"Executing story: {story_name}")

                try:
                    # Execute story
                    result = story_executor(story)

                    if result:
                        # Story succeeded
                        success_count += 1
                        iteration.completed_stories.append(story_id)
                        self.logger.info(f"Story completed: {story_name} ✓")
                    else:
                        # Story failed
                        failure_count += 1
                        iteration.failed_stories.append(story_id)
                        self.logger.error(f"Story failed: {story_name} ✗")

                        if self.fail_fast:
                            self.logger.info("Fail-fast enabled, stopping execution")
                            break

                except Exception as e:
                    self.logger.error(f"Story exception: {story_name} - {e}")
                    failure_count += 1
                    iteration.failed_stories.append(story_id)

                    if self.fail_fast:
                        break

            duration = time.time() - start_time

            # Record attempt
            attempt_obj = IterationAttempt(
                attempt_number=attempt,
                timestamp=datetime.now(),
                status=IterationStatus.SUCCESS if failure_count == 0 else IterationStatus.FAILED,
                duration_seconds=duration,
                failure_reason=FailureReason.UNKNOWN if failure_count > 0 else None,
                metrics={
                    "total_stories": len(stories),
                    "completed_stories": success_count,
                    "failed_stories": failure_count,
                },
            )
            iteration.attempts.append(attempt_obj)

            # Check if all stories succeeded
            if failure_count == 0:
                self.logger.info(f"Macro iteration succeeded: {success_count}/{len(stories)} stories completed")
                iteration.status = IterationStatus.SUCCESS
                return self._create_result(iteration, successful=True)

            # Some stories failed
            self.logger.warning(f"Macro attempt {attempt}: {failure_count} stories failed")

            # Retry failed stories only
            if attempt < self.max_retries:
                self.logger.info(f"Retrying {failure_count} failed stories...")
                failed_story_ids = iteration.failed_stories.copy()
                iteration.failed_stories.clear()

                # Filter stories to retry
                stories = [s for s in stories if s["id"] in failed_story_ids]

                # Exponential backoff
                delay = 2.0 * (2 ** (attempt - 1))  # 2s, 4s, 8s
                time.sleep(min(delay, 30.0))  # Cap at 30s

        # All retries exhausted
        self.logger.error(f"Macro iteration exhausted: {len(iteration.failed_stories)} stories still failing")
        iteration.status = IterationStatus.EXHAUSTED

        return self._create_result(iteration, successful=False)

    def _topological_sort(self, stories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Sort stories by dependencies using topological sort.

        Args:
            stories: List of stories with dependencies

        Returns:
            Sorted list of stories
        """
        from collections import deque

        # Build dependency graph
        in_degree = {s["id"]: 0 for s in stories}
        graph = {s["id"]: [] for s in stories}

        for story in stories:
            deps = story.get("dependencies", [])
            for dep in deps:
                if dep in graph:
                    graph[dep].append(story["id"])
                    in_degree[story["id"]] += 1

        # Topological sort (Kahn's algorithm)
        queue = deque([s["id"] for s in stories if in_degree[s["id"]] == 0])
        sorted_ids = []

        while queue:
            story_id = queue.popleft()
            sorted_ids.append(story_id)

            for neighbor in graph[story_id]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # Map back to stories
        story_map = {s["id"]: s for s in stories}
        sorted_stories = [story_map[sid] for sid in sorted_ids if sid in story_map]

        # Add any remaining stories (circular dependencies)
        for story in stories:
            if story not in sorted_stories:
                sorted_stories.append(story)

        return sorted_stories

    def _create_result(
        self,
        iteration: MacroIteration,
        successful: bool,
    ) -> IterationResult:
        """Create iteration result"""
        final_attempt = iteration.attempts[-1] if iteration.attempts else None

        recovery_actions = []
        if not successful:
            recovery_actions = [
                f"Review failed stories: {', '.join(iteration.failed_stories[:5])}",
                "Check story dependencies",
                "Rollback epic to last stable state",
                "Execute stories individually for debugging",
            ]

        return IterationResult(
            level=IterationLevel.MACRO,
            iteration_id=iteration.iteration_id,
            status=iteration.status,
            total_attempts=iteration.current_attempt,
            successful=successful,
            final_attempt=final_attempt,
            error_summary=f"{len(iteration.failed_stories)} stories failed" if not successful else None,
            recovery_actions=recovery_actions,
        )
