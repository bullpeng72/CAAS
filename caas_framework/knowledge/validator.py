"""
CAAS Ontology Validator

온톨로지 기반 검증 및 수정 제안 시스템입니다.
Agent Designer UI에서 사용할 수 있는 검증 결과를 제공합니다.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

from pydantic import BaseModel, Field

from caas_framework.knowledge.ontology import AgentRole, OntologyManager
from caas_framework.utils.logger import LoggerMixin, get_logger

logger = get_logger("knowledge.validator")


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


class ValidationSeverity(str, Enum):
    """검증 결과 심각도"""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    SUCCESS = "success"


class ValidationIssue(BaseModel):
    """검증 이슈"""

    severity: ValidationSeverity
    category: str  # "role", "task", "tool", "assignment"
    agent_id: Optional[str] = None
    task_id: Optional[str] = None
    message: str
    suggestion: str
    auto_fix_available: bool = False
    auto_fix_data: Optional[Dict[str, Any]] = None


class ValidationResult(BaseModel):
    """검증 결과"""

    is_valid: bool = True
    issues: List[ValidationIssue] = Field(default_factory=list)
    summary: Dict[str, int] = Field(default_factory=dict)


class OntologyValidator(LoggerMixin):
    """
    온톨로지 기반 검증기

    에이전트와 태스크 구성을 온톨로지 규칙에 따라 검증하고
    개선 제안 및 자동 수정 옵션을 제공합니다.
    """

    def __init__(self):
        self.ontology = OntologyManager()

    def validate_agents_and_tasks(
        self, agents: List[Dict[str, Any]], tasks: List[Dict[str, Any]]
    ) -> ValidationResult:
        """
        에이전트와 태스크를 검증합니다.

        Args:
            agents: 에이전트 목록
            tasks: 태스크 목록

        Returns:
            ValidationResult: 검증 결과
        """
        self.logger.info(f"검증 시작: {len(agents)}개 에이전트, {len(tasks)}개 태스크")

        issues: List[ValidationIssue] = []

        # 1. 에이전트 역할 검증
        issues.extend(self._validate_agent_roles(agents))

        # 2. 에이전트 도구 검증
        issues.extend(self._validate_agent_tools(agents, tasks))

        # 3. 태스크 할당 검증
        issues.extend(self._validate_task_assignments(agents, tasks))

        # 4. 태스크 의존성 검증
        issues.extend(self._validate_task_dependencies(tasks))

        # 요약 생성
        summary = {
            "total": len(issues),
            "errors": len(
                [i for i in issues if i.severity == ValidationSeverity.ERROR]
            ),
            "warnings": len(
                [i for i in issues if i.severity == ValidationSeverity.WARNING]
            ),
            "info": len([i for i in issues if i.severity == ValidationSeverity.INFO]),
            "auto_fixable": len([i for i in issues if i.auto_fix_available]),
        }

        is_valid = summary["errors"] == 0

        self.logger.info(
            f"검증 완료: {summary['total']}개 이슈 ({summary['errors']} errors, {summary['warnings']} warnings)"
        )

        return ValidationResult(is_valid=is_valid, issues=issues, summary=summary)

    def _validate_agent_roles(
        self, agents: List[Dict[str, Any]]
    ) -> List[ValidationIssue]:
        """에이전트 역할 검증"""
        issues = []

        standard_roles = [r.value for r in AgentRole]

        for agent in agents:
            agent_id = _safe_get(agent, "id", "unknown")
            role = _safe_get(agent, "role", "")

            # 역할 정규화 시도
            inferred_role = self.ontology.infer_role_from_description(
                f"{role} {_safe_get(agent, 'goal', '')}"
            )

            # 비표준 역할 감지
            if role.lower() != inferred_role.value:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        category="role",
                        agent_id=agent_id,
                        message=f"비표준 역할: '{role}'",
                        suggestion=f"표준 역할 '{inferred_role.value}'로 변경을 권장합니다.",
                        auto_fix_available=True,
                        auto_fix_data={
                            "action": "normalize_role",
                            "agent_id": agent_id,
                            "new_role": inferred_role.value,
                        },
                    )
                )

        return issues

    def _validate_agent_tools(
        self, agents: List[Dict[str, Any]], tasks: List[Dict[str, Any]]
    ) -> List[ValidationIssue]:
        """에이전트 도구 검증"""
        issues = []

        # Tool Registry에서 활성화된 도구 목록 가져오기 (한 번만)
        from caas_framework.models.tool_registry import get_enabled_tools_dict

        enabled_tools = get_enabled_tools_dict()

        for agent in agents:
            agent_id = _safe_get(agent, "id", "unknown")
            role = _safe_get(agent, "role", "")
            current_tools = set(_safe_get(agent, "tools", []))

            # Tool Registry에서 실제 도구 존재 여부 확인
            unregistered_tools = []
            for tool in current_tools:
                if tool not in enabled_tools:
                    unregistered_tools.append(tool)

            if unregistered_tools:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        category="tool",
                        agent_id=agent_id,
                        message=f"미등록 도구 사용: {', '.join(unregistered_tools)}",
                        suggestion=f"다음 도구를 Tool Registry에 등록하거나 제거하세요: {', '.join(unregistered_tools)}",
                        auto_fix_available=True,
                        auto_fix_data={
                            "action": "remove_tools",
                            "agent_id": agent_id,
                            "tools_to_remove": unregistered_tools,
                        },
                    )
                )

            # 에이전트가 담당할 태스크 찾기
            agent_tasks = [
                t
                for t in tasks
                if (_safe_get(t, "assigned_agent") or _safe_get(t, "agent", "")).lower()
                in agent_id.lower()
                or (_safe_get(t, "assigned_agent") or _safe_get(t, "agent", "")).lower()
                in role.lower()
            ]

            if not agent_tasks:
                continue

            # 태스크별 필요 도구 계산
            inferred_role = self.ontology.infer_role_from_description(
                f"{role} {_safe_get(agent, 'goal', '')}"
            )

            task_types = []
            for task in agent_tasks:
                task_type = self.ontology.infer_task_type_from_description(
                    _safe_get(task, "description", "")
                )
                task_types.append(task_type)

            # 추천 도구 계산
            recommended_tools = self.ontology.recommend_agent_tools(
                role=inferred_role, assigned_tasks=task_types
            )

            # 추천 도구 중 Tool Registry에 있는 것만 필터링
            recommended_tools = [
                tool for tool in recommended_tools if tool in enabled_tools
            ]

            # 누락된 도구 확인
            missing_tools = set(recommended_tools) - current_tools

            if missing_tools:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.INFO,
                        category="tool",
                        agent_id=agent_id,
                        message=f"추천 도구 누락: {len(missing_tools)}개",
                        suggestion=f"다음 도구 추가 권장: {', '.join(list(missing_tools)[:3])}",
                        auto_fix_available=True,
                        auto_fix_data={
                            "action": "add_tools",
                            "agent_id": agent_id,
                            "tools_to_add": list(missing_tools),
                        },
                    )
                )

        return issues

    def _validate_task_assignments(
        self, agents: List[Dict[str, Any]], tasks: List[Dict[str, Any]]
    ) -> List[ValidationIssue]:
        """태스크 할당 검증"""
        issues = []

        for task in tasks:
            task_id = _safe_get(task, "id", _safe_get(task, "name", "unknown"))
            # "assigned_agent" 또는 "agent" 키 모두 지원 (하위 호환성)
            assigned_agent_name = _safe_get(task, "assigned_agent") or _safe_get(
                task, "agent", ""
            )

            # 할당된 에이전트 찾기
            assigned_agent = None
            for agent in agents:
                if (
                    _safe_get(agent, "id", "").lower() in assigned_agent_name.lower()
                    or _safe_get(agent, "role", "").lower()
                    in assigned_agent_name.lower()
                ):
                    assigned_agent = agent
                    break

            if not assigned_agent:
                # 자동 수정: 태스크 유형에 맞는 에이전트를 찾아서 할당
                if len(agents) > 0:
                    # 태스크 유형 추론
                    task_type = self.ontology.infer_task_type_from_description(
                        _safe_get(task, "description", "")
                    )

                    # 적합한 에이전트 찾기
                    suitable_agent = None
                    suitable_roles = self.ontology.get_suitable_roles(task_type)

                    # 적합한 역할을 가진 에이전트 찾기
                    for role in suitable_roles:
                        for agent in agents:
                            agent_role = self.ontology.infer_role_from_description(
                                f"{_safe_get(agent, 'role', '')} {_safe_get(agent, 'goal', '')}"
                            )
                            if agent_role == role:
                                suitable_agent = agent
                                break
                        if suitable_agent:
                            break

                    # 적합한 에이전트가 없으면 첫 번째 에이전트 선택
                    if not suitable_agent:
                        suitable_agent = agents[0]

                    issues.append(
                        ValidationIssue(
                            severity=ValidationSeverity.ERROR,
                            category="assignment",
                            task_id=task_id,
                            message=f"할당된 에이전트를 찾을 수 없음: '{assigned_agent_name}'",
                            suggestion=f"에이전트 '{_safe_get(suitable_agent, 'id', _safe_get(suitable_agent, 'role'))}'를 자동 할당할 수 있습니다.",
                            auto_fix_available=True,
                            auto_fix_data={
                                "action": "assign_agent",
                                "task_id": task_id,
                                "agent_id": _safe_get(
                                    suitable_agent,
                                    "id",
                                    _safe_get(suitable_agent, "role"),
                                ),
                            },
                        )
                    )
                else:
                    issues.append(
                        ValidationIssue(
                            severity=ValidationSeverity.ERROR,
                            category="assignment",
                            task_id=task_id,
                            message=f"할당된 에이전트를 찾을 수 없음: '{assigned_agent_name}'",
                            suggestion="먼저 에이전트를 생성하세요.",
                            auto_fix_available=False,
                        )
                    )
                continue

            # 역할-태스크 적합성 검증
            inferred_role = self.ontology.infer_role_from_description(
                f"{_safe_get(assigned_agent, 'role', '')} {_safe_get(assigned_agent, 'goal', '')}"
            )

            task_type = self.ontology.infer_task_type_from_description(
                _safe_get(task, "description", "")
            )

            is_valid = self.ontology.validate_assignment(inferred_role, task_type)

            if not is_valid:
                # 더 적합한 역할 찾기
                suitable_roles = self.ontology.get_suitable_roles(task_type)

                # 현재 에이전트 역할에 맞는 태스크 타입 찾기
                suitable_tasks = self.ontology.get_suitable_tasks(inferred_role)

                # 권장 태스크 설명 생성
                recommended_description = self._generate_recommended_description(
                    _safe_get(task, "description", ""), inferred_role, suitable_tasks
                )

                if suitable_roles:
                    suggestion_parts = [
                        f"더 적합한 역할: {', '.join([r.value for r in suitable_roles[:2]])}",
                    ]

                    if recommended_description:
                        suggestion_parts.append(
                            f"또는 태스크 설명을 '{inferred_role.value}' 역할에 맞게 수정:\n\"{recommended_description}\""
                        )

                    issues.append(
                        ValidationIssue(
                            severity=ValidationSeverity.WARNING,
                            category="assignment",
                            task_id=task_id,
                            agent_id=_safe_get(assigned_agent, "id"),
                            message=f"부적합한 태스크 할당: '{task_type.value}' 태스크를 '{inferred_role.value}' 에이전트가 수행",
                            suggestion="\n".join(suggestion_parts),
                            auto_fix_available=False,  # 재할당은 수동으로
                        )
                    )

        return issues

    def _validate_task_dependencies(
        self, tasks: List[Dict[str, Any]]
    ) -> List[ValidationIssue]:
        """태스크 의존성 검증"""
        issues = []

        task_ids = {_safe_get(t, "id", _safe_get(t, "name")) for t in tasks}

        for task in tasks:
            task_id = _safe_get(task, "id", _safe_get(task, "name", "unknown"))
            dependencies = _safe_get(task, "dependencies", [])

            # 존재하지 않는 의존성 확인
            for dep in dependencies:
                if dep not in task_ids:
                    issues.append(
                        ValidationIssue(
                            severity=ValidationSeverity.ERROR,
                            category="task",
                            task_id=task_id,
                            message=f"존재하지 않는 의존 태스크: '{dep}'",
                            suggestion="의존성을 제거하거나 올바른 태스크 ID로 수정하세요.",
                            auto_fix_available=False,
                        )
                    )

            # 순환 의존성 확인 (간단한 버전)
            if task_id in dependencies:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        category="task",
                        task_id=task_id,
                        message="자기 자신을 의존하는 순환 의존성",
                        suggestion="의존성을 제거하세요.",
                        auto_fix_available=True,
                        auto_fix_data={
                            "action": "remove_circular_dependency",
                            "task_id": task_id,
                            "dependency_to_remove": task_id,
                        },
                    )
                )

        return issues

    def apply_auto_fix(
        self,
        agents: List[Dict[str, Any]],
        tasks: List[Dict[str, Any]],
        issue: ValidationIssue,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        자동 수정 적용

        Args:
            agents: 에이전트 목록
            tasks: 태스크 목록
            issue: 수정할 이슈

        Returns:
            Tuple[List[Dict], List[Dict]]: (수정된 agents, 수정된 tasks)
        """
        if not issue.auto_fix_available or not issue.auto_fix_data:
            self.logger.warning(f"자동 수정 불가능한 이슈: {issue.message}")
            return agents, tasks

        action = issue.auto_fix_data.get("action")

        if action == "normalize_role":
            # 역할 정규화
            agent_id = issue.auto_fix_data.get("agent_id")
            new_role = issue.auto_fix_data.get("new_role")

            for agent in agents:
                if _safe_get(agent, "id") == agent_id:
                    agent["role"] = new_role
                    self.logger.info(f"✅ 역할 정규화 적용: {agent_id} → {new_role}")
                    break

        elif action == "add_tools":
            # 도구 추가
            agent_id = issue.auto_fix_data.get("agent_id")
            tools_to_add = issue.auto_fix_data.get("tools_to_add", [])

            for agent in agents:
                if _safe_get(agent, "id") == agent_id:
                    current_tools = _safe_get(agent, "tools", [])
                    agent["tools"] = list(set(current_tools) | set(tools_to_add))
                    self.logger.info(
                        f"✅ 도구 추가: {agent_id} + {len(tools_to_add)}개 도구"
                    )
                    break

        elif action == "remove_tools":
            # 미등록 도구 제거
            agent_id = issue.auto_fix_data.get("agent_id")
            tools_to_remove = issue.auto_fix_data.get("tools_to_remove", [])

            for agent in agents:
                if _safe_get(agent, "id") == agent_id:
                    current_tools = _safe_get(agent, "tools", [])
                    agent["tools"] = [
                        t for t in current_tools if t not in tools_to_remove
                    ]
                    self.logger.info(
                        f"✅ 미등록 도구 제거: {agent_id} - {', '.join(tools_to_remove)}"
                    )
                    break

        elif action == "remove_circular_dependency":
            # 순환 의존성 제거
            task_id = issue.auto_fix_data.get("task_id")
            dep_to_remove = issue.auto_fix_data.get("dependency_to_remove")

            for task in tasks:
                if (
                    _safe_get(task, "id") == task_id
                    or _safe_get(task, "name") == task_id
                ):
                    deps = _safe_get(task, "dependencies", [])
                    if dep_to_remove in deps:
                        deps.remove(dep_to_remove)
                        task["dependencies"] = deps
                        self.logger.info(f"✅ 순환 의존성 제거: {task_id}")
                    break

        elif action == "assign_agent":
            # 에이전트 자동 할당
            task_id = issue.auto_fix_data.get("task_id")
            agent_id = issue.auto_fix_data.get("agent_id")

            for task in tasks:
                if (
                    _safe_get(task, "id") == task_id
                    or _safe_get(task, "name") == task_id
                ):
                    # 둘 다 설정 (하위 호환성)
                    task["assigned_agent"] = agent_id
                    task["agent"] = agent_id
                    self.logger.info(f"✅ 에이전트 자동 할당: {task_id} → {agent_id}")
                    break

        return agents, tasks

    def get_validation_stats(self, result: ValidationResult) -> Dict[str, Any]:
        """
        검증 결과 통계

        Args:
            result: 검증 결과

        Returns:
            Dict: 통계 정보
        """
        return {
            "total_issues": result.summary.get("total", 0),
            "errors": result.summary.get("errors", 0),
            "warnings": result.summary.get("warnings", 0),
            "info": result.summary.get("info", 0),
            "auto_fixable": result.summary.get("auto_fixable", 0),
            "is_valid": result.is_valid,
            "health_score": self._calculate_health_score(result),
        }

    def _calculate_health_score(self, result: ValidationResult) -> int:
        """
        전체 품질 점수 계산 (0-100)

        Args:
            result: 검증 결과

        Returns:
            int: 품질 점수
        """
        total = result.summary.get("total", 0)
        errors = result.summary.get("errors", 0)
        warnings = result.summary.get("warnings", 0)

        if total == 0:
            return 100  # 이슈 없음

        # 에러: -10점, 경고: -5점
        penalty = (errors * 10) + (warnings * 5)
        score = max(0, 100 - penalty)

        return score

    def _generate_recommended_description(
        self, original_description: str, agent_role, suitable_tasks: List
    ) -> str:
        """
        에이전트 역할에 맞는 권장 태스크 설명 생성

        Args:
            original_description: 원본 태스크 설명
            agent_role: 에이전트 역할 (AgentRole enum)
            suitable_tasks: 역할에 적합한 태스크 타입 목록

        Returns:
            str: 권장 태스크 설명
        """
        from caas_framework.knowledge.ontology import AgentRole, TaskType

        # 원본 설명에서 핵심 키워드 추출
        original_lower = original_description.lower()

        # 역할별 권장 키워드 매핑
        role_keywords = {
            AgentRole.CODER: ["코딩하고", "구현합니다", "개발합니다", "프로그래밍"],
            AgentRole.WRITER: ["작성합니다", "문서화합니다", "기술합니다"],
            AgentRole.RESEARCHER: ["조사하고", "분석합니다", "연구합니다"],
            AgentRole.ANALYST: ["분석하고", "평가합니다", "검토합니다"],
            AgentRole.PLANNER: ["계획하고", "설계합니다", "기획합니다"],
            AgentRole.EXECUTOR: ["실행하고", "수행합니다", "처리합니다"],
            AgentRole.MANAGER: ["관리하고", "조율합니다", "검토합니다"],
            AgentRole.REVIEWER: ["검토하고", "평가합니다", "피드백합니다"],
            AgentRole.ARCHITECT: ["설계하고", "아키텍처를 구성합니다"],
            AgentRole.DATA_ENGINEER: [
                "데이터 파이프라인을 구축하고",
                "ETL 프로세스를 개발합니다",
            ],
            AgentRole.UX_DESIGNER: ["UI를 설계하고", "사용자 경험을 개선합니다"],
        }

        # 태스크 타입별 권장 표현
        task_type_phrases = {
            TaskType.CODING: "코딩하고 구현합니다",
            TaskType.WRITING: "작성하고 문서화합니다",
            TaskType.RESEARCH: "조사하고 분석합니다",
            TaskType.ANALYSIS: "분석하고 평가합니다",
            TaskType.PLANNING: "계획하고 설계합니다",
            TaskType.EXECUTION: "실행하고 처리합니다",
            TaskType.REVIEW: "검토하고 피드백합니다",
            TaskType.DATA_PIPELINE: "데이터 파이프라인을 구축하고 ETL 프로세스를 개발합니다",
            TaskType.BACKEND_DEVELOPMENT: "백엔드 API를 개발하고 서버 로직을 구현합니다",
            TaskType.FRONTEND_DEVELOPMENT: "프론트엔드 컴포넌트를 개발하고 UI를 구현합니다",
            TaskType.UI_DESIGN: "UI를 설계하고 인터페이스를 구성합니다",
        }

        # 원본 설명의 주요 단어 추출 (명사 중심)
        main_subject = (
            original_description.split()[0] if original_description else "작업"
        )

        # UI/프론트엔드 관련 키워드 감지
        if any(
            kw in original_lower
            for kw in ["ui", "프론트", "frontend", "화면", "인터페이스"]
        ):
            if agent_role == AgentRole.CODER:
                return f"React와 TypeScript를 사용하여 {main_subject} UI 컴포넌트를 코딩하고 구현합니다"
            elif agent_role == AgentRole.UX_DESIGNER:
                return f"{main_subject} UI를 설계하고 사용자 인터페이스를 구성합니다"

        # 데이터 관련 키워드 감지
        if any(kw in original_lower for kw in ["data", "데이터", "파이프라인", "etl"]):
            if agent_role == AgentRole.CODER or agent_role == AgentRole.EXECUTOR:
                return f"{main_subject} 데이터 파이프라인을 구축하고 ETL 프로세스를 구현합니다"
            elif agent_role == AgentRole.DATA_ENGINEER:
                return f"{main_subject} 데이터 처리 워크플로우를 설계하고 구축합니다"

        # 역할에 맞는 기본 표현 사용
        keywords = role_keywords.get(agent_role, ["수행합니다"])

        # 첫 번째 적합한 태스크 타입의 표현 사용
        if suitable_tasks:
            first_task = suitable_tasks[0]
            phrase = task_type_phrases.get(first_task, keywords[0])
            return f"{main_subject}을(를) {phrase}"

        return f"{main_subject}을(를) {keywords[0]}"
