"""
Task Dependency Validator

Validates task dependencies including circular dependencies, orphan tasks,
and dependency depth.
"""

from typing import Dict, List, Set, Tuple, Optional, Any, Union
from pydantic import BaseModel

from caas_framework.models.validation import DependencyIssue


def _safe_get(obj: Union[Dict, BaseModel], key: str, default: Any = None) -> Any:
    """
    Safely get value from dict or Pydantic model.

    Args:
        obj: Dict or Pydantic model object
        key: Key or attribute name
        default: Default value

    Returns:
        Found value or default
    """
    if isinstance(obj, dict):
        return obj.get(key, default)
    else:
        return getattr(obj, key, default)


class DependencyValidator:
    """Task Dependency Validator"""

    def __init__(self, tasks: List[Dict]):
        """
        Args:
            tasks: Task list [{"id": "task1", "context": ["task0"]}, ...]
        """
        self.tasks = {_safe_get(task, "id"): task for task in tasks}
        self.issues: List[DependencyIssue] = []

    def validate(self) -> Tuple[bool, List[DependencyIssue]]:
        """
        Validate all dependencies.

        Returns:
            (is_valid, issues)
        """
        self.issues = []

        # 1. Check circular dependencies
        self._check_circular_dependencies()

        # 2. Check orphan tasks
        self._check_orphan_tasks()

        # 3. Check dependency depth
        self._check_dependency_depth()

        # 4. Check missing references
        self._check_missing_references()

        # Invalid if any errors
        has_errors = any(issue.severity == "error" for issue in self.issues)
        return (not has_errors, self.issues)

    def _check_circular_dependencies(self) -> None:
        """Detect circular dependencies using DFS"""

        def dfs(task_id: str, visited: Set[str], rec_stack: Set[str], path: List[str]) -> Optional[List[str]]:
            """
            Depth-first search.

            Returns:
                Circular path (if cycle detected) or None
            """
            visited.add(task_id)
            rec_stack.add(task_id)
            path.append(task_id)

            # Explore dependencies (context)
            dependencies = _safe_get(self.tasks[task_id], "context", [])
            for dep_id in dependencies:
                if dep_id not in self.tasks:
                    continue  # Missing tasks checked separately

                if dep_id not in visited:
                    # Recursive exploration
                    cycle_path = dfs(dep_id, visited, rec_stack, path.copy())
                    if cycle_path:
                        return cycle_path
                elif dep_id in rec_stack:
                    # Cycle detected!
                    cycle_start = path.index(dep_id)
                    return path[cycle_start:] + [dep_id]

            rec_stack.remove(task_id)
            return None

        visited = set()
        for task_id in self.tasks:
            if task_id not in visited:
                cycle_path = dfs(task_id, visited, set(), [])
                if cycle_path:
                    self.issues.append(DependencyIssue(
                        severity="error",
                        task_id=task_id,
                        message=f"Circular dependency detected",
                        path=cycle_path
                    ))

    def _check_orphan_tasks(self) -> None:
        """Detect orphan tasks (unreachable from dependency graph)"""

        # Start tasks (no dependencies)
        start_tasks = [
            task_id for task_id, task in self.tasks.items()
            if not _safe_get(task, "context")
        ]

        # Find all reachable tasks from start tasks (BFS)
        reachable = set()
        queue = start_tasks.copy()

        while queue:
            current = queue.pop(0)
            if current in reachable:
                continue
            reachable.add(current)

            # Find tasks that depend on current task
            for task_id, task in self.tasks.items():
                if current in _safe_get(task, "context", []) and task_id not in reachable:
                    queue.append(task_id)

        # Unreachable tasks = orphan tasks
        for task_id in self.tasks:
            if task_id not in reachable:
                self.issues.append(DependencyIssue(
                    severity="warning",
                    task_id=task_id,
                    message=f"Orphan task: unreachable from start tasks (broken dependency chain)"
                ))

    def _check_dependency_depth(self, max_depth: int = 10) -> None:
        """Validate dependency depth (check for overly deep dependency chains)"""

        def get_depth(task_id: str, visited: Set[str] = None) -> int:
            if visited is None:
                visited = set()

            if task_id in visited:
                return 0  # Prevent cycles

            visited.add(task_id)
            dependencies = _safe_get(self.tasks[task_id], "context", [])

            if not dependencies:
                return 0

            max_dep_depth = 0
            for dep_id in dependencies:
                if dep_id in self.tasks:
                    max_dep_depth = max(max_dep_depth, get_depth(dep_id, visited.copy()))

            return max_dep_depth + 1

        for task_id in self.tasks:
            depth = get_depth(task_id)
            if depth > max_depth:
                self.issues.append(DependencyIssue(
                    severity="warning",
                    task_id=task_id,
                    message=f"Dependency depth too deep (depth: {depth}, max: {max_depth})"
                ))

    def _check_missing_references(self) -> None:
        """Validate non-existent task references"""

        for task_id, task in self.tasks.items():
            dependencies = _safe_get(task, "context", [])
            for dep_id in dependencies:
                if dep_id not in self.tasks:
                    self.issues.append(DependencyIssue(
                        severity="error",
                        task_id=task_id,
                        message=f"References non-existent task '{dep_id}'"
                    ))

    def get_execution_order(self) -> Optional[List[str]]:
        """
        Generate execution order using topological sort.

        Returns:
            Execution order list or None (if circular dependencies exist)
        """
        # Check for circular dependencies
        if any(issue.severity == "error" and "Circular" in issue.message for issue in self.issues):
            return None

        # Calculate in-degree
        in_degree = {task_id: 0 for task_id in self.tasks}
        for task in self.tasks.values():
            for dep_id in _safe_get(task, "context", []):
                if dep_id in in_degree:
                    in_degree[dep_id] += 1

        # Start with nodes having in-degree 0
        queue = [task_id for task_id, degree in in_degree.items() if degree == 0]
        result = []

        while queue:
            task_id = queue.pop(0)
            result.append(task_id)

            # Remove dependencies
            for other_id, other_task in self.tasks.items():
                if task_id in _safe_get(other_task, "context", []):
                    in_degree[other_id] -= 1
                    if in_degree[other_id] == 0:
                        queue.append(other_id)

        # Check if all tasks are included
        if len(result) != len(self.tasks):
            return None

        return result
