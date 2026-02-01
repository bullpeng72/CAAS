"""
Spec Validator

CrewAI YAML Spec의 구조적 검증 및 품질 체크
"""

from typing import List, Dict, Any, Optional
import yaml
from pydantic import BaseModel, Field

from caas_framework.utils.logger import get_logger

logger = get_logger("spec_validator")


class ValidationIssue(BaseModel):
    """검증 이슈"""
    severity: str = Field(description="error, warning, info")
    category: str = Field(description="구조, 일관성, 품질 등")
    message: str
    location: Optional[str] = None
    suggestion: Optional[str] = None


class SpecValidationResult(BaseModel):
    """Spec 검증 결과"""
    is_valid: bool
    issues: List[ValidationIssue] = []
    warnings_count: int = 0
    errors_count: int = 0
    quality_score: float = Field(default=0.7, ge=0.0, le=1.0)


class SpecValidator:
    """
    CrewAI YAML Spec 검증기

    구조적 검증, 일관성 검증, 품질 검증을 수행합니다.
    """

    @classmethod
    def validate_structure(cls, spec_data: Dict[str, Any]) -> List[ValidationIssue]:
        """구조적 검증: 필수 필드가 모두 존재하는지 확인"""
        issues = []

        # 1. 최상위 필드 검증
        required_fields = ["agents", "tasks"]
        for field in required_fields:
            if field not in spec_data:
                issues.append(ValidationIssue(
                    severity="error",
                    category="structure",
                    message=f"필수 필드 '{field}'가 누락되었습니다.",
                    suggestion=f"'{field}' 필드를 추가하세요."
                ))

        if "agents" not in spec_data or "tasks" not in spec_data:
            return issues  # 기본 구조가 없으면 추가 검증 불가

        # 2. Agents 구조 검증
        agents = spec_data.get("agents", [])
        if not isinstance(agents, list):
            issues.append(ValidationIssue(
                severity="error",
                category="structure",
                message="'agents' 필드는 리스트여야 합니다.",
            ))
        else:
            for idx, agent in enumerate(agents):
                if not isinstance(agent, dict):
                    issues.append(ValidationIssue(
                        severity="error",
                        category="structure",
                        message=f"agents[{idx}]는 딕셔너리여야 합니다.",
                        location=f"agents[{idx}]"
                    ))
                    continue

                # Agent 필수 필드
                agent_required = ["id", "role", "goal"]
                for field in agent_required:
                    if field not in agent:
                        issues.append(ValidationIssue(
                            severity="error",
                            category="structure",
                            message=f"Agent '{agent.get('id', idx)}'에 필수 필드 '{field}'가 누락되었습니다.",
                            location=f"agents[{idx}].{field}",
                            suggestion=f"'{field}' 필드를 추가하세요."
                        ))

                # llm 필드 검증 (CrewAI 요구사항)
                if "llm" not in agent or agent["llm"] is None:
                    issues.append(ValidationIssue(
                        severity="error",
                        category="structure",
                        message=f"Agent '{agent.get('id', idx)}'에 'llm' 필드가 필요합니다.",
                        location=f"agents[{idx}].llm",
                        suggestion="'llm' 필드에 LLM 설정을 추가하세요 (예: model: gpt-4)"
                    ))

        # 3. Tasks 구조 검증
        tasks = spec_data.get("tasks", [])
        if not isinstance(tasks, list):
            issues.append(ValidationIssue(
                severity="error",
                category="structure",
                message="'tasks' 필드는 리스트여야 합니다.",
            ))
        else:
            for idx, task in enumerate(tasks):
                if not isinstance(task, dict):
                    issues.append(ValidationIssue(
                        severity="error",
                        category="structure",
                        message=f"tasks[{idx}]는 딕셔너리여야 합니다.",
                        location=f"tasks[{idx}]"
                    ))
                    continue

                # Task 필수 필드
                task_required = ["id", "description", "agent", "expected_output"]
                for field in task_required:
                    if field not in task:
                        issues.append(ValidationIssue(
                            severity="error",
                            category="structure",
                            message=f"Task '{task.get('id', idx)}'에 필수 필드 '{field}'가 누락되었습니다.",
                            location=f"tasks[{idx}].{field}",
                            suggestion=f"'{field}' 필드를 추가하세요."
                        ))

        return issues

    @classmethod
    def validate_consistency(cls, spec_data: Dict[str, Any]) -> List[ValidationIssue]:
        """일관성 검증: Agent-Task 관계 등 확인"""
        issues = []

        agents = spec_data.get("agents", [])
        tasks = spec_data.get("tasks", [])

        # Agent ID 목록 수집
        agent_ids = set()
        for agent in agents:
            if isinstance(agent, dict) and "id" in agent:
                agent_ids.add(agent["id"])

        # Task ID 목록 수집
        task_ids = set()
        for task in tasks:
            if isinstance(task, dict) and "id" in task:
                task_ids.add(task["id"])

        # 1. Task의 agent 참조 검증
        for idx, task in enumerate(tasks):
            if not isinstance(task, dict):
                continue

            task_agent = task.get("agent")
            if task_agent and task_agent not in agent_ids:
                issues.append(ValidationIssue(
                    severity="error",
                    category="consistency",
                    message=f"Task '{task.get('id', idx)}'가 존재하지 않는 agent '{task_agent}'를 참조합니다.",
                    location=f"tasks[{idx}].agent",
                    suggestion=f"정의된 agent 중 하나를 사용하세요: {', '.join(agent_ids)}"
                ))

            # 2. Task의 context 참조 검증
            task_context = task.get("context", [])
            if isinstance(task_context, list):
                for ctx_task in task_context:
                    if ctx_task not in task_ids:
                        issues.append(ValidationIssue(
                            severity="warning",
                            category="consistency",
                            message=f"Task '{task.get('id', idx)}'의 context가 존재하지 않는 task '{ctx_task}'를 참조합니다.",
                            location=f"tasks[{idx}].context",
                            suggestion="정의된 task ID를 사용하세요."
                        ))

        # 3. 순환 의존성 검증 (간단한 버전)
        task_dependencies = {}
        for task in tasks:
            if isinstance(task, dict) and "id" in task:
                task_id = task["id"]
                context = task.get("context", [])
                if isinstance(context, list):
                    task_dependencies[task_id] = set(context)

        # 간단한 순환 검증 (직접 순환만)
        for task_id, deps in task_dependencies.items():
            if task_id in deps:
                issues.append(ValidationIssue(
                    severity="error",
                    category="consistency",
                    message=f"Task '{task_id}'가 자기 자신을 context로 참조합니다 (순환 의존성).",
                    location=f"task.{task_id}.context",
                    suggestion="context에서 자기 자신을 제거하세요."
                ))

        return issues

    @classmethod
    def validate_quality(cls, spec_data: Dict[str, Any]) -> List[ValidationIssue]:
        """품질 검증: 명명 규칙, 설명 품질 등 확인"""
        issues = []

        agents = spec_data.get("agents", [])
        tasks = spec_data.get("tasks", [])

        # 1. Agent ID 명명 규칙 검증
        for idx, agent in enumerate(agents):
            if not isinstance(agent, dict):
                continue

            agent_id = agent.get("id", "")
            if not agent_id:
                continue

            # snake_case 검증
            import re
            if not re.match(r'^[a-z][a-z0-9_]*$', agent_id):
                issues.append(ValidationIssue(
                    severity="warning",
                    category="quality",
                    message=f"Agent ID '{agent_id}'는 snake_case 규칙을 따르지 않습니다.",
                    location=f"agents[{idx}].id",
                    suggestion="snake_case 형식 (예: my_agent_name)을 사용하세요."
                ))

            # Goal 설명 길이 검증
            goal = agent.get("goal", "")
            if len(goal) < 10:
                issues.append(ValidationIssue(
                    severity="info",
                    category="quality",
                    message=f"Agent '{agent_id}'의 goal이 너무 짧습니다 ({len(goal)}자).",
                    location=f"agents[{idx}].goal",
                    suggestion="더 상세한 목표를 작성하세요 (최소 10자 권장)."
                ))

        # 2. Task ID 명명 규칙 검증
        for idx, task in enumerate(tasks):
            if not isinstance(task, dict):
                continue

            task_id = task.get("id", "")
            if not task_id:
                continue

            import re
            if not re.match(r'^[a-z][a-z0-9_]*$', task_id):
                issues.append(ValidationIssue(
                    severity="warning",
                    category="quality",
                    message=f"Task ID '{task_id}'는 snake_case 규칙을 따르지 않습니다.",
                    location=f"tasks[{idx}].id",
                    suggestion="snake_case 형식을 사용하세요."
                ))

            # Description 길이 검증
            description = task.get("description", "")
            if len(description) < 20:
                issues.append(ValidationIssue(
                    severity="info",
                    category="quality",
                    message=f"Task '{task_id}'의 description이 너무 짧습니다 ({len(description)}자).",
                    location=f"tasks[{idx}].description",
                    suggestion="더 상세한 설명을 작성하세요 (최소 20자 권장)."
                ))

        # 3. Agent/Task 수 밸런스 검증
        num_agents = len(agents)
        num_tasks = len(tasks)

        if num_tasks < num_agents:
            issues.append(ValidationIssue(
                severity="warning",
                category="quality",
                message=f"Task 수({num_tasks})가 Agent 수({num_agents})보다 적습니다.",
                suggestion="일반적으로 Agent당 1-3개의 Task가 적절합니다."
            ))

        if num_agents > 10:
            issues.append(ValidationIssue(
                severity="warning",
                category="quality",
                message=f"Agent 수가 너무 많습니다 ({num_agents}개).",
                suggestion="Agent 수를 10개 이하로 줄이는 것을 권장합니다."
            ))

        return issues

    @classmethod
    def validate_spec(cls, spec_yaml: str) -> SpecValidationResult:
        """
        전체 Spec 검증을 수행합니다.

        Args:
            spec_yaml: YAML 문자열

        Returns:
            SpecValidationResult: 검증 결과
        """
        logger.info("Spec 검증 시작")

        all_issues = []

        # YAML 파싱
        try:
            spec_data = yaml.safe_load(spec_yaml)
        except yaml.YAMLError as e:
            return SpecValidationResult(
                is_valid=False,
                issues=[ValidationIssue(
                    severity="error",
                    category="structure",
                    message=f"YAML 파싱 오류: {e}",
                    suggestion="YAML 문법을 확인하세요."
                )],
                errors_count=1,
                quality_score=0.0
            )

        if not spec_data or not isinstance(spec_data, dict):
            return SpecValidationResult(
                is_valid=False,
                issues=[ValidationIssue(
                    severity="error",
                    category="structure",
                    message="Spec이 비어있거나 유효하지 않습니다.",
                )],
                errors_count=1,
                quality_score=0.0
            )

        # 1. 구조적 검증
        structure_issues = cls.validate_structure(spec_data)
        all_issues.extend(structure_issues)

        # 2. 일관성 검증
        consistency_issues = cls.validate_consistency(spec_data)
        all_issues.extend(consistency_issues)

        # 3. 품질 검증
        quality_issues = cls.validate_quality(spec_data)
        all_issues.extend(quality_issues)

        # 이슈 카운트
        errors_count = sum(1 for issue in all_issues if issue.severity == "error")
        warnings_count = sum(1 for issue in all_issues if issue.severity == "warning")

        # 유효성 판단 (error가 없으면 valid)
        is_valid = errors_count == 0

        # 품질 점수 계산
        quality_score = cls._calculate_quality_score(spec_data, all_issues)

        logger.info(f"검증 완료: valid={is_valid}, errors={errors_count}, warnings={warnings_count}, score={quality_score:.2f}")

        return SpecValidationResult(
            is_valid=is_valid,
            issues=all_issues,
            errors_count=errors_count,
            warnings_count=warnings_count,
            quality_score=quality_score
        )

    @classmethod
    def _calculate_quality_score(cls, spec_data: Dict[str, Any], issues: List[ValidationIssue]) -> float:
        """품질 점수를 계산합니다 (0.0 ~ 1.0)"""
        base_score = 1.0

        # 오류당 감점
        for issue in issues:
            if issue.severity == "error":
                base_score -= 0.2
            elif issue.severity == "warning":
                base_score -= 0.05
            elif issue.severity == "info":
                base_score -= 0.01

        # 최소값 보장
        quality_score = max(0.0, min(1.0, base_score))

        return round(quality_score, 3)
