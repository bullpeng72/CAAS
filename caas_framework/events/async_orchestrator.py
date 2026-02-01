"""
Async Orchestrator

Provides asynchronous and parallel execution of phases for improved
performance and scalability.
"""

import asyncio
from typing import List, Dict, Any, Callable, Optional
from dataclasses import dataclass, field
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from enum import Enum
import time
import logging

from caas_framework.events.events import PhaseEvent, create_phase_event
from caas_framework.events.event_bus import EventBus, get_global_event_bus

logger = logging.getLogger(__name__)


class ExecutionMode(Enum):
    """Execution mode for phases."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    ASYNC = "async"


@dataclass
class PhaseResult:
    """Result of phase execution."""
    phase_name: str
    success: bool
    result: Any = None
    error: Optional[Exception] = None
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PhaseDefinition:
    """Definition of a phase to execute."""
    name: str
    executor: Callable
    dependencies: List[str] = field(default_factory=list)
    timeout: Optional[float] = None
    retry_count: int = 0


class AsyncOrchestrator:
    """
    Orchestrates asynchronous and parallel execution of phases.

    Supports dependency management, parallel execution, and event-driven
    workflow.
    """

    def __init__(
        self,
        event_bus: Optional[EventBus] = None,
        max_workers: int = 4,
        use_processes: bool = False
    ):
        """
        Initialize async orchestrator.

        Args:
            event_bus: Event bus for publishing events
            max_workers: Maximum number of parallel workers
            use_processes: Use processes instead of threads
        """
        self.event_bus = event_bus or get_global_event_bus()
        self.max_workers = max_workers
        self.use_processes = use_processes

        if use_processes:
            self.executor = ProcessPoolExecutor(max_workers=max_workers)
        else:
            self.executor = ThreadPoolExecutor(max_workers=max_workers)

    async def execute_phase_async(
        self,
        phase_def: PhaseDefinition,
        context: Dict[str, Any]
    ) -> PhaseResult:
        """
        Execute a single phase asynchronously.

        Args:
            phase_def: Phase definition
            context: Execution context

        Returns:
            PhaseResult
        """
        start_time = time.time()

        # Publish phase started event
        self.event_bus.publish(create_phase_event(
            PhaseEvent.PHASE_STARTED,
            phase_def.name,
            {'context_keys': list(context.keys())}
        ))

        try:
            # Execute with timeout
            if phase_def.timeout:
                result = await asyncio.wait_for(
                    self._run_executor(phase_def.executor, context),
                    timeout=phase_def.timeout
                )
            else:
                result = await self._run_executor(phase_def.executor, context)

            execution_time = time.time() - start_time

            # Publish phase completed event
            self.event_bus.publish(create_phase_event(
                PhaseEvent.PHASE_COMPLETED,
                phase_def.name,
                {'execution_time': execution_time}
            ))

            return PhaseResult(
                phase_name=phase_def.name,
                success=True,
                result=result,
                execution_time=execution_time
            )

        except asyncio.TimeoutError:
            execution_time = time.time() - start_time
            error = TimeoutError(f"Phase {phase_def.name} timed out after {phase_def.timeout}s")

            self.event_bus.publish(create_phase_event(
                PhaseEvent.PHASE_FAILED,
                phase_def.name,
                {'error': str(error), 'reason': 'timeout'}
            ))

            return PhaseResult(
                phase_name=phase_def.name,
                success=False,
                error=error,
                execution_time=execution_time
            )

        except Exception as e:
            execution_time = time.time() - start_time

            self.event_bus.publish(create_phase_event(
                PhaseEvent.PHASE_FAILED,
                phase_def.name,
                {'error': str(e), 'error_type': type(e).__name__}
            ))

            return PhaseResult(
                phase_name=phase_def.name,
                success=False,
                error=e,
                execution_time=execution_time
            )

    async def _run_executor(self, executor: Callable, context: Dict[str, Any]) -> Any:
        """Run executor function (sync or async)."""
        if asyncio.iscoroutinefunction(executor):
            return await executor(context)
        else:
            # Run sync function in thread pool
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(self.executor, executor, context)

    async def execute_parallel(
        self,
        phase_defs: List[PhaseDefinition],
        context: Dict[str, Any]
    ) -> List[PhaseResult]:
        """
        Execute multiple independent phases in parallel.

        Args:
            phase_defs: List of phase definitions
            context: Shared execution context

        Returns:
            List of phase results
        """
        logger.info(f"Executing {len(phase_defs)} phases in parallel")

        tasks = [
            self.execute_phase_async(phase_def, context)
            for phase_def in phase_defs
        ]

        results = await asyncio.gather(*tasks, return_exceptions=False)

        return results

    async def execute_with_dependencies(
        self,
        phase_defs: List[PhaseDefinition],
        context: Dict[str, Any]
    ) -> Dict[str, PhaseResult]:
        """
        Execute phases respecting dependencies.

        Uses topological sort to determine execution order and
        parallelizes independent phases.

        Args:
            phase_defs: List of phase definitions
            context: Execution context

        Returns:
            Dictionary mapping phase names to results
        """
        # Build dependency graph
        phase_map = {p.name: p for p in phase_defs}
        results: Dict[str, PhaseResult] = {}
        pending = set(p.name for p in phase_defs)
        executing = set()

        while pending or executing:
            # First, remove phases with failed dependencies
            phases_to_skip = []
            for phase_name in pending:
                phase_def = phase_map[phase_name]
                deps_failed = any(
                    dep in results and not results[dep].success
                    for dep in phase_def.dependencies
                )
                if deps_failed:
                    phases_to_skip.append(phase_name)

            for phase_name in phases_to_skip:
                pending.remove(phase_name)
                logger.info(f"Skipping {phase_name} due to failed dependency")

            # Find phases ready to execute (no pending dependencies)
            ready = []
            for phase_name in pending:
                phase_def = phase_map[phase_name]
                deps_completed = all(
                    dep in results and results[dep].success
                    for dep in phase_def.dependencies
                )

                if deps_completed:
                    ready.append(phase_def)

            if not ready and not executing and pending:
                # Deadlock or circular dependency
                raise RuntimeError(
                    f"Cannot proceed: no phases ready to execute. "
                    f"Pending: {pending}, Executing: {executing}"
                )

            # Execute ready phases in parallel
            if ready:
                logger.info(f"Executing {len(ready)} ready phases in parallel")

                # Move to executing
                for phase_def in ready:
                    pending.remove(phase_def.name)
                    executing.add(phase_def.name)

                # Execute
                phase_results = await self.execute_parallel(ready, context)

                # Update results
                for phase_result in phase_results:
                    results[phase_result.phase_name] = phase_result
                    executing.remove(phase_result.phase_name)

                    # Update context with result
                    if phase_result.success and phase_result.result is not None:
                        context[phase_result.phase_name] = phase_result.result

            # Small delay to allow async tasks to progress
            if executing:
                await asyncio.sleep(0.01)

        return results

    async def execute_pipeline(
        self,
        phase_defs: List[PhaseDefinition],
        initial_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, PhaseResult]:
        """
        Execute a pipeline of phases.

        Automatically determines execution order based on dependencies
        and parallelizes when possible.

        Args:
            phase_defs: List of phase definitions
            initial_context: Initial context

        Returns:
            Dictionary mapping phase names to results
        """
        context = initial_context or {}

        logger.info(f"Starting pipeline with {len(phase_defs)} phases")

        start_time = time.time()

        results = await self.execute_with_dependencies(phase_defs, context)

        total_time = time.time() - start_time

        # Log summary
        successful = sum(1 for r in results.values() if r.success)
        failed = len(results) - successful

        logger.info(
            f"Pipeline completed in {total_time:.2f}s: "
            f"{successful} successful, {failed} failed"
        )

        return results

    def get_execution_summary(
        self,
        results: Dict[str, PhaseResult]
    ) -> Dict[str, Any]:
        """
        Get execution summary.

        Args:
            results: Phase results

        Returns:
            Summary dictionary
        """
        successful = [r for r in results.values() if r.success]
        failed = [r for r in results.values() if not r.success]

        total_time = sum(r.execution_time for r in results.values())
        avg_time = total_time / len(results) if results else 0

        return {
            'total_phases': len(results),
            'successful': len(successful),
            'failed': len(failed),
            'success_rate': len(successful) / len(results) if results else 0,
            'total_execution_time': total_time,
            'avg_execution_time': avg_time,
            'failed_phases': [r.phase_name for r in failed]
        }

    def shutdown(self):
        """Shutdown the orchestrator and cleanup resources."""
        self.executor.shutdown(wait=True)


def create_phase_definition(
    name: str,
    executor: Callable,
    dependencies: Optional[List[str]] = None,
    timeout: Optional[float] = None
) -> PhaseDefinition:
    """
    Convenience function to create phase definition.

    Args:
        name: Phase name
        executor: Executor function
        dependencies: List of dependency phase names
        timeout: Optional timeout in seconds

    Returns:
        PhaseDefinition instance
    """
    return PhaseDefinition(
        name=name,
        executor=executor,
        dependencies=dependencies or [],
        timeout=timeout
    )
