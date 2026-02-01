"""
태스크 의존성 검증

순환 의존성, 고아 태스크, 의존성 깊이 등을 검증합니다.
"""

from typing import Dict, List, Set, Tuple, Optional, Any, Union
from dataclasses import dataclass
from pydantic import BaseModel


def _safe_get(obj: Union[Dict, BaseModel], key: str, default: Any = None) -> Any:
    """
    사전 또는 Pydantic 모델에서 안전하게 값을 가져옵니다.

    Args:
        obj: 사전 또는 Pydantic 모델 객체
        key: 키 또는 속성 이름
        default: 기본값

    Returns:
        찾은 값 또는 기본값
    """
    if isinstance(obj, dict):
        return obj.get(key, default)
    else:
        # Pydantic 모델
        return getattr(obj, key, default)


@dataclass
class DependencyIssue:
    """의존성 이슈"""
    severity: str  # error, warning, info
    task_id: str
    message: str
    path: Optional[List[str]] = None


class DependencyValidator:
    """태스크 의존성 검증기"""

    def __init__(self, tasks: List[Dict]):
        """
        Args:
            tasks: 태스크 리스트 [{"id": "task1", "context": ["task0"]}, ...]
        """
        self.tasks = {_safe_get(task, "id"): task for task in tasks}
        self.issues: List[DependencyIssue] = []

    def validate(self) -> Tuple[bool, List[DependencyIssue]]:
        """
        전체 의존성 검증

        Returns:
            (is_valid, issues)
        """
        self.issues = []

        # 1. 순환 의존성 검증
        self._check_circular_dependencies()

        # 2. 고아 태스크 검증 (의존 불가능한 태스크)
        self._check_orphan_tasks()

        # 3. 의존성 깊이 검증
        self._check_dependency_depth()

        # 4. 존재하지 않는 태스크 참조
        self._check_missing_references()

        # 에러가 하나라도 있으면 invalid
        has_errors = any(issue.severity == "error" for issue in self.issues)
        return (not has_errors, self.issues)

    def _check_circular_dependencies(self) -> None:
        """DFS로 순환 의존성 감지"""

        def dfs(task_id: str, visited: Set[str], rec_stack: Set[str], path: List[str]) -> Optional[List[str]]:
            """
            깊이 우선 탐색

            Returns:
                순환 경로 (순환 발견 시) 또는 None
            """
            visited.add(task_id)
            rec_stack.add(task_id)
            path.append(task_id)

            # 의존성(context) 탐색
            dependencies = _safe_get(self.tasks[task_id], "context", [])
            for dep_id in dependencies:
                if dep_id not in self.tasks:
                    continue  # 존재하지 않는 태스크는 별도 검증

                if dep_id not in visited:
                    # 재귀 탐색
                    cycle_path = dfs(dep_id, visited, rec_stack, path.copy())
                    if cycle_path:
                        return cycle_path
                elif dep_id in rec_stack:
                    # 순환 발견!
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
                        message=f"순환 의존성 발견",
                        path=cycle_path
                    ))

    def _check_orphan_tasks(self) -> None:
        """고아 태스크 감지 (의존성 그래프에서 도달 불가능한 태스크)"""

        # 시작 태스크 (의존성 없음)
        start_tasks = [
            task_id for task_id, task in self.tasks.items()
            if not _safe_get(task, "context")
        ]

        # 시작 태스크로부터 도달 가능한 모든 태스크 찾기 (BFS)
        reachable = set()
        queue = start_tasks.copy()

        while queue:
            current = queue.pop(0)
            if current in reachable:
                continue
            reachable.add(current)

            # 이 태스크를 의존하는 다른 태스크들 찾기
            for task_id, task in self.tasks.items():
                if current in _safe_get(task, "context", []) and task_id not in reachable:
                    queue.append(task_id)

        # 도달 불가능한 태스크 = 고아 태스크
        for task_id in self.tasks:
            if task_id not in reachable:
                self.issues.append(DependencyIssue(
                    severity="warning",
                    task_id=task_id,
                    message=f"고아 태스크: 시작 태스크로부터 도달할 수 없습니다 (의존성 체인이 끊어짐)"
                ))

    def _check_dependency_depth(self, max_depth: int = 10) -> None:
        """의존성 깊이 검증 (너무 깊은 의존성 체인)"""

        def get_depth(task_id: str, visited: Set[str] = None) -> int:
            if visited is None:
                visited = set()

            if task_id in visited:
                return 0  # 순환 방지

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
                    message=f"의존성 깊이가 너무 깊습니다 (깊이: {depth}, 최대: {max_depth})"
                ))

    def _check_missing_references(self) -> None:
        """존재하지 않는 태스크 참조 검증"""

        for task_id, task in self.tasks.items():
            dependencies = _safe_get(task, "context", [])
            for dep_id in dependencies:
                if dep_id not in self.tasks:
                    self.issues.append(DependencyIssue(
                        severity="error",
                        task_id=task_id,
                        message=f"존재하지 않는 태스크 '{dep_id}'를 참조합니다"
                    ))

    def get_execution_order(self) -> Optional[List[str]]:
        """
        위상 정렬(Topological Sort)로 실행 순서 생성

        Returns:
            실행 순서 리스트 또는 None (순환 의존성 있는 경우)
        """
        # 순환 의존성 체크
        if any(issue.severity == "error" and "순환" in issue.message for issue in self.issues):
            return None

        # 진입 차수 계산
        in_degree = {task_id: 0 for task_id in self.tasks}
        for task in self.tasks.values():
            for dep_id in _safe_get(task, "context", []):
                if dep_id in in_degree:
                    in_degree[dep_id] += 1

        # 진입 차수 0인 노드로 시작
        queue = [task_id for task_id, degree in in_degree.items() if degree == 0]
        result = []

        while queue:
            task_id = queue.pop(0)
            result.append(task_id)

            # 의존성 제거
            for other_id, other_task in self.tasks.items():
                if task_id in _safe_get(other_task, "context", []):
                    in_degree[other_id] -= 1
                    if in_degree[other_id] == 0:
                        queue.append(other_id)

        # 모든 태스크가 포함되었는지 확인
        if len(result) != len(self.tasks):
            return None

        return result
