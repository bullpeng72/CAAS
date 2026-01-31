"""
Design Validator

Agent와 Task 설계의 일관성을 검증하는 Rule-based Validator
"""

from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass
from enum import Enum

from app.utils.logger import get_logger

logger = get_logger("validation.design")


class IssueSeverity(str, Enum):
    """이슈 심각도"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class IssueCategory(str, Enum):
    """이슈 카테고리"""
    COVERAGE = "coverage"
    CONSISTENCY = "consistency"
    DEPENDENCY = "dependency"
    COMPLETENESS = "completeness"
    TOOL_MISMATCH = "tool_mismatch"


@dataclass
class ValidationIssue:
    """검증 이슈"""
    severity: IssueSeverity
    category: IssueCategory
    message: str
    suggestion: str
    fixable: bool = False
    fix_data: Optional[Dict[str, Any]] = None


@dataclass
class ValidationResult:
    """검증 결과"""
    is_valid: bool
    validation_score: int
    issues: List[ValidationIssue]
    coverage: Dict[str, Any]
    recommendations: List[str]


class DesignValidator:
    """
    Agent와 Task 설계 검증기

    Rule-based 검증으로 일관성 있는 결과 제공
    """

    def __init__(self):
        self.logger = logger

    def validate(
        self,
        agents: List[Dict[str, Any]],
        tasks: List[Dict[str, Any]],
        requirements: Optional[List[Dict[str, Any]]] = None
    ) -> ValidationResult:
        """
        Agent와 Task 설계를 검증합니다.

        Args:
            agents: 에이전트 리스트
            tasks: 태스크 리스트
            requirements: 요구사항 리스트 (선택)

        Returns:
            ValidationResult: 검증 결과
        """
        issues = []

        # 1. Completeness Check (필수 필드 확인)
        issues.extend(self._check_completeness(agents, tasks))

        # 2. Agent-Task Assignment Check (태스크가 올바른 에이전트에 할당되었는지)
        issues.extend(self._check_agent_task_assignment(agents, tasks))

        # 3. Tool Consistency Check (Agent와 Task의 도구 일관성)
        issues.extend(self._check_tool_consistency(agents, tasks))

        # 4. Dependency Check (태스크 의존성 확인)
        issues.extend(self._check_dependencies(tasks))

        # 5. Coverage Check (요구사항이 제공된 경우)
        coverage = {"requirements_covered": 0, "requirements_total": 0, "coverage_percentage": 100}
        if requirements:
            coverage_issues, coverage = self._check_coverage(agents, tasks, requirements)
            issues.extend(coverage_issues)

        # 검증 점수 계산
        validation_score = self._calculate_score(issues, len(agents), len(tasks))

        # 검증 통과 여부 (에러가 없으면 통과)
        is_valid = not any(issue.severity == IssueSeverity.ERROR for issue in issues)

        # 권장사항 생성
        recommendations = self._generate_recommendations(agents, tasks, issues)

        self.logger.info(
            f"검증 완료: valid={is_valid}, score={validation_score}, "
            f"issues={len(issues)} (errors={sum(1 for i in issues if i.severity == IssueSeverity.ERROR)})"
        )

        return ValidationResult(
            is_valid=is_valid,
            validation_score=validation_score,
            issues=issues,
            coverage=coverage,
            recommendations=recommendations
        )

    def _check_completeness(
        self,
        agents: List[Dict[str, Any]],
        tasks: List[Dict[str, Any]]
    ) -> List[ValidationIssue]:
        """
        필수 필드가 모두 채워져 있는지 확인
        """
        issues = []

        # Agent 필수 필드
        for idx, agent in enumerate(agents):
            agent_name = agent.get("role", f"Agent {idx+1}")

            if not agent.get("role"):
                issues.append(ValidationIssue(
                    severity=IssueSeverity.ERROR,
                    category=IssueCategory.COMPLETENESS,
                    message=f"Agent {idx+1}: 'role' 필드가 누락되었습니다.",
                    suggestion="Agent에 역할(role)을 지정하세요.",
                    fixable=False
                ))

            if not agent.get("goal"):
                issues.append(ValidationIssue(
                    severity=IssueSeverity.ERROR,
                    category=IssueCategory.COMPLETENESS,
                    message=f"'{agent_name}' agent: 'goal' 필드가 누락되었습니다.",
                    suggestion="Agent의 목표(goal)를 명확히 작성하세요.",
                    fixable=False
                ))

            if not agent.get("backstory"):
                issues.append(ValidationIssue(
                    severity=IssueSeverity.WARNING,
                    category=IssueCategory.COMPLETENESS,
                    message=f"'{agent_name}' agent: 'backstory' 필드가 누락되었습니다.",
                    suggestion="Agent의 배경 스토리(backstory)를 추가하면 성능이 향상됩니다.",
                    fixable=False
                ))

        # Task 필수 필드
        for idx, task in enumerate(tasks):
            if not task.get("description"):
                issues.append(ValidationIssue(
                    severity=IssueSeverity.ERROR,
                    category=IssueCategory.COMPLETENESS,
                    message=f"Task {idx+1}: 'description' 필드가 누락되었습니다.",
                    suggestion="Task의 설명(description)을 작성하세요.",
                    fixable=False
                ))

            if not task.get("expected_output"):
                issues.append(ValidationIssue(
                    severity=IssueSeverity.WARNING,
                    category=IssueCategory.COMPLETENESS,
                    message=f"Task {idx+1}: 'expected_output' 필드가 누락되었습니다.",
                    suggestion="예상 출력(expected_output)을 명확히 작성하세요.",
                    fixable=False
                ))

            if not task.get("agent"):
                issues.append(ValidationIssue(
                    severity=IssueSeverity.ERROR,
                    category=IssueCategory.COMPLETENESS,
                    message=f"Task {idx+1}: 'agent' 필드가 누락되었습니다.",
                    suggestion="Task에 담당 Agent를 할당하세요.",
                    fixable=False
                ))

        return issues

    def _check_agent_task_assignment(
        self,
        agents: List[Dict[str, Any]],
        tasks: List[Dict[str, Any]]
    ) -> List[ValidationIssue]:
        """
        Task가 존재하는 Agent에 할당되었는지 확인
        """
        issues = []

        agent_roles = {agent.get("role") for agent in agents if agent.get("role")}

        for idx, task in enumerate(tasks):
            assigned_agent = task.get("agent")
            if assigned_agent and assigned_agent not in agent_roles:
                issues.append(ValidationIssue(
                    severity=IssueSeverity.ERROR,
                    category=IssueCategory.CONSISTENCY,
                    message=f"Task {idx+1}: 존재하지 않는 Agent '{assigned_agent}'에 할당되었습니다.",
                    suggestion=f"다음 중 하나의 Agent를 선택하세요: {', '.join(agent_roles)}",
                    fixable=False
                ))

        # 사용되지 않는 Agent 확인
        assigned_agents = {task.get("agent") for task in tasks if task.get("agent")}
        unused_agents = agent_roles - assigned_agents

        if unused_agents:
            issues.append(ValidationIssue(
                severity=IssueSeverity.INFO,
                category=IssueCategory.CONSISTENCY,
                message=f"사용되지 않는 Agent가 있습니다: {', '.join(unused_agents)}",
                suggestion="사용하지 않는 Agent는 제거하거나 Task를 할당하세요.",
                fixable=False
            ))

        return issues

    def _check_tool_consistency(
        self,
        agents: List[Dict[str, Any]],
        tasks: List[Dict[str, Any]]
    ) -> List[ValidationIssue]:
        """
        Agent와 Task의 도구 일관성 확인

        핵심: Task에 명시된 도구가 담당 Agent의 도구에 포함되어 있는지 확인
        """
        issues = []

        # Agent별 도구 맵 생성
        agent_tools_map = {}
        for agent in agents:
            role = agent.get("role")
            if role:
                agent_tools_map[role] = set(agent.get("tools", []))

        # Task별 도구 확인
        for idx, task in enumerate(tasks):
            task_tools = set(task.get("tools", []))
            assigned_agent = task.get("agent")

            if not assigned_agent:
                continue

            agent_tools = agent_tools_map.get(assigned_agent, set())

            # Task에만 있고 Agent에 없는 도구 찾기
            tools_not_in_agent = task_tools - agent_tools

            if tools_not_in_agent:
                for tool in tools_not_in_agent:
                    issues.append(ValidationIssue(
                        severity=IssueSeverity.WARNING,
                        category=IssueCategory.TOOL_MISMATCH,
                        message=f"Task {idx+1}은 '{tool}' 도구를 사용하지만, 담당 Agent '{assigned_agent}'에는 이 도구가 없습니다.",
                        suggestion=f"'{assigned_agent}' Agent의 도구 목록에 '{tool}'을 추가하세요.",
                        fixable=True,
                        fix_data={
                            "type": "add_tool_to_agent",
                            "agent_role": assigned_agent,
                            "tool": tool
                        }
                    ))

            # Agent에는 있지만 Task에 없는 도구 (정보성)
            tools_in_agent_not_task = agent_tools - task_tools

            if tools_in_agent_not_task and task_tools:
                # Task에 도구가 명시되어 있는데 Agent의 일부 도구만 사용하는 경우
                issues.append(ValidationIssue(
                    severity=IssueSeverity.INFO,
                    category=IssueCategory.TOOL_MISMATCH,
                    message=f"Task {idx+1}은 Agent '{assigned_agent}'의 일부 도구만 사용합니다. Agent는 {len(agent_tools)}개 도구를 가지고 있지만 Task는 {len(task_tools)}개만 사용합니다.",
                    suggestion="Task에 도구를 명시하지 않으면 Agent의 모든 도구를 사용할 수 있습니다.",
                    fixable=False
                ))

        # Agent 도구 없음 경고
        for agent in agents:
            role = agent.get("role")
            tools = agent.get("tools", [])

            if not tools:
                issues.append(ValidationIssue(
                    severity=IssueSeverity.WARNING,
                    category=IssueCategory.COMPLETENESS,
                    message=f"'{role}' agent: 도구가 지정되지 않았습니다.",
                    suggestion="Agent에 필요한 도구를 추가하세요 (예: web_search, file_read 등).",
                    fixable=False
                ))

        return issues

    def _check_dependencies(
        self,
        tasks: List[Dict[str, Any]]
    ) -> List[ValidationIssue]:
        """
        Task dependencies (context) 확인
        """
        issues = []

        # 전체 태스크에 dependencies가 하나도 없는 경우
        total_deps = sum(len(task.get("context", [])) for task in tasks)

        if total_deps == 0 and len(tasks) > 1:
            issues.append(ValidationIssue(
                severity=IssueSeverity.INFO,
                category=IssueCategory.DEPENDENCY,
                message="Task dependencies (context)가 정의되지 않았습니다. 모든 Task가 독립적으로 실행됩니다.",
                suggestion="Task 간 의존성이 있다면 context 필드에 선행 Task를 지정하세요.",
                fixable=True,
                fix_data={
                    "type": "suggest_dependencies"
                }
            ))

        # 순환 의존성 확인
        circular_deps = self._find_circular_dependencies(tasks)
        if circular_deps:
            issues.append(ValidationIssue(
                severity=IssueSeverity.ERROR,
                category=IssueCategory.DEPENDENCY,
                message=f"순환 의존성이 발견되었습니다: {' -> '.join(circular_deps)}",
                suggestion="Task dependencies를 재구성하여 순환 참조를 제거하세요.",
                fixable=False
            ))

        # 존재하지 않는 Task 참조 확인
        task_names = {f"Task {i+1}" for i in range(len(tasks))}

        for idx, task in enumerate(tasks):
            context = task.get("context", [])
            for dep in context:
                if dep not in task_names:
                    issues.append(ValidationIssue(
                        severity=IssueSeverity.ERROR,
                        category=IssueCategory.DEPENDENCY,
                        message=f"Task {idx+1}: 존재하지 않는 Task '{dep}'를 참조합니다.",
                        suggestion="올바른 Task 이름을 사용하세요.",
                        fixable=False
                    ))

        return issues

    def _find_circular_dependencies(self, tasks: List[Dict[str, Any]]) -> List[str]:
        """
        순환 의존성 탐지
        """
        # 간단한 DFS 기반 순환 탐지
        graph = {}
        for idx, task in enumerate(tasks):
            task_name = f"Task {idx+1}"
            graph[task_name] = task.get("context", [])

        visited = set()
        rec_stack = set()

        def has_cycle(node, path):
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor, path):
                        return True
                elif neighbor in rec_stack:
                    # 순환 발견
                    cycle_start = path.index(neighbor)
                    return path[cycle_start:]

            path.pop()
            rec_stack.remove(node)
            return False

        for node in graph:
            if node not in visited:
                result = has_cycle(node, [])
                if result:
                    return result

        return []

    def _check_coverage(
        self,
        agents: List[Dict[str, Any]],
        tasks: List[Dict[str, Any]],
        requirements: List[Dict[str, Any]]
    ) -> tuple[List[ValidationIssue], Dict[str, Any]]:
        """
        요구사항 커버리지 확인
        """
        issues = []

        # 간단한 키워드 매칭으로 커버리지 계산
        covered_count = 0

        for req in requirements:
            req_text = str(req).lower()
            covered = False

            for task in tasks:
                task_text = f"{task.get('description', '')} {task.get('expected_output', '')}".lower()
                if any(word in task_text for word in req_text.split()[:3]):  # 상위 3개 키워드 매칭
                    covered = True
                    break

            if covered:
                covered_count += 1

        total_count = len(requirements)
        coverage_percentage = (covered_count / total_count * 100) if total_count > 0 else 100

        if coverage_percentage < 70:
            issues.append(ValidationIssue(
                severity=IssueSeverity.WARNING,
                category=IssueCategory.COVERAGE,
                message=f"요구사항 커버리지가 낮습니다 ({coverage_percentage:.1f}%).",
                suggestion="추가 Agent 또는 Task를 생성하여 모든 요구사항을 커버하세요.",
                fixable=False
            ))

        coverage = {
            "requirements_covered": covered_count,
            "requirements_total": total_count,
            "coverage_percentage": round(coverage_percentage, 1)
        }

        return issues, coverage

    def _calculate_score(
        self,
        issues: List[ValidationIssue],
        num_agents: int,
        num_tasks: int
    ) -> int:
        """
        검증 점수 계산 (0-100)
        """
        # 기본 점수 100에서 시작
        score = 100

        # 이슈별 감점
        for issue in issues:
            if issue.severity == IssueSeverity.ERROR:
                score -= 20
            elif issue.severity == IssueSeverity.WARNING:
                score -= 10
            elif issue.severity == IssueSeverity.INFO:
                score -= 2

        # 최소 0점
        score = max(0, score)

        return score

    def _generate_recommendations(
        self,
        agents: List[Dict[str, Any]],
        tasks: List[Dict[str, Any]],
        issues: List[ValidationIssue]
    ) -> List[str]:
        """
        권장사항 생성
        """
        recommendations = []

        # 이슈 기반 권장사항
        error_count = sum(1 for i in issues if i.severity == IssueSeverity.ERROR)
        warning_count = sum(1 for i in issues if i.severity == IssueSeverity.WARNING)

        if error_count > 0:
            recommendations.append(f"🔴 {error_count}개의 오류를 수정하세요. 오류가 있으면 코드 생성이 실패할 수 있습니다.")

        if warning_count > 0:
            recommendations.append(f"⚠️ {warning_count}개의 경고를 확인하세요. 경고는 선택사항이지만 품질 향상에 도움이 됩니다.")

        # Agent/Task 비율 권장사항
        if len(tasks) > len(agents) * 3:
            recommendations.append("💡 Task가 Agent에 비해 너무 많습니다. Agent를 추가하거나 Task를 통합하는 것을 고려하세요.")

        if len(agents) > len(tasks):
            recommendations.append("💡 Agent가 Task에 비해 많습니다. 사용하지 않는 Agent는 제거하세요.")

        # 도구 권장사항
        agents_without_tools = sum(1 for agent in agents if not agent.get("tools"))
        if agents_without_tools > 0:
            recommendations.append(f"🔧 {agents_without_tools}개 Agent에 도구가 없습니다. 도구를 추가하면 Agent의 능력이 향상됩니다.")

        if not recommendations:
            recommendations.append("✅ 설계가 우수합니다! 다음 단계로 진행하세요.")

        return recommendations
