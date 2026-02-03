"""
Async Batch Executor

Efficient parallel execution of async operations with batching and concurrency control.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, List, Optional, TypeVar

T = TypeVar("T")


@dataclass
class BatchConfig:
    """Configuration for batch execution"""

    max_concurrent: int = 5  # Maximum concurrent operations
    batch_size: int = 10  # Size of each batch
    timeout_per_item: float = 30.0  # Timeout per item (seconds)
    continue_on_error: bool = True  # Continue if individual items fail


class AsyncBatchExecutor:
    """
    Execute async operations in parallel batches with concurrency control.

    Features:
    - Controlled concurrency (semaphore-based)
    - Batch processing
    - Timeout handling
    - Error recovery
    - Progress tracking
    """

    def __init__(
        self,
        config: Optional[BatchConfig] = None,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize batch executor.

        Args:
            config: Batch configuration
            logger: Optional logger
        """
        self.config = config or BatchConfig()
        self.logger = logger or logging.getLogger(__name__)
        self.semaphore = asyncio.Semaphore(self.config.max_concurrent)

    async def execute_batch(
        self,
        items: List[T],
        async_fn: Callable[[T], Awaitable[Any]],
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> List[tuple[T, Any, Optional[Exception]]]:
        """
        Execute async function on batch of items.

        Args:
            items: List of items to process
            async_fn: Async function to apply to each item
            progress_callback: Optional callback(completed, total)

        Returns:
            List of (item, result, error) tuples
        """
        results = []
        total = len(items)

        self.logger.info(
            f"🚀 Starting batch execution: {total} items, "
            f"max concurrent: {self.config.max_concurrent}"
        )

        # Process in batches
        for batch_start in range(0, total, self.config.batch_size):
            batch_end = min(batch_start + self.config.batch_size, total)
            batch = items[batch_start:batch_end]

            self.logger.debug(
                f"Processing batch {batch_start//self.config.batch_size + 1}: "
                f"items {batch_start+1}-{batch_end}/{total}"
            )

            # Execute batch with concurrency control
            batch_results = await asyncio.gather(
                *[self._execute_with_semaphore(item, async_fn) for item in batch],
                return_exceptions=False,
            )

            results.extend(batch_results)

            # Progress callback
            if progress_callback:
                progress_callback(len(results), total)

        self.logger.info(f"✅ Batch execution completed: {len(results)}/{total} items")

        return results

    async def _execute_with_semaphore(
        self, item: T, async_fn: Callable[[T], Awaitable[Any]]
    ) -> tuple[T, Any, Optional[Exception]]:
        """
        Execute with semaphore for concurrency control.

        Args:
            item: Item to process
            async_fn: Async function

        Returns:
            (item, result, error) tuple
        """
        async with self.semaphore:
            try:
                result = await asyncio.wait_for(
                    async_fn(item), timeout=self.config.timeout_per_item
                )
                return (item, result, None)

            except asyncio.TimeoutError as e:
                self.logger.warning(f"⏱️ Timeout processing item: {item}")
                if self.config.continue_on_error:
                    return (item, None, e)
                raise

            except Exception as e:
                self.logger.warning(f"❌ Error processing item: {item} - {e}")
                if self.config.continue_on_error:
                    return (item, None, e)
                raise

    async def map_parallel(
        self,
        items: List[T],
        async_fn: Callable[[T], Awaitable[Any]],
        filter_errors: bool = True,
    ) -> List[Any]:
        """
        Map async function over items in parallel (like asyncio.gather but with control).

        Args:
            items: Items to process
            async_fn: Async function to map
            filter_errors: Filter out failed items

        Returns:
            List of results (errors filtered if filter_errors=True)
        """
        batch_results = await self.execute_batch(items, async_fn)

        if filter_errors:
            # Return only successful results
            return [result for _, result, error in batch_results if error is None]
        else:
            # Return all results (None for errors)
            return [result for _, result, _ in batch_results]

    async def execute_parallel(
        self,
        tasks: List[Callable[[], Awaitable[T]]],
        max_concurrent: Optional[int] = None,
    ) -> List[T]:
        """
        Execute multiple async tasks in parallel.

        Args:
            tasks: List of async callables (no args)
            max_concurrent: Override max concurrent

        Returns:
            List of results
        """
        if max_concurrent:
            original_max = self.config.max_concurrent
            self.config.max_concurrent = max_concurrent
            self.semaphore = asyncio.Semaphore(max_concurrent)

        try:
            # Wrap tasks to work with execute_batch
            async def execute_task(task_fn):
                return await task_fn()

            results = await self.map_parallel(tasks, execute_task, filter_errors=False)
            return results

        finally:
            if max_concurrent:
                self.config.max_concurrent = original_max
                self.semaphore = asyncio.Semaphore(original_max)

    def get_optimal_batch_size(self, total_items: int, target_batches: int = 10) -> int:
        """
        Calculate optimal batch size.

        Args:
            total_items: Total number of items
            target_batches: Target number of batches

        Returns:
            Optimal batch size
        """
        if total_items <= target_batches:
            return 1

        return max(1, total_items // target_batches)


async def run_parallel(
    *coroutines: Awaitable[T], max_concurrent: int = 5, return_exceptions: bool = False
) -> List[T]:
    """
    Convenience function to run coroutines in parallel with concurrency limit.

    Args:
        *coroutines: Coroutines to run
        max_concurrent: Maximum concurrent executions
        return_exceptions: Return exceptions instead of raising

    Returns:
        List of results

    Example:
        results = await run_parallel(
            task1(), task2(), task3(),
            max_concurrent=2
        )
    """
    semaphore = asyncio.Semaphore(max_concurrent)

    async def run_with_semaphore(coro):
        async with semaphore:
            return await coro

    return await asyncio.gather(
        *[run_with_semaphore(coro) for coro in coroutines],
        return_exceptions=return_exceptions,
    )


async def batch_process(
    items: List[T],
    process_fn: Callable[[T], Awaitable[Any]],
    batch_size: int = 10,
    max_concurrent: int = 5,
) -> List[Any]:
    """
    Convenience function for batch processing.

    Args:
        items: Items to process
        process_fn: Async processing function
        batch_size: Batch size
        max_concurrent: Max concurrent operations

    Returns:
        List of results

    Example:
        results = await batch_process(
            items=[1, 2, 3, 4, 5],
            process_fn=async_double,
            batch_size=2,
            max_concurrent=3
        )
    """
    config = BatchConfig(max_concurrent=max_concurrent, batch_size=batch_size)

    executor = AsyncBatchExecutor(config=config)
    return await executor.map_parallel(items, process_fn)
