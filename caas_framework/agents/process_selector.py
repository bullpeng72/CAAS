"""
Process Selector for CrewAI

Automatically selects the optimal CrewAI Process type (Sequential vs Hierarchical)
based on task dependencies and agent collaboration patterns.
"""

from typing import List, Dict, Set
from enum import Enum
import logging

from caas_framework.models.specifications import AgentSpecModel, TaskSpecModel

logger = logging.getLogger(__name__)


class ProcessType(str, Enum):
    """CrewAI Process types"""
    SEQUENTIAL = "sequential"
    HIERARCHICAL = "hierarchical"


class DependencyAnalysis:
    """Results of task dependency analysis"""

    def __init__(
        self,
        dependencies: Dict[str, List[str]],
        independent_tasks: List[str],
        max_dependency_depth: int,
        has_circular_deps: bool,
        complexity_score: float
    ):
        self.dependencies = dependencies
        self.independent_tasks = independent_tasks
        self.max_dependency_depth = max_dependency_depth
        self.has_circular_deps = has_circular_deps
        self.complexity_score = complexity_score


class ProcessSelector:
    """
    Intelligent Process Type Selector

    Analyzes task dependencies and agent collaboration patterns
    to select the optimal CrewAI Process type.
    """

    def __init__(
        self,
        prefer_hierarchical_threshold: float = 0.5,
        max_sequential_depth: int = 5
    ):
        """
        Initialize ProcessSelector.

        Args:
            prefer_hierarchical_threshold: Ratio of independent tasks to prefer hierarchical
            max_sequential_depth: Maximum dependency depth before preferring hierarchical
        """
        self.prefer_hierarchical_threshold = prefer_hierarchical_threshold
        self.max_sequential_depth = max_sequential_depth

    def select_process(
        self,
        tasks: List[TaskSpecModel],
        agents: List[AgentSpecModel],
        verbose: bool = True
    ) -> ProcessType:
        """
        Select the optimal Process type.

        Args:
            tasks: List of task specifications
            agents: List of agent specifications
            verbose: Whether to log decision reasoning

        Returns:
            ProcessType (SEQUENTIAL or HIERARCHICAL)
        """
        if not tasks:
            return ProcessType.SEQUENTIAL

        # Analyze task dependencies
        dep_analysis = self.analyze_dependencies(tasks)

        # Calculate decision factors
        independent_ratio = len(dep_analysis.independent_tasks) / len(tasks)
        has_complex_deps = dep_analysis.max_dependency_depth > self.max_sequential_depth
        has_many_parallel = independent_ratio > self.prefer_hierarchical_threshold

        # Decision logic
        if dep_analysis.has_circular_deps:
            # Circular dependencies require hierarchical with manager
            decision = ProcessType.HIERARCHICAL
            reason = "Circular dependencies detected - requires manager coordination"

        elif has_complex_deps:
            # Deep dependency chains benefit from hierarchical
            decision = ProcessType.HIERARCHICAL
            reason = f"Complex dependencies (depth={dep_analysis.max_dependency_depth}) - manager can optimize"

        elif has_many_parallel:
            # Many independent tasks can run in parallel
            decision = ProcessType.HIERARCHICAL
            reason = f"High parallelism potential ({independent_ratio:.1%} independent tasks)"

        elif len(agents) > 5 and dep_analysis.complexity_score > 0.7:
            # Many agents with complex interactions
            decision = ProcessType.HIERARCHICAL
            reason = f"Complex multi-agent system ({len(agents)} agents, complexity={dep_analysis.complexity_score:.2f})"

        else:
            # Default to sequential for simple cases
            decision = ProcessType.SEQUENTIAL
            reason = "Simple sequential workflow is sufficient"

        if verbose:
            logger.info(f"\n{'='*70}")
            logger.info(f"🔍 Process Selection Analysis")
            logger.info(f"{'='*70}")
            logger.info(f"Total tasks: {len(tasks)}")
            logger.info(f"Total agents: {len(agents)}")
            logger.info(f"Independent tasks: {len(dep_analysis.independent_tasks)} ({independent_ratio:.1%})")
            logger.info(f"Max dependency depth: {dep_analysis.max_dependency_depth}")
            logger.info(f"Complexity score: {dep_analysis.complexity_score:.2f}")
            logger.info(f"Has circular dependencies: {dep_analysis.has_circular_deps}")
            logger.info(f"\n✅ Selected Process: {decision.value.upper()}")
            logger.info(f"📝 Reason: {reason}")
            logger.info(f"{'='*70}\n")

        return decision

    def analyze_dependencies(self, tasks: List[TaskSpecModel]) -> DependencyAnalysis:
        """
        Analyze task dependencies.

        Args:
            tasks: List of task specifications

        Returns:
            DependencyAnalysis with dependency graph and metrics
        """
        # Build dependency graph
        dependencies: Dict[str, List[str]] = {}
        task_ids = {task.id for task in tasks}

        for task in tasks:
            task_id = task.id
            dependencies[task_id] = []

            # Extract dependencies from context field
            if task.context:
                for dep_id in task.context:
                    if dep_id in task_ids:
                        dependencies[task_id].append(dep_id)

            # Also check description for references to other tasks
            # Pattern: "using the result from task_X" or "after task_Y completes"
            for other_task in tasks:
                if other_task.id != task_id and other_task.id in task.description:
                    if other_task.id not in dependencies[task_id]:
                        dependencies[task_id].append(other_task.id)

        # Find independent tasks
        independent_tasks = [
            task_id for task_id, deps in dependencies.items()
            if not deps
        ]

        # Calculate max dependency depth
        max_depth = self._calculate_max_depth(dependencies)

        # Check for circular dependencies
        has_circular = self._has_circular_dependencies(dependencies)

        # Calculate complexity score
        complexity = self._calculate_complexity(dependencies, len(tasks))

        return DependencyAnalysis(
            dependencies=dependencies,
            independent_tasks=independent_tasks,
            max_dependency_depth=max_depth,
            has_circular_deps=has_circular,
            complexity_score=complexity
        )

    def _calculate_max_depth(self, dependencies: Dict[str, List[str]]) -> int:
        """Calculate maximum dependency depth using DFS."""
        visited: Set[str] = set()
        max_depth = 0

        def dfs(task_id: str, depth: int) -> int:
            if task_id in visited:
                return depth

            visited.add(task_id)
            current_max = depth

            for dep_id in dependencies.get(task_id, []):
                dep_depth = dfs(dep_id, depth + 1)
                current_max = max(current_max, dep_depth)

            return current_max

        for task_id in dependencies:
            visited.clear()
            depth = dfs(task_id, 0)
            max_depth = max(max_depth, depth)

        return max_depth

    def _has_circular_dependencies(self, dependencies: Dict[str, List[str]]) -> bool:
        """Check for circular dependencies using DFS."""
        visited: Set[str] = set()
        rec_stack: Set[str] = set()

        def has_cycle(task_id: str) -> bool:
            visited.add(task_id)
            rec_stack.add(task_id)

            for dep_id in dependencies.get(task_id, []):
                if dep_id not in visited:
                    if has_cycle(dep_id):
                        return True
                elif dep_id in rec_stack:
                    return True

            rec_stack.remove(task_id)
            return False

        for task_id in dependencies:
            if task_id not in visited:
                if has_cycle(task_id):
                    return True

        return False

    def _calculate_complexity(
        self,
        dependencies: Dict[str, List[str]],
        total_tasks: int
    ) -> float:
        """
        Calculate dependency complexity score (0.0-1.0).

        Factors:
        - Average number of dependencies per task
        - Variance in dependency distribution
        - Ratio of dependent tasks
        """
        if total_tasks == 0:
            return 0.0

        # Average dependencies
        total_deps = sum(len(deps) for deps in dependencies.values())
        avg_deps = total_deps / total_tasks

        # Ratio of tasks with dependencies
        dependent_tasks = sum(1 for deps in dependencies.values() if deps)
        dependency_ratio = dependent_tasks / total_tasks

        # Max dependencies for any single task
        max_deps = max((len(deps) for deps in dependencies.values()), default=0)

        # Normalize to 0.0-1.0
        # High complexity = many dependencies, high variance, many dependent tasks
        complexity = (
            (avg_deps / max(total_tasks, 1)) * 0.4 +  # 40% weight on avg deps
            dependency_ratio * 0.3 +  # 30% weight on dependency ratio
            (max_deps / max(total_tasks, 1)) * 0.3  # 30% weight on max deps
        )

        return min(complexity, 1.0)

    def get_process_recommendation_summary(
        self,
        tasks: List[TaskSpecModel],
        agents: List[AgentSpecModel]
    ) -> Dict[str, any]:
        """
        Get detailed recommendation summary.

        Args:
            tasks: List of task specifications
            agents: List of agent specifications

        Returns:
            Dictionary with recommendation details
        """
        dep_analysis = self.analyze_dependencies(tasks)
        selected_process = self.select_process(tasks, agents, verbose=False)

        return {
            'selected_process': selected_process.value,
            'total_tasks': len(tasks),
            'total_agents': len(agents),
            'independent_tasks': len(dep_analysis.independent_tasks),
            'independent_ratio': len(dep_analysis.independent_tasks) / len(tasks) if tasks else 0,
            'max_dependency_depth': dep_analysis.max_dependency_depth,
            'complexity_score': dep_analysis.complexity_score,
            'has_circular_dependencies': dep_analysis.has_circular_deps,
            'dependencies': dep_analysis.dependencies
        }


def create_process_selector(
    prefer_hierarchical_threshold: float = 0.5,
    max_sequential_depth: int = 5
) -> ProcessSelector:
    """
    Factory function to create ProcessSelector.

    Args:
        prefer_hierarchical_threshold: Ratio of independent tasks to prefer hierarchical
        max_sequential_depth: Maximum dependency depth before preferring hierarchical

    Returns:
        ProcessSelector instance
    """
    return ProcessSelector(
        prefer_hierarchical_threshold=prefer_hierarchical_threshold,
        max_sequential_depth=max_sequential_depth
    )
