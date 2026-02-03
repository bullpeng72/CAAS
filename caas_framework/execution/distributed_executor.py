"""
Distributed Phase Executor

Enables parallel execution of BMAD phases using ProcessPoolExecutor or ThreadPoolExecutor.
Analyzes dependency graphs and schedules phases for maximum parallelism while respecting
dependencies.

Key Features:
- Dependency graph-based scheduling
- Process isolation for CPU-bound tasks
- Thread-based execution for I/O-bound tasks
- Automatic resource management
- Fault isolation (failed process doesn't affect others)
- Performance monitoring
"""

import asyncio
import multiprocessing
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

from caas_framework.utils.logger import get_logger

# Setup logging
logger = get_logger()


class ExecutionStrategy(Enum):
    """Execution strategy for phase processing"""

    SEQUENTIAL = "sequential"  # Traditional sequential execution
    PROCESS_POOL = "process_pool"  # CPU-bound parallel execution
    THREAD_POOL = "thread_pool"  # I/O-bound parallel execution
    AUTO = "auto"  # Automatically select based on task type


@dataclass
class PhaseExecutionResult:
    """Result from phase execution"""

    phase_id: str
    success: bool
    output: Any
    error: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_seconds: float = 0.0
    worker_id: Optional[int] = None
    memory_mb: float = 0.0

    @property
    def duration_ms(self) -> float:
        """Duration in milliseconds"""
        return self.duration_seconds * 1000


@dataclass
class DependencyGraph:
    """
    Dependency graph for phases

    Represents phase dependencies as a Directed Acyclic Graph (DAG).
    """

    phases: List[str]
    dependencies: Dict[str, List[str]] = field(default_factory=dict)  # phase_id -> [dependency_ids]

    def add_dependency(self, phase_id: str, depends_on: List[str]) -> None:
        """Add dependencies for a phase"""
        if phase_id not in self.phases:
            raise ValueError(f"Phase {phase_id} not in graph")

        for dep in depends_on:
            if dep not in self.phases:
                raise ValueError(f"Dependency {dep} not in graph")

        self.dependencies[phase_id] = depends_on

    def get_dependencies(self, phase_id: str) -> List[str]:
        """Get dependencies for a phase"""
        return self.dependencies.get(phase_id, [])

    def get_ready_phases(self, completed: Set[str]) -> List[str]:
        """Get phases that are ready to execute (all dependencies completed)"""
        ready = []
        for phase_id in self.phases:
            if phase_id in completed:
                continue

            deps = self.get_dependencies(phase_id)
            if all(dep in completed for dep in deps):
                ready.append(phase_id)

        return ready

    def validate_dag(self) -> bool:
        """Validate that the graph is a DAG (no cycles)"""
        visited = set()
        rec_stack = set()

        def has_cycle(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)

            for neighbor in self.dependencies.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True

            rec_stack.remove(node)
            return False

        for phase in self.phases:
            if phase not in visited:
                if has_cycle(phase):
                    return False

        return True

    def estimate_parallelism(self) -> Dict[str, Any]:
        """Estimate maximum parallelism potential"""
        levels = {}
        completed = set()
        level = 0

        while len(completed) < len(self.phases):
            ready = self.get_ready_phases(completed)
            if not ready:
                break

            levels[level] = ready
            completed.update(ready)
            level += 1

        max_parallel = max(len(phases) for phases in levels.values()) if levels else 1
        avg_parallel = sum(len(phases) for phases in levels.values()) / len(levels) if levels else 1

        return {
            "levels": levels,
            "max_parallelism": max_parallel,
            "avg_parallelism": avg_parallel,
            "critical_path_length": level,
            "speedup_potential": len(self.phases) / level if level > 0 else 1.0,
        }


