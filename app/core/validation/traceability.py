"""
CAAS Traceability Validator

자연어 요구사항과 Spec 간 양방향 추적성을 검증합니다.
누락, 과잉, 불일치를 탐지하여 품질을 보장합니다.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

from pydantic import BaseModel

from app.llm.chains import RequirementAnalysis
from caas_framework.utils.logger import get_logger, LoggerMixin

logger = get_logger("validation.traceability")


class TraceabilityIssueType(str, Enum):
    """추적성 이슈 유형"""
    MISSING_IN_SPEC = "missing_in_spec"  # 요구사항에 있지만 Spec에 없음
    MISSING_IN_REQUIREMENT = "missing_in_requirement"  # Spec에 있지만 요구사항에 없음
    MISMATCH = "mismatch"  # 매핑되었지만 내용 불일치
    PARTIAL_MATCH = "partial_match"  # 부분적으로만 매핑됨


class TraceabilitySeverity(str, Enum):
    """이슈 심각도"""
    CRITICAL = "critical"  # 핵심 요구사항 누락
    HIGH = "high"  # 중요 요소 누락
    MEDIUM = "medium"  # 부분 매칭 또는 경미한 불일치
    LOW = "low"  # 권장사항 수준


@dataclass
class TraceabilityIssue:
    """추적성 이슈"""
    issue_type: TraceabilityIssueType
    severity: TraceabilitySeverity
    category: str  # agent, task, tool, constraint
    message: str
    requirement_reference: Optional[str] = None
    spec_reference: Optional[str] = None
    suggestion: Optional[str] = None


@dataclass
class TraceabilityMapping:
    """요소 간 매핑 정보"""
    requirement_id: str
    requirement_content: str
    spec_id: Optional[str] = None
    spec_content: Optional[str] = None
    match_confidence: float = 0.0  # 0.0 ~ 1.0
    match_reason: Optional[str] = None


class TraceabilityReport(BaseModel):
    """추적성 검증 보고서"""
    valid: bool
    coverage_score: float  # 0.0 ~ 1.0
    issues: List[Dict[str, Any]] = []

    # 매핑 통계
    total_requirement_agents: int = 0
    total_requirement_tasks: int = 0
    total_requirement_tools: int = 0

    total_spec_agents: int = 0
    total_spec_tasks: int = 0
    total_spec_tools: int = 0

    mapped_agents: int = 0
    mapped_tasks: int = 0
    mapped_tools: int = 0

    # 상세 매핑
    agent_mappings: List[Dict[str, Any]] = []
    task_mappings: List[Dict[str, Any]] = []
    tool_mappings: List[Dict[str, Any]] = []

    # 누락/과잉
    missing_agents: List[str] = []
    missing_tasks: List[str] = []
    missing_tools: List[str] = []
    extra_agents: List[str] = []
    extra_tasks: List[str] = []
    extra_tools: List[str] = []


class TraceabilityValidator(LoggerMixin):
    """
    양방향 추적성 검증기

    Forward Tracing: 요구사항 → Spec
    Backward Tracing: Spec → 요구사항
    Gap Analysis: 누락/과잉 요소 식별
    """

    def __init__(self, min_match_confidence: float = 0.6):
        """
        Args:
            min_match_confidence: 매핑 인정 최소 신뢰도 (0.0 ~ 1.0)
        """
        self.min_match_confidence = min_match_confidence
        self.issues: List[TraceabilityIssue] = []

    def validate_coverage(
        self,
        requirement_analysis: RequirementAnalysis,
        generated_spec: Dict[str, Any],
    ) -> TraceabilityReport:
        """
        요구사항과 Spec 간 커버리지를 검증합니다.

        Args:
            requirement_analysis: 요구사항 분석 결과
            generated_spec: 생성된 Spec (dict 형태)

        Returns:
            TraceabilityReport: 추적성 보고서
        """
        self.logger.info("=== 추적성 검증 시작 ===")
        self.issues = []

        # Tool Registry에서 활성화된 도구 목록 가져오기 (한 번만)
        from app.models.tool_registry import get_enabled_tools_dict
        enabled_tools = get_enabled_tools_dict()

        # 1. Forward Tracing: 요구사항 → Spec
        agent_mappings = self._trace_agents_forward(
            requirement_analysis.agents,
            generated_spec.get("agents", [])
        )

        task_mappings = self._trace_tasks_forward(
            requirement_analysis.tasks,
            generated_spec.get("tasks", [])
        )

        tool_mappings = self._trace_tools_forward(
            requirement_analysis.suggested_tools,
            generated_spec.get("agents", []),
            enabled_tools
        )

        # 2. Backward Tracing: Spec → 요구사항
        extra_agents = self._trace_agents_backward(
            requirement_analysis.agents,
            generated_spec.get("agents", [])
        )

        extra_tasks = self._trace_tasks_backward(
            requirement_analysis.tasks,
            generated_spec.get("tasks", [])
        )

        extra_tools = self._trace_tools_backward(
            requirement_analysis.suggested_tools,
            generated_spec.get("agents", []),
            enabled_tools
        )

        # 3. Gap Analysis: 누락 요소 식별
        missing_agents = [
            m.requirement_id for m in agent_mappings
            if m.match_confidence < self.min_match_confidence
        ]

        missing_tasks = [
            m.requirement_id for m in task_mappings
            if m.match_confidence < self.min_match_confidence
        ]

        missing_tools = [
            m.requirement_id for m in tool_mappings
            if m.match_confidence < self.min_match_confidence
        ]

        # 4. 이슈 생성
        self._generate_issues(
            missing_agents, missing_tasks, missing_tools,
            extra_agents, extra_tasks, extra_tools,
            agent_mappings, task_mappings
        )

        # 5. 커버리지 점수 계산
        coverage_score = self._calculate_coverage_score(
            len(requirement_analysis.agents),
            len(requirement_analysis.tasks),
            len(requirement_analysis.suggested_tools),
            len(missing_agents),
            len(missing_tasks),
            len(missing_tools),
        )

        # 6. 보고서 생성
        report = TraceabilityReport(
            valid=len([i for i in self.issues if i.severity in [
                TraceabilitySeverity.CRITICAL, TraceabilitySeverity.HIGH
            ]]) == 0,
            coverage_score=coverage_score,
            issues=[self._issue_to_dict(i) for i in self.issues],

            # 통계
            total_requirement_agents=len(requirement_analysis.agents),
            total_requirement_tasks=len(requirement_analysis.tasks),
            total_requirement_tools=len(requirement_analysis.suggested_tools),

            total_spec_agents=len(generated_spec.get("agents", [])),
            total_spec_tasks=len(generated_spec.get("tasks", [])),
            total_spec_tools=self._count_tools_in_spec(generated_spec.get("agents", [])),

            mapped_agents=len([m for m in agent_mappings if m.match_confidence >= self.min_match_confidence]),
            mapped_tasks=len([m for m in task_mappings if m.match_confidence >= self.min_match_confidence]),
            mapped_tools=len([m for m in tool_mappings if m.match_confidence >= self.min_match_confidence]),

            # 상세 매핑
            agent_mappings=[self._mapping_to_dict(m) for m in agent_mappings],
            task_mappings=[self._mapping_to_dict(m) for m in task_mappings],
            tool_mappings=[self._mapping_to_dict(m) for m in tool_mappings],

            # 누락/과잉
            missing_agents=missing_agents,
            missing_tasks=missing_tasks,
            missing_tools=missing_tools,
            extra_agents=extra_agents,
            extra_tasks=extra_tasks,
            extra_tools=extra_tools,
        )

        self.logger.info(
            f"추적성 검증 완료: valid={report.valid}, "
            f"coverage={report.coverage_score:.2%}, "
            f"issues={len(report.issues)}"
        )

        return report

    def _trace_agents_forward(
        self,
        requirement_agents: List,
        spec_agents: List[Dict]
    ) -> List[TraceabilityMapping]:
        """Agent: 요구사항 → Spec 추적 (Greedy matching 적용)"""
        mappings = []
        used_spec_agents = set()  # 이미 매칭된 Spec 에이전트 추적

        for req_agent in requirement_agents:
            best_match = None
            best_confidence = 0.0
            best_reason = None

            for spec_agent in spec_agents:
                # 이미 매칭된 Spec 에이전트는 건너뛰기 (Greedy matching)
                spec_agent_id = spec_agent.get("id", spec_agent.get("role"))
                if spec_agent_id in used_spec_agents:
                    continue

                confidence, reason = self._match_agent(req_agent, spec_agent)
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_match = spec_agent
                    best_reason = reason

            # 매칭된 Spec 에이전트를 used 목록에 추가
            if best_match:
                spec_agent_id = best_match.get("id", best_match.get("role"))
                used_spec_agents.add(spec_agent_id)

            mapping = TraceabilityMapping(
                requirement_id=req_agent.role,
                requirement_content=f"{req_agent.role}: {req_agent.goal}",
                spec_id=best_match.get("id") if best_match else None,
                spec_content=best_match.get("role") if best_match else None,
                match_confidence=best_confidence,
                match_reason=best_reason,
            )
            mappings.append(mapping)

            self.logger.debug(
                f"Agent 매핑: {req_agent.role} → "
                f"{mapping.spec_id or 'NONE'} (신뢰도: {best_confidence:.2f})"
            )

        return mappings

    def _trace_tasks_forward(
        self,
        requirement_tasks: List,
        spec_tasks: List[Dict]
    ) -> List[TraceabilityMapping]:
        """Task: 요구사항 → Spec 추적"""
        mappings = []

        for req_task in requirement_tasks:
            best_match = None
            best_confidence = 0.0
            best_reason = None

            for spec_task in spec_tasks:
                confidence, reason = self._match_task(req_task, spec_task)
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_match = spec_task
                    best_reason = reason

            mapping = TraceabilityMapping(
                requirement_id=req_task.name,
                requirement_content=req_task.description,
                spec_id=best_match.get("id") if best_match else None,
                spec_content=best_match.get("description") if best_match else None,
                match_confidence=best_confidence,
                match_reason=best_reason,
            )
            mappings.append(mapping)

            self.logger.debug(
                f"Task 매핑: {req_task.name} → "
                f"{mapping.spec_id or 'NONE'} (신뢰도: {best_confidence:.2f})"
            )

        return mappings

    def _trace_tools_forward(
        self,
        requirement_tools: List[str],
        spec_agents: List[Dict],
        enabled_tools: Dict[str, str]
    ) -> List[TraceabilityMapping]:
        """Tool: 요구사항 → Spec 추적"""
        mappings = []

        # 요구사항 도구 중 Tool Registry에 있는 것만 검증
        requirement_tools = [tool for tool in requirement_tools if tool in enabled_tools]

        # Spec의 모든 도구 수집
        spec_tools = set()
        for agent in spec_agents:
            spec_tools.update(agent.get("tools", []))

        for req_tool in requirement_tools:
            # 완전 일치 또는 부분 일치
            matched = req_tool in spec_tools
            confidence = 1.0 if matched else 0.0

            # 부분 일치 검사 (유사한 이름)
            if not matched:
                for spec_tool in spec_tools:
                    if self._is_similar_tool(req_tool, spec_tool):
                        confidence = 0.7
                        matched = True
                        break

            mapping = TraceabilityMapping(
                requirement_id=req_tool,
                requirement_content=req_tool,
                spec_id=req_tool if matched else None,
                spec_content=req_tool if matched else None,
                match_confidence=confidence,
                match_reason="완전 일치" if confidence == 1.0 else ("부분 일치" if confidence > 0 else "미매핑"),
            )
            mappings.append(mapping)

        return mappings

    def _trace_agents_backward(
        self,
        requirement_agents: List,
        spec_agents: List[Dict]
    ) -> List[str]:
        """Agent: Spec → 요구사항 역추적 (과잉 탐지)"""
        req_roles = {agent.role.lower() for agent in requirement_agents}
        extra = []

        for spec_agent in spec_agents:
            spec_role = spec_agent.get("role", "").lower()
            # 요구사항에 없는 역할인지 확인
            if not any(req_role in spec_role or spec_role in req_role for req_role in req_roles):
                extra.append(spec_agent.get("id", spec_agent.get("role")))

        return extra

    def _trace_tasks_backward(
        self,
        requirement_tasks: List,
        spec_tasks: List[Dict]
    ) -> List[str]:
        """Task: Spec → 요구사항 역추적 (과잉 탐지)"""
        req_task_names = {task.name.lower() for task in requirement_tasks}
        req_task_descs = {task.description.lower() for task in requirement_tasks}
        extra = []

        for spec_task in spec_tasks:
            spec_desc = spec_task.get("description", "").lower()
            spec_id = spec_task.get("id", "")

            # 이름이나 설명에서 키워드 매칭
            matched = False
            for req_name in req_task_names:
                if req_name in spec_desc or spec_desc in req_name:
                    matched = True
                    break

            if not matched:
                for req_desc in req_task_descs:
                    # 주요 키워드 5개 이상 추출하여 비교
                    req_keywords = set(req_desc.split()[:10])
                    spec_keywords = set(spec_desc.split()[:10])
                    overlap = len(req_keywords & spec_keywords)
                    if overlap >= 3:  # 3개 이상 키워드 일치
                        matched = True
                        break

            if not matched:
                extra.append(spec_id)

        return extra

    def _trace_tools_backward(
        self,
        requirement_tools: List[str],
        spec_agents: List[Dict],
        enabled_tools: Dict[str, str]
    ) -> List[str]:
        """Tool: Spec → 요구사항 역추적 (과잉 탐지)"""
        # 요구사항 도구 중 Tool Registry에 있는 것만 검증
        req_tools = set([tool for tool in requirement_tools if tool in enabled_tools])
        spec_tools = set()

        for agent in spec_agents:
            spec_tools.update(agent.get("tools", []))

        extra = []
        for spec_tool in spec_tools:
            if spec_tool not in req_tools:
                # 유사 도구 체크
                is_similar = any(self._is_similar_tool(spec_tool, req_tool) for req_tool in req_tools)
                if not is_similar:
                    extra.append(spec_tool)

        return extra

    def _match_agent(self, req_agent, spec_agent: Dict) -> tuple[float, str]:
        """Agent 매칭 신뢰도 계산 (개선된 버전 + 온톨로지 정규화 고려)"""
        confidence = 0.0
        reasons = []

        # 1. Role 매칭 (가장 중요) - 개선: 단어 단위 유사도 + 온톨로지 정규화
        req_role = req_agent.role.lower()
        spec_role = spec_agent.get("role", "").lower()

        # ✨ 온톨로지 기반 정규화된 역할 비교
        # 예: "Backend Developer" → "developer", "Frontend Developer" → "developer"
        try:
            from app.knowledge.validator import OntologyValidator
            validator = OntologyValidator()

            # 요구사항 역할의 정규화
            req_role_normalized = validator.ontology.infer_role_from_description(req_agent.role)
            # Spec 역할의 정규화
            spec_role_normalized = validator.ontology.infer_role_from_description(spec_agent.get("role", ""))

            # 정규화된 역할이 같으면 높은 신뢰도
            if req_role_normalized == spec_role_normalized:
                confidence += 0.5
                reasons.append(f"온톨로지 역할 일치 ({req_role_normalized})")
                # 이미 매칭되었으므로 아래 로직은 추가 점수만 제공
        except Exception as e:
            # 온톨로지 검증 실패 시 기존 로직 사용
            logger.debug(f"온톨로지 매칭 실패, 기존 로직 사용: {e}")

        # 기존 역할 매칭 로직 (온톨로지 매칭이 안 된 경우만)
        if confidence < 0.5:  # 온톨로지 매칭이 안 된 경우
            req_role = req_agent.role.lower()
            spec_role = spec_agent.get("role", "").lower()

            if req_role == spec_role:
                confidence += 0.5
                reasons.append("역할 완전 일치")
            elif req_role in spec_role or spec_role in req_role:
                confidence += 0.3
                reasons.append("역할 부분 일치")
            else:
                # 🔧 개선: 단어 단위로 분해하여 유사도 계산
                req_role_words = set(req_role.replace("_", " ").replace("-", " ").split())
                spec_role_words = set(spec_role.replace("_", " ").replace("-", " ").split())
                role_overlap = len(req_role_words & spec_role_words)
                role_total = max(len(req_role_words), len(spec_role_words))

                if role_overlap > 0 and role_total > 0:
                    role_similarity = role_overlap / role_total
                    if role_similarity >= 0.6:
                        confidence += 0.35
                        reasons.append(f"역할 {int(role_similarity*100)}% 유사")
                    elif role_similarity >= 0.4:
                        confidence += 0.2
                        reasons.append(f"역할 {int(role_similarity*100)}% 유사")

        # 2. Goal 매칭 (개선: 불용어 제거 및 유사도)
        req_goal = req_agent.goal.lower()
        spec_goal = spec_agent.get("goal", "").lower()

        # 불용어 제거
        stopwords = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by"}

        req_keywords = set(w for w in req_goal.split() if w not in stopwords and len(w) > 2)
        spec_keywords = set(w for w in spec_goal.split() if w not in stopwords and len(w) > 2)
        overlap = len(req_keywords & spec_keywords)
        total_keywords = max(len(req_keywords), len(spec_keywords))

        if total_keywords > 0:
            goal_similarity = overlap / total_keywords
            if goal_similarity >= 0.5:
                confidence += 0.3
                reasons.append(f"목표 키워드 {overlap}개 일치 ({int(goal_similarity*100)}%)")
            elif goal_similarity >= 0.3:
                confidence += 0.2
                reasons.append(f"목표 키워드 {overlap}개 유사 ({int(goal_similarity*100)}%)")
            elif overlap >= 2:  # 최소 2개만 일치해도 인정
                confidence += 0.1
                reasons.append(f"목표 키워드 {overlap}개 일치")

        # 3. Skills 매칭
        req_skills = {skill.lower() for skill in req_agent.skills}
        spec_backstory = spec_agent.get("backstory", "").lower()

        if req_skills:
            skill_matches = sum(1 for skill in req_skills if skill in spec_backstory)
            if skill_matches > 0:
                confidence += 0.2 * (skill_matches / len(req_skills))
                reasons.append(f"스킬 {skill_matches}개 반영")

        reason = ", ".join(reasons) if reasons else "매칭 없음"
        return min(confidence, 1.0), reason

    def _match_task(self, req_task, spec_task: Dict) -> tuple[float, str]:
        """Task 매칭 신뢰도 계산 (개선된 버전)"""
        confidence = 0.0
        reasons = []

        # 1. Name 매칭 (개선: 단어 단위 정규화 및 유사도)
        req_name = req_task.name.lower()
        spec_id = spec_task.get("id", "").lower()
        spec_desc = spec_task.get("description", "").lower()

        # 🔧 개선: 이름을 단어로 분해하고 정규화
        req_name_words = set(req_name.replace("_", " ").replace("-", " ").split())
        spec_id_words = set(spec_id.replace("_", " ").replace("-", " ").split())

        # 단어 중복도 계산
        name_overlap = len(req_name_words & spec_id_words)
        name_total = max(len(req_name_words), len(spec_id_words))

        if name_overlap > 0 and name_total > 0:
            name_similarity = name_overlap / name_total
            if name_similarity >= 0.7:
                confidence += 0.4
                reasons.append(f"이름 {int(name_similarity*100)}% 일치")
            elif name_similarity >= 0.4:
                confidence += 0.25
                reasons.append(f"이름 {int(name_similarity*100)}% 유사")

        # 기존 substring 매칭도 유지
        if req_name in spec_id or spec_id in req_name:
            if "이름" not in str(reasons):  # 중복 방지
                confidence += 0.2
                reasons.append("이름 포함")

        # 2. Description 매칭 (개선: 임계값 낮춤)
        req_desc = req_task.description.lower()

        # 불용어 제거 (간단한 버전)
        stopwords = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by"}

        req_keywords = set(w for w in req_desc.split() if w not in stopwords and len(w) > 2)
        spec_keywords = set(w for w in spec_desc.split() if w not in stopwords and len(w) > 2)
        overlap = len(req_keywords & spec_keywords)
        total_keywords = max(len(req_keywords), len(spec_keywords))

        if total_keywords > 0:
            keyword_similarity = overlap / total_keywords
            if keyword_similarity >= 0.5:
                confidence += 0.4
                reasons.append(f"설명 키워드 {overlap}개 일치 ({int(keyword_similarity*100)}%)")
            elif keyword_similarity >= 0.3:
                confidence += 0.25
                reasons.append(f"설명 키워드 {overlap}개 유사 ({int(keyword_similarity*100)}%)")
            elif overlap >= 2:  # 최소 2개 키워드만 일치해도 인정
                confidence += 0.15
                reasons.append(f"설명 키워드 {overlap}개 일치")

        # 3. Assigned Agent 매칭
        req_agent = req_task.assigned_agent.lower()
        spec_agent = spec_task.get("agent", "").lower()

        if req_agent in spec_agent or spec_agent in req_agent:
            confidence += 0.2
            reasons.append("담당 에이전트 일치")

        reason = ", ".join(reasons) if reasons else "매칭 없음"
        return min(confidence, 1.0), reason

    def _is_similar_tool(self, tool1: str, tool2: str) -> bool:
        """도구 이름 유사도 판정"""
        tool1 = tool1.lower().replace("_", "").replace("-", "")
        tool2 = tool2.lower().replace("_", "").replace("-", "")

        # 부분 문자열 포함
        if tool1 in tool2 or tool2 in tool1:
            return True

        # 레벤슈타인 거리 계산 (간단한 버전)
        if len(tool1) > 3 and len(tool2) > 3:
            # 첫 3글자 일치
            if tool1[:3] == tool2[:3]:
                return True

        return False

    def _generate_issues(
        self,
        missing_agents: List[str],
        missing_tasks: List[str],
        missing_tools: List[str],
        extra_agents: List[str],
        extra_tasks: List[str],
        extra_tools: List[str],
        agent_mappings: List[TraceabilityMapping],
        task_mappings: List[TraceabilityMapping],
    ):
        """이슈 생성"""
        # 1. 누락된 Agent
        for agent in missing_agents:
            self.issues.append(TraceabilityIssue(
                issue_type=TraceabilityIssueType.MISSING_IN_SPEC,
                severity=TraceabilitySeverity.CRITICAL,
                category="agent",
                message=f"요구사항의 Agent '{agent}'가 Spec에 반영되지 않았습니다",
                requirement_reference=agent,
                suggestion="Agent를 Spec에 추가하거나 요구사항 분석을 재확인하세요.",
            ))

        # 2. 누락된 Task
        for task in missing_tasks:
            self.issues.append(TraceabilityIssue(
                issue_type=TraceabilityIssueType.MISSING_IN_SPEC,
                severity=TraceabilitySeverity.HIGH,
                category="task",
                message=f"요구사항의 Task '{task}'가 Spec에 반영되지 않았습니다",
                requirement_reference=task,
                suggestion="Task를 Spec에 추가하거나 다른 Task에 통합되었는지 확인하세요.",
            ))

        # 3. 누락된 Tool
        for tool in missing_tools:
            self.issues.append(TraceabilityIssue(
                issue_type=TraceabilityIssueType.MISSING_IN_SPEC,
                severity=TraceabilitySeverity.MEDIUM,
                category="tool",
                message=f"요구사항의 Tool '{tool}'이 Spec에 할당되지 않았습니다",
                requirement_reference=tool,
                suggestion="Tool을 Agent에 할당하거나 대체 Tool로 변경하세요.",
            ))

        # 4. 과잉 Agent (경고 수준)
        for agent in extra_agents:
            self.issues.append(TraceabilityIssue(
                issue_type=TraceabilityIssueType.MISSING_IN_REQUIREMENT,
                severity=TraceabilitySeverity.LOW,
                category="agent",
                message=f"Spec의 Agent '{agent}'가 요구사항에 명시되지 않았습니다",
                spec_reference=agent,
                suggestion="의도적 추가인지 확인하거나 불필요하면 제거하세요.",
            ))

        # 5. 부분 매칭 Agent (중간 신뢰도)
        for mapping in agent_mappings:
            if 0.3 <= mapping.match_confidence < self.min_match_confidence:
                self.issues.append(TraceabilityIssue(
                    issue_type=TraceabilityIssueType.PARTIAL_MATCH,
                    severity=TraceabilitySeverity.MEDIUM,
                    category="agent",
                    message=f"Agent '{mapping.requirement_id}'가 부분적으로만 매핑되었습니다 (신뢰도: {mapping.match_confidence:.2f})",
                    requirement_reference=mapping.requirement_id,
                    spec_reference=mapping.spec_id,
                    suggestion=f"매핑 확인 필요: {mapping.match_reason}",
                ))

        # 6. 부분 매칭 Task
        for mapping in task_mappings:
            if 0.3 <= mapping.match_confidence < self.min_match_confidence:
                self.issues.append(TraceabilityIssue(
                    issue_type=TraceabilityIssueType.PARTIAL_MATCH,
                    severity=TraceabilitySeverity.MEDIUM,
                    category="task",
                    message=f"Task '{mapping.requirement_id}'가 부분적으로만 매핑되었습니다 (신뢰도: {mapping.match_confidence:.2f})",
                    requirement_reference=mapping.requirement_id,
                    spec_reference=mapping.spec_id,
                    suggestion=f"매핑 확인 필요: {mapping.match_reason}",
                ))

    def _calculate_coverage_score(
        self,
        total_agents: int,
        total_tasks: int,
        total_tools: int,
        missing_agents: int,
        missing_tasks: int,
        missing_tools: int,
    ) -> float:
        """커버리지 점수 계산 (0.0 ~ 1.0)"""
        if total_agents + total_tasks + total_tools == 0:
            return 1.0  # 요구사항이 없으면 100%

        # 가중치: Agent(50%), Task(40%), Tool(10%)
        agent_coverage = (total_agents - missing_agents) / total_agents if total_agents > 0 else 1.0
        task_coverage = (total_tasks - missing_tasks) / total_tasks if total_tasks > 0 else 1.0
        tool_coverage = (total_tools - missing_tools) / total_tools if total_tools > 0 else 1.0

        weighted_coverage = (
            agent_coverage * 0.5 +
            task_coverage * 0.4 +
            tool_coverage * 0.1
        )

        return weighted_coverage

    def _count_tools_in_spec(self, spec_agents: List[Dict]) -> int:
        """Spec의 총 도구 수 (중복 제거)"""
        tools = set()
        for agent in spec_agents:
            tools.update(agent.get("tools", []))
        return len(tools)

    def _issue_to_dict(self, issue: TraceabilityIssue) -> Dict[str, Any]:
        """이슈를 딕셔너리로 변환"""
        return {
            "issue_type": issue.issue_type.value,
            "severity": issue.severity.value,
            "category": issue.category,
            "message": issue.message,
            "requirement_reference": issue.requirement_reference,
            "spec_reference": issue.spec_reference,
            "suggestion": issue.suggestion,
        }

    def _mapping_to_dict(self, mapping: TraceabilityMapping) -> Dict[str, Any]:
        """매핑을 딕셔너리로 변환"""
        return {
            "requirement_id": mapping.requirement_id,
            "requirement_content": mapping.requirement_content,
            "spec_id": mapping.spec_id,
            "spec_content": mapping.spec_content,
            "match_confidence": mapping.match_confidence,
            "match_reason": mapping.match_reason,
        }
