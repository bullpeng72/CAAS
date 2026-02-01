"""
BMAD Reflection Engine (CORE - Collaboration Optimized Reflection Engine)

생성된 결과를 자체 평가하고 개선하는 피드백 루프
"""

from typing import List, Dict, Optional
from pydantic import BaseModel, Field
import ast

import logging, LoggerMixin

logger = logging.getLogger("caas_framework.bmad.reflection")


class ReflectionFeedback(BaseModel):
    """반성 피드백"""
    aspect: str  # "code_quality", "spec_clarity", "test_coverage"
    score: float = Field(ge=0.0, le=1.0, description="평가 점수 (0.0 ~ 1.0)")
    issues: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    severity: str = "info"  # "critical", "warning", "info"


class ReflectionResult(BaseModel):
    """반성 결과"""
    overall_score: float = Field(ge=0.0, le=1.0)
    feedbacks: List[ReflectionFeedback]
    requires_iteration: bool
    iteration_plan: Optional[str] = None
    iteration_count: int = 0


class ReflectionEngine(LoggerMixin):
    """
    협업 최적화 반성 엔진 (CORE)

    생성된 스펙과 코드를 자동으로 평가하고 개선 방안을 제시합니다.
    BMAD 방법론의 핵심 기능으로 품질을 자동으로 보장합니다.
    """

    def __init__(self, quality_threshold: float = 0.7):
        """
        Args:
            quality_threshold: 품질 임계값 (이하면 재생성)
        """
        self.quality_threshold = quality_threshold
        self.logger.info(f"ReflectionEngine 초기화: threshold={quality_threshold}")

    def reflect_on_spec(
        self,
        spec_yaml: str,
        requirement: str,
        use_llm: bool = False
    ) -> ReflectionResult:
        """
        스펙에 대한 반성

        Args:
            spec_yaml: 생성된 CrewAI YAML 스펙
            requirement: 원본 요구사항
            use_llm: LLM 기반 평가 사용 여부

        Returns:
            ReflectionResult: 반성 결과
        """
        self.logger.info("스펙 반성 시작")

        feedbacks = []

        # 1. 구조 검증
        structure_feedback = self._evaluate_spec_structure(spec_yaml)
        feedbacks.append(structure_feedback)

        # 2. 완전성 검증
        completeness_feedback = self._evaluate_spec_completeness(spec_yaml, requirement)
        feedbacks.append(completeness_feedback)

        # 3. LLM 기반 품질 평가 (선택적)
        if use_llm:
            try:
                quality_feedback = self._evaluate_spec_with_llm(spec_yaml, requirement)
                feedbacks.append(quality_feedback)
            except Exception as e:
                self.logger.warning(f"LLM 평가 실패: {e}")

        # 전체 점수 계산
        overall_score = sum(f.score for f in feedbacks) / len(feedbacks) if feedbacks else 0.0

        result = ReflectionResult(
            overall_score=overall_score,
            feedbacks=feedbacks,
            requires_iteration=overall_score < self.quality_threshold,
            iteration_plan=self._create_iteration_plan(feedbacks) if overall_score < self.quality_threshold else None
        )

        self.logger.info(f"스펙 반성 완료: 점수={overall_score:.2f}, 재생성 필요={result.requires_iteration}")
        return result

    def reflect_on_code(
        self,
        code_files: Dict[str, str],
        spec_yaml: str
    ) -> ReflectionResult:
        """
        생성된 코드에 대한 반성

        Args:
            code_files: 파일명 -> 코드 매핑
            spec_yaml: CrewAI 스펙

        Returns:
            ReflectionResult: 반성 결과
        """
        self.logger.info(f"코드 반성 시작: {len(code_files)}개 파일")

        feedbacks = []

        # 1. 코드 품질 평가
        quality_feedback = self._evaluate_code_quality(code_files)
        feedbacks.append(quality_feedback)

        # 2. 스펙 준수도 평가
        compliance_feedback = self._evaluate_spec_compliance(code_files, spec_yaml)
        feedbacks.append(compliance_feedback)

        # 3. 베스트 프랙티스 준수 평가
        best_practices_feedback = self._evaluate_best_practices(code_files)
        feedbacks.append(best_practices_feedback)

        # 4. 테스트 커버리지 평가
        test_coverage_feedback = self._evaluate_test_coverage(code_files)
        feedbacks.append(test_coverage_feedback)

        overall_score = sum(f.score for f in feedbacks) / len(feedbacks)

        result = ReflectionResult(
            overall_score=overall_score,
            feedbacks=feedbacks,
            requires_iteration=overall_score < 0.75,  # 코드는 더 높은 기준
            iteration_plan=self._create_code_iteration_plan(feedbacks) if overall_score < 0.75 else None
        )

        self.logger.info(f"코드 반성 완료: 점수={overall_score:.2f}, 재생성 필요={result.requires_iteration}")
        return result

    # ========================================================================
    # 스펙 평가 메서드
    # ========================================================================

    def _evaluate_spec_structure(self, spec_yaml: str) -> ReflectionFeedback:
        """스펙 구조 검증"""
        issues = []
        score = 1.0

        # YAML 파싱 가능 여부
        try:
            import yaml
            spec_dict = yaml.safe_load(spec_yaml)
        except Exception as e:
            issues.append(f"YAML 파싱 실패: {str(e)}")
            return ReflectionFeedback(
                aspect="spec_structure",
                score=0.0,
                issues=issues,
                suggestions=["YAML 구문을 수정하세요"],
                severity="critical"
            )

        # 필수 필드 검증
        required_fields = ["project", "agents", "tasks", "crew"]
        for field in required_fields:
            if field not in spec_dict:
                issues.append(f"필수 필드 누락: {field}")
                score -= 0.25

        return ReflectionFeedback(
            aspect="spec_structure",
            score=max(0.0, score),
            issues=issues,
            suggestions=["누락된 필드를 추가하세요"] if issues else [],
            severity="critical" if score < 0.5 else "warning"
        )

    def _evaluate_spec_completeness(self, spec_yaml: str, requirement: str) -> ReflectionFeedback:
        """스펙 완전성 검증"""
        import yaml

        issues = []
        suggestions = []
        score = 1.0

        try:
            spec_dict = yaml.safe_load(spec_yaml)

            # 에이전트 개수
            agents = spec_dict.get("agents", [])
            if len(agents) == 0:
                issues.append("에이전트가 정의되지 않음")
                score -= 0.4
            elif len(agents) < 2:
                suggestions.append("최소 2개 이상의 에이전트 권장")
                score -= 0.1

            # 태스크 개수
            tasks = spec_dict.get("tasks", [])
            if len(tasks) == 0:
                issues.append("태스크가 정의되지 않음")
                score -= 0.4
            elif len(tasks) < len(agents):
                suggestions.append("태스크 수가 에이전트 수보다 적음")
                score -= 0.1

            # 태스크-에이전트 할당
            agent_ids = {a.get("id") for a in agents if isinstance(a, dict)}
            unassigned_tasks = 0
            for task in tasks:
                if isinstance(task, dict):
                    assigned_agent = task.get("agent")
                    if not assigned_agent or assigned_agent not in agent_ids:
                        unassigned_tasks += 1

            if unassigned_tasks > 0:
                issues.append(f"{unassigned_tasks}개 태스크가 에이전트에 할당되지 않음")
                score -= 0.2

        except Exception as e:
            issues.append(f"완전성 검증 실패: {str(e)}")
            score = 0.5

        return ReflectionFeedback(
            aspect="spec_completeness",
            score=max(0.0, score),
            issues=issues,
            suggestions=suggestions,
            severity="warning" if score >= 0.5 else "critical"
        )

    def _evaluate_spec_with_llm(self, spec_yaml: str, requirement: str) -> ReflectionFeedback:
        """LLM 기반 스펙 품질 평가"""
        # LLM 평가는 비용이 높으므로 간단한 휴리스틱으로 대체
        # 실제 구현 시 LLMClient를 사용하여 평가 가능

        return ReflectionFeedback(
            aspect="spec_quality_llm",
            score=0.8,  # 기본 점수
            issues=[],
            suggestions=["LLM 기반 평가는 선택적 기능입니다"],
            severity="info"
        )

    # ========================================================================
    # 코드 평가 메서드
    # ========================================================================

    def _evaluate_code_quality(self, code_files: Dict[str, str]) -> ReflectionFeedback:
        """코드 품질 평가"""
        issues = []
        suggestions = []
        score = 1.0

        python_files = {k: v for k, v in code_files.items() if k.endswith('.py')}

        for filename, code in python_files.items():
            # 구문 검증
            try:
                ast.parse(code)
            except SyntaxError as e:
                issues.append(f"{filename}: 구문 오류 (line {e.lineno})")
                score -= 0.3

            # 코드 길이
            lines = code.split('\n')
            if len(lines) > 500:
                suggestions.append(f"{filename}: 파일이 너무 길 (500줄 초과)")
                score -= 0.05

            # Docstring 체크
            if '"""' not in code and "'''" not in code:
                suggestions.append(f"{filename}: Docstring 부족")
                score -= 0.05

        return ReflectionFeedback(
            aspect="code_quality",
            score=max(0.0, score),
            issues=issues,
            suggestions=suggestions,
            severity="critical" if issues else "info"
        )

    def _evaluate_spec_compliance(self, code_files: Dict[str, str], spec_yaml: str) -> ReflectionFeedback:
        """스펙 준수도 평가"""
        import yaml

        issues = []
        suggestions = []
        score = 1.0

        try:
            spec_dict = yaml.safe_load(spec_yaml)
            agents = spec_dict.get("agents", [])
            tasks = spec_dict.get("tasks", [])

            # agents.py 파일 확인
            agent_file = code_files.get("agents.py", "")
            if not agent_file:
                issues.append("agents.py 파일이 생성되지 않음")
                score -= 0.4
            else:
                # 각 에이전트가 코드에 존재하는지 확인
                for agent in agents:
                    if isinstance(agent, dict):
                        agent_id = agent.get("id", "")
                        if agent_id and agent_id not in agent_file:
                            issues.append(f"에이전트 '{agent_id}'가 코드에 없음")
                            score -= 0.1

            # tasks.py 파일 확인
            task_file = code_files.get("tasks.py", "")
            if not task_file:
                issues.append("tasks.py 파일이 생성되지 않음")
                score -= 0.4

        except Exception as e:
            self.logger.warning(f"스펙 준수도 평가 실패: {e}")
            score = 0.8  # 평가 실패 시 기본 점수

        return ReflectionFeedback(
            aspect="spec_compliance",
            score=max(0.0, score),
            issues=issues,
            suggestions=suggestions,
            severity="critical" if score < 0.5 else "warning"
        )

    def _evaluate_best_practices(self, code_files: Dict[str, str]) -> ReflectionFeedback:
        """베스트 프랙티스 준수 평가"""
        suggestions = []
        score = 1.0

        python_files = {k: v for k, v in code_files.items() if k.endswith('.py')}

        for filename, code in python_files.items():
            # Type hints 체크
            if '->' not in code and ':' not in code:
                suggestions.append(f"{filename}: Type hints 부족")
                score -= 0.05

            # 위험한 패턴 체크
            if 'eval(' in code or 'exec(' in code:
                suggestions.append(f"{filename}: eval/exec 사용 지양")
                score -= 0.1

            # 하드코딩된 비밀번호 체크
            if 'password' in code.lower() and '=' in code:
                suggestions.append(f"{filename}: 하드코딩된 비밀번호 가능성")
                score -= 0.1

        return ReflectionFeedback(
            aspect="best_practices",
            score=max(0.0, score),
            issues=[],
            suggestions=suggestions,
            severity="info"
        )

    def _evaluate_test_coverage(self, code_files: Dict[str, str]) -> ReflectionFeedback:
        """테스트 커버리지 평가"""
        test_files = {k: v for k, v in code_files.items() if 'test' in k.lower()}
        code_files_count = len([k for k in code_files.keys() if k.endswith('.py') and 'test' not in k.lower()])

        issues = []
        suggestions = []

        if not test_files:
            issues.append("테스트 파일이 없음")
            score = 0.3
        elif len(test_files) < code_files_count * 0.5:
            suggestions.append("테스트 파일이 부족함")
            score = 0.6
        else:
            score = 0.9

        return ReflectionFeedback(
            aspect="test_coverage",
            score=score,
            issues=issues,
            suggestions=suggestions,
            severity="warning" if issues else "info"
        )

    # ========================================================================
    # 개선 계획 생성
    # ========================================================================

    def _create_iteration_plan(self, feedbacks: List[ReflectionFeedback]) -> str:
        """스펙 개선 계획 생성"""
        plan_parts = ["# 스펙 개선 계획\n"]

        critical_issues = []
        warnings = []

        for fb in feedbacks:
            if fb.severity == "critical" and fb.issues:
                critical_issues.extend(fb.issues)
            elif fb.issues or fb.suggestions:
                warnings.extend(fb.issues + fb.suggestions)

        if critical_issues:
            plan_parts.append("## 🚨 긴급 수정 필요\n")
            for i, issue in enumerate(critical_issues, 1):
                plan_parts.append(f"{i}. {issue}\n")

        if warnings:
            plan_parts.append("\n## ⚠️ 개선 권장\n")
            for i, warning in enumerate(warnings, 1):
                plan_parts.append(f"{i}. {warning}\n")

        return ''.join(plan_parts)

    def _create_code_iteration_plan(self, feedbacks: List[ReflectionFeedback]) -> str:
        """코드 개선 계획 생성"""
        plan_parts = ["# 코드 개선 계획\n"]

        for fb in feedbacks:
            if fb.score < 0.7:
                plan_parts.append(f"\n## {fb.aspect}\n")
                plan_parts.append(f"현재 점수: {fb.score:.2f}\n\n")

                if fb.issues:
                    plan_parts.append("**문제점:**\n")
                    for issue in fb.issues:
                        plan_parts.append(f"- {issue}\n")

                if fb.suggestions:
                    plan_parts.append("\n**개선 방안:**\n")
                    for suggestion in fb.suggestions:
                        plan_parts.append(f"- {suggestion}\n")

        return ''.join(plan_parts)