class DistributedPhaseExecutor:
    """
    Distributed Phase Executor

    Executes phases in parallel using ProcessPoolExecutor or ThreadPoolExecutor,
    respecting dependency constraints defined in a DAG.

    Features:
    - Automatic dependency resolution
    - Parallel execution of independent phases
    - Process/Thread pool management
    - Fault isolation
    - Performance monitoring
    """

    def __init__(
        self,
        strategy: ExecutionStrategy = ExecutionStrategy.AUTO,
        max_workers: Optional[int] = None,
        enable_monitoring: bool = True,
    ):
        """
        Initialize distributed executor

        Args:
            strategy: Execution strategy (auto, process_pool, thread_pool, sequential)
            max_workers: Maximum number of workers (default: CPU count)
            enable_monitoring: Enable performance monitoring
        """
        self.strategy = strategy
        self.max_workers = max_workers or multiprocessing.cpu_count()
        self.enable_monitoring = enable_monitoring

        # Executor instance (created lazily)
        self._executor: Optional[Any] = None

        # Execution state
        self.results: Dict[str, PhaseExecutionResult] = {}
        self.completed: Set[str] = set()
        self.failed: Set[str] = set()

        # Performance metrics
        self.total_start_time: Optional[datetime] = None
        self.total_end_time: Optional[datetime] = None

        logger.info(
            f"DistributedPhaseExecutor initialized: strategy={strategy.value}, workers={self.max_workers}"
        )

    def _get_executor(self):
        """Get or create executor based on strategy"""
        if self._executor is None:
            if self.strategy == ExecutionStrategy.PROCESS_POOL:
                self._executor = ProcessPoolExecutor(max_workers=self.max_workers)
                logger.info(f"Created ProcessPoolExecutor with {self.max_workers} workers")
            elif self.strategy == ExecutionStrategy.THREAD_POOL:
                self._executor = ThreadPoolExecutor(max_workers=self.max_workers)
                logger.info(f"Created ThreadPoolExecutor with {self.max_workers} workers")
            elif self.strategy == ExecutionStrategy.AUTO:
                # Auto-select: use ProcessPool for better isolation
                self._executor = ProcessPoolExecutor(max_workers=self.max_workers)
                logger.info(f"Auto-selected ProcessPoolExecutor with {self.max_workers} workers")
            else:  # SEQUENTIAL
                self._executor = None

        return self._executor

    async def execute_phases(
        self,
        dependency_graph: DependencyGraph,
        phase_functions: Dict[str, Callable],
        phase_inputs: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, PhaseExecutionResult]:
        """
        Execute phases in parallel based on dependency graph

        Args:
            dependency_graph: Dependency graph defining phase relationships
            phase_functions: Dict mapping phase_id to callable function
            phase_inputs: Optional dict of inputs for each phase

        Returns:
            Dict mapping phase_id to PhaseExecutionResult
        """
        # Validate inputs
        if not dependency_graph.validate_dag():
            raise ValueError("Dependency graph contains cycles! Must be a DAG.")

        for phase_id in dependency_graph.phases:
            if phase_id not in phase_functions:
                raise ValueError(f"Missing function for phase: {phase_id}")

        phase_inputs = phase_inputs or {}

        # Log parallelism analysis
        if self.enable_monitoring:
            analysis = dependency_graph.estimate_parallelism()
            logger.info(f"Parallelism analysis:")
            logger.info(f"  Max parallelism: {analysis['max_parallelism']}")
            logger.info(f"  Avg parallelism: {analysis['avg_parallelism']:.2f}")
            logger.info(f"  Critical path: {analysis['critical_path_length']} levels")
            logger.info(f"  Speedup potential: {analysis['speedup_potential']:.2f}x")

        # Reset state
        self.results = {}
        self.completed = set()
        self.failed = set()
        self.total_start_time = datetime.now()

        # Execute phases
        if self.strategy == ExecutionStrategy.SEQUENTIAL:
            await self._execute_sequential(dependency_graph, phase_functions, phase_inputs)
        else:
            await self._execute_parallel(dependency_graph, phase_functions, phase_inputs)

        self.total_end_time = datetime.now()

        # Log summary
        if self.enable_monitoring:
            self._log_execution_summary()

        return self.results

    async def _execute_sequential(
        self,
        dependency_graph: DependencyGraph,
        phase_functions: Dict[str, Callable],
        phase_inputs: Dict[str, Any],
    ) -> None:
        """Execute phases sequentially (no parallelism)"""
        logger.info("Executing phases sequentially...")

        for phase_id in dependency_graph.phases:
            logger.info(f"Executing phase: {phase_id}")

            # Get dependencies' outputs
            dep_outputs = {
                dep: self.results[dep].output
                for dep in dependency_graph.get_dependencies(phase_id)
                if dep in self.results
            }

            # Execute phase
            result = await self._execute_single_phase(
                phase_id, phase_functions[phase_id], phase_inputs.get(phase_id), dep_outputs
            )

            self.results[phase_id] = result

            if result.success:
                self.completed.add(phase_id)
            else:
                self.failed.add(phase_id)
                logger.error(f"Phase {phase_id} failed: {result.error}")
                break  # Stop on failure in sequential mode

    async def _execute_parallel(
        self,
        dependency_graph: DependencyGraph,
        phase_functions: Dict[str, Callable],
        phase_inputs: Dict[str, Any],
    ) -> None:
        """Execute phases in parallel based on dependencies"""
        logger.info("Executing phases in parallel...")

        executor = self._get_executor()
        loop = asyncio.get_event_loop()

        while len(self.completed) + len(self.failed) < len(dependency_graph.phases):
            # Get ready phases
            ready_phases = dependency_graph.get_ready_phases(self.completed)

            if not ready_phases:
                if len(self.completed) + len(self.failed) < len(dependency_graph.phases):
                    logger.error(
                        "No ready phases but not all completed - possible deadlock or failed dependencies"
                    )
                break

            logger.info(f"Ready phases: {ready_phases} (parallel batch)")

            # Execute ready phases in parallel
            tasks = []
            for phase_id in ready_phases:
                # Get dependencies' outputs
                dep_outputs = {
                    dep: self.results[dep].output
                    for dep in dependency_graph.get_dependencies(phase_id)
                    if dep in self.results
                }

                # Submit to executor
                task = loop.run_in_executor(
                    executor,
                    self._execute_phase_sync,
                    phase_id,
                    phase_functions[phase_id],
                    phase_inputs.get(phase_id),
                    dep_outputs,
                )
                tasks.append((phase_id, task))

            # Wait for all tasks in this batch
            for phase_id, task in tasks:
                try:
                    result = await task
                    self.results[phase_id] = result

                    if result.success:
                        self.completed.add(phase_id)
                        logger.info(f"✅ Phase {phase_id} completed in {result.duration_ms:.1f}ms")
                    else:
                        self.failed.add(phase_id)
                        logger.error(f"❌ Phase {phase_id} failed: {result.error}")

                except Exception as e:
                    logger.error(f"❌ Phase {phase_id} execution error: {e}")
                    self.results[phase_id] = PhaseExecutionResult(
                        phase_id=phase_id, success=False, output=None, error=str(e)
                    )
                    self.failed.add(phase_id)

    def _execute_phase_sync(
        self, phase_id: str, phase_function: Callable, phase_input: Any, dep_outputs: Dict[str, Any]
    ) -> PhaseExecutionResult:
        """Execute a single phase synchronously (for ProcessPoolExecutor)"""
        import traceback

        start_time = datetime.now()

        try:
            # Execute phase function
            if asyncio.iscoroutinefunction(phase_function):
                # Handle async functions
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                output = loop.run_until_complete(phase_function(phase_input, dep_outputs))
                loop.close()
            else:
                # Sync function
                output = phase_function(phase_input, dep_outputs)

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            return PhaseExecutionResult(
                phase_id=phase_id,
                success=True,
                output=output,
                start_time=start_time,
                end_time=end_time,
                duration_seconds=duration,
            )

        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            error_msg = f"{type(e).__name__}: {str(e)}"

            logger.error(f"Phase {phase_id} error: {error_msg}")
            logger.error(traceback.format_exc())

            return PhaseExecutionResult(
                phase_id=phase_id,
                success=False,
                output=None,
                error=error_msg,
                start_time=start_time,
                end_time=end_time,
                duration_seconds=duration,
            )

    async def _execute_single_phase(
        self, phase_id: str, phase_function: Callable, phase_input: Any, dep_outputs: Dict[str, Any]
    ) -> PhaseExecutionResult:
        """Execute a single phase asynchronously"""
        start_time = datetime.now()

        try:
            if asyncio.iscoroutinefunction(phase_function):
                output = await phase_function(phase_input, dep_outputs)
            else:
                output = phase_function(phase_input, dep_outputs)

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            return PhaseExecutionResult(
                phase_id=phase_id,
                success=True,
                output=output,
                start_time=start_time,
                end_time=end_time,
                duration_seconds=duration,
            )

        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            return PhaseExecutionResult(
                phase_id=phase_id,
                success=False,
                output=None,
                error=str(e),
                start_time=start_time,
                end_time=end_time,
                duration_seconds=duration,
            )

    def _log_execution_summary(self) -> None:
        """Log execution summary with performance metrics"""
        if not self.total_start_time or not self.total_end_time:
            return

        total_duration = (self.total_end_time - self.total_start_time).total_seconds()

        logger.info("=" * 60)
        logger.info("Execution Summary:")
        logger.info("=" * 60)
        logger.info(f"Total phases: {len(self.results)}")
        logger.info(f"Completed: {len(self.completed)}")
        logger.info(f"Failed: {len(self.failed)}")
        logger.info(f"Total duration: {total_duration:.2f}s")

        if self.results:
            phase_durations = [r.duration_seconds for r in self.results.values()]
            cumulative_duration = sum(phase_durations)

            logger.info(f"Cumulative phase time: {cumulative_duration:.2f}s")
            logger.info(f"Speedup: {cumulative_duration / total_duration:.2f}x")
            logger.info(
                f"Efficiency: {(cumulative_duration / total_duration) / self.max_workers:.2%}"
            )

        logger.info("=" * 60)

    def get_performance_report(self) -> Dict[str, Any]:
        """Generate detailed performance report"""
        if not self.total_start_time or not self.total_end_time:
            return {}

        total_duration = (self.total_end_time - self.total_start_time).total_seconds()
        phase_durations = [r.duration_seconds for r in self.results.values()]
        cumulative_duration = sum(phase_durations)

        return {
            "total_phases": len(self.results),
            "completed": len(self.completed),
            "failed": len(self.failed),
            "total_duration_seconds": total_duration,
            "cumulative_phase_time": cumulative_duration,
            "speedup": cumulative_duration / total_duration if total_duration > 0 else 1.0,
            "efficiency": (
                (cumulative_duration / total_duration) / self.max_workers
                if total_duration > 0
                else 0.0
            ),
            "max_workers": self.max_workers,
            "strategy": self.strategy.value,
            "phase_results": {
                phase_id: {
                    "success": result.success,
                    "duration_ms": result.duration_ms,
                    "error": result.error,
                }
                for phase_id, result in self.results.items()
            },
        }

    def close(self) -> None:
        """Close executor and cleanup resources"""
        if self._executor:
            self._executor.shutdown(wait=True)
            logger.info("Executor shutdown complete")

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
