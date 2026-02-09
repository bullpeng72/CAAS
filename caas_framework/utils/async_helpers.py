"""
Async Utilities for CAAS Framework

Provides common utilities for async operations:
- TimeoutManager: Unified timeout handling
- RetryStrategy: Standardized retry logic with exponential backoff
"""

import asyncio
import logging
import time
from functools import wraps
from typing import Awaitable, Callable, List, Optional, Tuple, TypeVar

from caas_framework.utils.logger import get_logger

T = TypeVar("T")

logger = get_logger()


class TimeoutManager:
    """
    Unified timeout management for async operations.

    Eliminates duplicate timeout handling across the codebase.
    """

    @staticmethod
    async def execute_with_timeout(
        coro: Awaitable[T],
        timeout: float,
        operation_name: str,
        logger_instance: Optional[logging.Logger] = None,
        fallback_value: Optional[T] = None,
    ) -> Tuple[bool, Optional[T], Optional[str]]:
        """
        Execute coroutine with timeout protection.

        Args:
            coro: Coroutine to execute
            timeout: Timeout in seconds
            operation_name: Human-readable operation name for logging
            logger_instance: Optional logger instance
            fallback_value: Value to return on timeout/error

        Returns:
            Tuple of (success, result, error_message)
            - success: True if completed within timeout
            - result: Result of the operation or fallback_value
            - error_message: Error description if failed

        Example:
            success, result, error = await TimeoutManager.execute_with_timeout(
                some_async_function(),
                timeout=60.0,
                operation_name="Validation"
            )
        """
        log = logger_instance or logger

        try:
            result = await asyncio.wait_for(coro, timeout=timeout)
            return (True, result, None)

        except asyncio.TimeoutError:
            error_msg = f"⏱️ {operation_name} timed out after {timeout}s"
            log.warning(error_msg)
            return (False, fallback_value, error_msg)

        except Exception as e:
            error_msg = f"❌ {operation_name} failed: {str(e)}"
            log.error(error_msg, exc_info=True)
            return (False, fallback_value, error_msg)

    @staticmethod
    def with_timeout(timeout: float, operation_name: str = "Operation"):
        """
        Decorator for adding timeout to async functions.

        Args:
            timeout: Timeout in seconds
            operation_name: Operation name for error messages

        Example:
            @TimeoutManager.with_timeout(timeout=30.0, operation_name="Data processing")
            async def process_data():
                ...
        """

        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                success, result, error = await TimeoutManager.execute_with_timeout(
                    func(*args, **kwargs),
                    timeout=timeout,
                    operation_name=operation_name,
                )
                if not success:
                    raise TimeoutError(error)
                return result

            return wrapper

        return decorator


class RetryStrategy:
    """
    Standardized retry logic with exponential backoff.

    Eliminates duplicate retry patterns across the codebase.
    """

    @staticmethod
    async def execute_with_retry(
        func: Callable[[], Awaitable[T]],
        max_retries: int = 3,
        timeout_per_retry: Optional[float] = None,
        backoff_factor: float = 1.5,
        initial_delay: float = 0.5,
        operation_name: str = "Operation",
        logger_instance: Optional[logging.Logger] = None,
        should_retry: Optional[Callable[[Exception], bool]] = None,
    ) -> Tuple[bool, Optional[T], List[str]]:
        """
        Execute function with retry logic and exponential backoff.

        Args:
            func: Async function to execute
            max_retries: Maximum number of retry attempts
            timeout_per_retry: Optional timeout per attempt (increases with backoff)
            backoff_factor: Multiplier for delay between retries
            initial_delay: Initial delay between retries (seconds)
            operation_name: Operation name for logging
            logger_instance: Optional logger instance
            should_retry: Optional function to determine if error is retryable

        Returns:
            Tuple of (success, result, errors)
            - success: True if any attempt succeeded
            - result: Result of the operation
            - errors: List of error messages from failed attempts

        Example:
            success, result, errors = await RetryStrategy.execute_with_retry(
                lambda: my_async_function(),
                max_retries=3,
                timeout_per_retry=60.0,
                operation_name="Code generation"
            )
        """
        log = logger_instance or logger
        errors = []

        for attempt in range(max_retries):
            try:
                # Calculate timeout with backoff
                current_timeout = None
                if timeout_per_retry:
                    current_timeout = timeout_per_retry * (backoff_factor**attempt)
                    log.info(
                        f"🔄 {operation_name} attempt {attempt + 1}/{max_retries} "
                        f"(timeout: {current_timeout:.1f}s)"
                    )
                else:
                    log.info(f"🔄 {operation_name} attempt {attempt + 1}/{max_retries}")

                # Execute with optional timeout
                if current_timeout:
                    success, result, error = await TimeoutManager.execute_with_timeout(
                        func(),
                        timeout=current_timeout,
                        operation_name=f"{operation_name} (attempt {attempt + 1})",
                        logger_instance=log,
                    )

                    if success:
                        if attempt > 0:
                            log.info(
                                f"✅ {operation_name} succeeded on attempt {attempt + 1}"
                            )
                        return (True, result, errors)
                    else:
                        errors.append(error)
                else:
                    # No timeout
                    result = await func()
                    if attempt > 0:
                        log.info(
                            f"✅ {operation_name} succeeded on attempt {attempt + 1}"
                        )
                    return (True, result, errors)

            except Exception as e:
                error_msg = f"Attempt {attempt + 1} failed: {str(e)}"
                errors.append(error_msg)
                log.warning(error_msg)

                # Check if should retry
                if should_retry and not should_retry(e):
                    log.error(f"Non-retryable error encountered: {e}")
                    return (False, None, errors)

                # Exponential backoff before next retry
                if attempt < max_retries - 1:
                    delay = initial_delay * (backoff_factor**attempt)
                    log.info(f"⏳ Waiting {delay:.1f}s before retry...")
                    await asyncio.sleep(delay)

        # All retries exhausted
        log.error(f"❌ {operation_name} failed after {max_retries} attempts")
        return (False, None, errors)

    @staticmethod
    def with_retry(
        max_retries: int = 3,
        timeout_per_retry: Optional[float] = None,
        backoff_factor: float = 1.5,
        operation_name: str = "Operation",
    ):
        """
        Decorator for adding retry logic to async functions.

        Example:
            @RetryStrategy.with_retry(max_retries=3, timeout_per_retry=30.0)
            async def unstable_operation():
                ...
        """

        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                success, result, errors = await RetryStrategy.execute_with_retry(
                    lambda: func(*args, **kwargs),
                    max_retries=max_retries,
                    timeout_per_retry=timeout_per_retry,
                    backoff_factor=backoff_factor,
                    operation_name=operation_name,
                )
                if not success:
                    raise RuntimeError(
                        f"{operation_name} failed after {max_retries} retries. "
                        f"Errors: {'; '.join(errors)}"
                    )
                return result

            return wrapper

        return decorator


class OperationTimer:
    """
    Simple context manager for timing operations.

    Example:
        with OperationTimer("Phase execution") as timer:
            await some_operation()

        logger.info(f"Duration: {timer.duration}s")
    """

    def __init__(
        self, operation_name: str, logger_instance: Optional[logging.Logger] = None
    ):
        self.operation_name = operation_name
        self.logger = logger_instance or logger
        self.start_time = None
        self.end_time = None
        self.duration = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time

        if exc_type is None:
            self.logger.info(
                f"✅ {self.operation_name} completed in {self.duration:.2f}s"
            )
        else:
            self.logger.error(
                f"❌ {self.operation_name} failed after {self.duration:.2f}s"
            )

        return False  # Don't suppress exceptions
