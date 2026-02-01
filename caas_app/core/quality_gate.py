"""
Quality Gate System

BMAD 파이프라인의 각 단계에서 품질을 체크하고 자동 회귀를 수행하는 시스템
"""

from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from pydantic import BaseModel, Field

from caas_framework.models.analysis import QualityMetrics
from caas_app.core.spec_validator import SpecValidator
from caas_framework.utils.logger import get_logger

# Phase 3.2: Monitoring Integration
from caas_app.monitoring.usage_analytics import get_usage_analytics, EventType

logger = get_logger("quality_gate")


class QualityGatePhase(str, Enum):
    """Quality Gate가 적용되는 단계"""
    DISCOVERY = "discovery"
    ARCHITECTURE = "architecture"
    DESIGN = "design"
    DEVELOPMENT = "development"


class QualityGateStatus(str, Enum):
    """Quality Gate 통과 여부"""
    PASS = "pass"  # 품질 기준 통과
    CONDITIONAL_PASS = "conditional_pass"  # 경고가 있지만 통과
    FAIL = "fail"  # 품질 기준 미달, 재작업 필요


class QualityGateResult(BaseModel):
    """Quality Gate 검증 결과"""
    phase: QualityGatePhase
    status: QualityGateStatus
    overall_score: float = Field(ge=0.0, le=1.0, description="전체 품질 점수")

    # 세부 점수
    completeness_score: Optional[float] = None
    consistency_score: Optional[float] = None
    quality_score: Optional[float] = None

    # 이슈
    errors: List[str] = []
    warnings: List[str] = []
    suggestions: List[str] = []

    # 판정
    requires_rework: bool = False
    can_proceed: bool = True


class QualityGate:
    """
    Quality Gate 시스템

    각 BMAD 단계에서 품질을 평가하고 다음 단계 진행 여부를 결정합니다.
    """

    # 각 단계별 품질 임계값
    THRESHOLDS = {
        QualityGatePhase.DISCOVERY: {
            "min_score": 0.6,  # 최소 품질 점수
            "warning_score": 0.7,  # 경고 임계값
            "target_score": 0.8,  # 목표 점수
        },
        QualityGatePhase.ARCHITECTURE: {
            "min_score": 0.65,
            "warning_score": 0.75,
            "target_score": 0.85,
        },
        QualityGatePhase.DESIGN: {
            "min_score": 0.7,
            "warning_score": 0.8,
            "target_score": 0.9,
        },
        QualityGatePhase.DEVELOPMENT: {
            "min_score": 0.75,
            "warning_score": 0.85,
            "target_score": 0.95,
        },
    }

    @classmethod
    def check_discovery_phase(
        cls,
        requirement_analysis: Dict[str, Any],
        quality_metrics: Optional[QualityMetrics] = None,
        session_id: Optional[str] = None,
    ) -> QualityGateResult:
        """
        Discovery 단계 품질 검증

        Args:
            requirement_analysis: RequirementAnalysis 결과
            quality_metrics: 품질 메트릭 (없으면 자동 계산)

        Returns:
            QualityGateResult: 검증 결과
        """
        logger.info("Quality Gate: Discovery 단계 검증")

        # Quality Metrics 가져오기
        if quality_metrics is None:
            from caas_framework.models.analysis import RequirementAnalysis
            analysis_obj = RequirementAnalysis(**requirement_analysis)
            quality_metrics = analysis_obj.compute_quality_metrics()

        # 임계값 가져오기
        thresholds = cls.THRESHOLDS[QualityGatePhase.DISCOVERY]

        # 전체 점수
        overall_score = quality_metrics.overall_quality or quality_metrics.confidence_score

        # 에러/경고 수집
        errors = []
        warnings = []
        suggestions = quality_metrics.improvement_suggestions

        # 심각한 품질 이슈 확인
        for issue in quality_metrics.quality_issues:
            if "불완전" in issue or "일관" in issue:
                errors.append(issue)
            else:
                warnings.append(issue)

        # 상태 판정
        if overall_score < thresholds["min_score"] or len(errors) > 0:
            status = QualityGateStatus.FAIL
            requires_rework = True
            can_proceed = False
        elif overall_score < thresholds["warning_score"]:
            status = QualityGateStatus.CONDITIONAL_PASS
            requires_rework = False
            can_proceed = True
        else:
            status = QualityGateStatus.PASS
            requires_rework = False
            can_proceed = True

        result = QualityGateResult(
            phase=QualityGatePhase.DISCOVERY,
            status=status,
            overall_score=overall_score,
            completeness_score=quality_metrics.completeness_score,
            consistency_score=quality_metrics.consistency_score,
            quality_score=quality_metrics.confidence_score,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions,
            requires_rework=requires_rework,
            can_proceed=can_proceed,
        )

        cls._log_result(result, session_id=session_id)
        return result

    @classmethod
    def check_architecture_phase(
        cls,
        architecture_design: Dict[str, Any],
        session_id: Optional[str] = None,
    ) -> QualityGateResult:
        """
        Architecture 단계 품질 검증

        Args:
            architecture_design: ArchitectureDesign 결과

        Returns:
            QualityGateResult: 검증 결과
        """
        logger.info("Quality Gate: Architecture 단계 검증")

        thresholds = cls.THRESHOLDS[QualityGatePhase.ARCHITECTURE]

        # 기본 점수
        design_confidence = architecture_design.get("design_confidence", 0.7)
        complexity = architecture_design.get("complexity_estimate", 5)

        # 복잡도 정규화 (1-10 -> 0-1, 반비례)
        normalized_complexity = 1.0 - (complexity - 1) / 9.0

        # 전체 점수 계산
        overall_score = (design_confidence * 0.7 + normalized_complexity * 0.3)

        # 검증
        errors = []
        warnings = []
        suggestions = []

        # 필수 필드 확인
        required_fields = ["project_name", "architectural_pattern", "components", "technology_stack"]
        for field in required_fields:
            if field not in architecture_design or not architecture_design[field]:
                errors.append(f"필수 필드 '{field}'가 누락되었습니다.")

        # Component 수 확인
        components = architecture_design.get("components", [])
        if len(components) == 0:
            errors.append("컴포넌트가 정의되지 않았습니다.")
        elif len(components) > 15:
            warnings.append(f"컴포넌트 수가 너무 많습니다 ({len(components)}개). 10개 이하를 권장합니다.")

        # 상태 판정
        if overall_score < thresholds["min_score"] or len(errors) > 0:
            status = QualityGateStatus.FAIL
            requires_rework = True
            can_proceed = False
        elif overall_score < thresholds["warning_score"] or len(warnings) > 3:
            status = QualityGateStatus.CONDITIONAL_PASS
            requires_rework = False
            can_proceed = True
        else:
            status = QualityGateStatus.PASS
            requires_rework = False
            can_proceed = True

        result = QualityGateResult(
            phase=QualityGatePhase.ARCHITECTURE,
            status=status,
            overall_score=round(overall_score, 3),
            quality_score=design_confidence,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions,
            requires_rework=requires_rework,
            can_proceed=can_proceed,
        )

        cls._log_result(result, session_id=session_id)
        return result

    @classmethod
    def check_design_phase(
        cls,
        agent_specs: List[Dict[str, Any]],
        task_specs: List[Dict[str, Any]],
        session_id: Optional[str] = None,
    ) -> QualityGateResult:
        """
        Design 단계 품질 검증

        Args:
            agent_specs: Agent 스펙 리스트
            task_specs: Task 스펙 리스트

        Returns:
            QualityGateResult: 검증 결과
        """
        logger.info("Quality Gate: Design 단계 검증")

        thresholds = cls.THRESHOLDS[QualityGatePhase.DESIGN]

        errors = []
        warnings = []
        suggestions = []

        # 1. Agent 검증
        if len(agent_specs) == 0:
            errors.append("Agent가 하나도 정의되지 않았습니다.")

        for agent in agent_specs:
            if not agent.get("id"):
                errors.append("Agent ID가 누락되었습니다.")
            if not agent.get("role"):
                errors.append(f"Agent '{agent.get('id', 'unknown')}'의 role이 누락되었습니다.")
            if not agent.get("tools"):
                warnings.append(f"Agent '{agent.get('id', 'unknown')}'에 도구가 할당되지 않았습니다.")

        # 2. Task 검증
        if len(task_specs) == 0:
            errors.append("Task가 하나도 정의되지 않았습니다.")

        for task in task_specs:
            if not task.get("id"):
                errors.append("Task ID가 누락되었습니다.")
            if not task.get("agent"):
                errors.append(f"Task '{task.get('id', 'unknown')}'에 agent가 할당되지 않았습니다.")

        # 3. 일관성 검증
        agent_ids = {a.get("id") for a in agent_specs if a.get("id")}
        for task in task_specs:
            task_agent = task.get("agent")
            if task_agent and task_agent not in agent_ids:
                errors.append(f"Task '{task.get('id')}'가 존재하지 않는 agent '{task_agent}'를 참조합니다.")

        # 품질 점수 계산
        completeness = 1.0 - (len(errors) * 0.2 + len(warnings) * 0.05)
        consistency = 1.0 if len(errors) == 0 else 0.5
        overall_score = (completeness + consistency) / 2.0
        overall_score = max(0.0, min(1.0, overall_score))

        # 상태 판정
        if overall_score < thresholds["min_score"] or len(errors) > 0:
            status = QualityGateStatus.FAIL
            requires_rework = True
            can_proceed = False
        elif overall_score < thresholds["warning_score"]:
            status = QualityGateStatus.CONDITIONAL_PASS
            requires_rework = False
            can_proceed = True
        else:
            status = QualityGateStatus.PASS
            requires_rework = False
            can_proceed = True

        result = QualityGateResult(
            phase=QualityGatePhase.DESIGN,
            status=status,
            overall_score=round(overall_score, 3),
            completeness_score=completeness,
            consistency_score=consistency,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions,
            requires_rework=requires_rework,
            can_proceed=can_proceed,
        )

        cls._log_result(result, session_id=session_id)
        return result

    @classmethod
    def check_development_phase(
        cls,
        spec_yaml: str,
        session_id: Optional[str] = None,
    ) -> QualityGateResult:
        """
        Development 단계 품질 검증

        Args:
            spec_yaml: 생성된 YAML 스펙

        Returns:
            QualityGateResult: 검증 결과
        """
        logger.info("Quality Gate: Development 단계 검증")

        thresholds = cls.THRESHOLDS[QualityGatePhase.DEVELOPMENT]

        # SpecValidator 사용
        validation_result = SpecValidator.validate_spec(spec_yaml)

        # 에러/경고 추출
        errors = [issue.message for issue in validation_result.issues if issue.severity == "error"]
        warnings = [issue.message for issue in validation_result.issues if issue.severity == "warning"]
        suggestions = [issue.suggestion for issue in validation_result.issues if issue.suggestion]

        overall_score = validation_result.quality_score

        # 상태 판정
        if not validation_result.is_valid or overall_score < thresholds["min_score"]:
            status = QualityGateStatus.FAIL
            requires_rework = True
            can_proceed = False
        elif overall_score < thresholds["warning_score"]:
            status = QualityGateStatus.CONDITIONAL_PASS
            requires_rework = False
            can_proceed = True
        else:
            status = QualityGateStatus.PASS
            requires_rework = False
            can_proceed = True

        result = QualityGateResult(
            phase=QualityGatePhase.DEVELOPMENT,
            status=status,
            overall_score=overall_score,
            quality_score=overall_score,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions,
            requires_rework=requires_rework,
            can_proceed=can_proceed,
        )

        cls._log_result(result, session_id=session_id)
        return result

    @classmethod
    def _log_result(cls, result: QualityGateResult, session_id: Optional[str] = None):
        """검증 결과를 로깅하고 analytics 이벤트를 추적합니다"""
        status_emoji = {
            QualityGateStatus.PASS: "✅",
            QualityGateStatus.CONDITIONAL_PASS: "⚠️",
            QualityGateStatus.FAIL: "❌",
        }

        emoji = status_emoji[result.status]
        logger.info(f"{emoji} Quality Gate: {result.phase} - {result.status} (score: {result.overall_score:.2f})")

        if result.errors:
            logger.warning(f"  Errors: {len(result.errors)}")
            for error in result.errors[:3]:  # 최대 3개만 로깅
                logger.warning(f"    - {error}")

        if result.warnings:
            logger.info(f"  Warnings: {len(result.warnings)}")

        if result.requires_rework:
            logger.warning(f"  ⚠️ 재작업 필요")

        # Phase 3.2: Track quality gate event
        if session_id:
            analytics = get_usage_analytics()
            event_type = EventType.QUALITY_GATE_PASS if result.can_proceed else EventType.QUALITY_GATE_FAIL
            analytics.track_event(
                event_type=event_type,
                session_id=session_id,
                phase=result.phase.value,
                metadata={
                    "status": result.status.value,
                    "overall_score": result.overall_score,
                    "errors": len(result.errors),
                    "warnings": len(result.warnings),
                    "requires_rework": result.requires_rework,
                },
            )


# =============================================================================
# Golden Data Quality Gate (Phase 0 Integration)
# =============================================================================

class GoldenDataQualityGate:
    """
    Golden Data 기반 Quality Gate

    각 Phase 출력을 ConcretizedRequirement (Golden Data)와 비교하여 검증합니다.
    """

    @classmethod
    def check_with_golden_data(
        cls,
        phase: QualityGatePhase,
        phase_output: Any,
        golden_validator: Any,  # GoldenDataValidator instance
        auto_fixer: Optional[Any] = None,  # AutoFixer instance (optional)
        enable_auto_fix: bool = True,
    ) -> Tuple[QualityGateResult, Optional[Dict[str, Any]]]:
        """
        Golden Data 기준으로 Phase 출력 검증 및 자동 수정

        Args:
            phase: 검증할 Phase
            phase_output: Phase 출력 (RequirementAnalysis, ArchitectureDesign, etc.)
            golden_validator: GoldenDataValidator 인스턴스
            auto_fixer: AutoFixer 인스턴스 (선택적)
            enable_auto_fix: 자동 수정 활성화 여부

        Returns:
            (QualityGateResult, 수정된 출력 or None)
        """

        logger.info(f"🔍 Golden Data Quality Gate - {phase.value.upper()} Phase")

        # 1. 기존 Quality Gate 검증
        if phase == QualityGatePhase.DISCOVERY:
            basic_result = QualityGate.check_discovery_phase(
                requirement_analysis=phase_output if isinstance(phase_output, dict) else phase_output.model_dump()
            )
        elif phase == QualityGatePhase.ARCHITECTURE:
            basic_result = QualityGate.check_architecture_phase(
                architecture_design=phase_output if isinstance(phase_output, dict) else phase_output.model_dump()
            )
        elif phase == QualityGatePhase.DESIGN:
            basic_result = QualityGate.check_design_phase(
                agent_specs=phase_output.get("agents", []) if isinstance(phase_output, dict) else [],
                task_specs=phase_output.get("tasks", []) if isinstance(phase_output, dict) else [],
            )
        elif phase == QualityGatePhase.DEVELOPMENT:
            basic_result = QualityGate.check_development_phase(
                spec_yaml=phase_output.get("spec_yaml", "") if isinstance(phase_output, dict) else ""
            )
        else:
            raise ValueError(f"Unknown phase: {phase}")

        # 2. Golden Data 검증
        golden_report = None
        fixed_output = None

        try:
            # Phase별 Golden Data 검증 실행
            if phase == QualityGatePhase.DISCOVERY:
                golden_report = golden_validator.validate_discovery(phase_output)
            elif phase == QualityGatePhase.ARCHITECTURE:
                golden_report = golden_validator.validate_architecture(phase_output)
            elif phase == QualityGatePhase.DESIGN:
                agent_specs = phase_output.get("agents", []) if isinstance(phase_output, dict) else []
                task_specs = phase_output.get("tasks", []) if isinstance(phase_output, dict) else []
                golden_report = golden_validator.validate_design(agent_specs, task_specs)
            elif phase == QualityGatePhase.DEVELOPMENT:
                spec_dict = phase_output if isinstance(phase_output, dict) else {}
                golden_report = golden_validator.validate_code(spec_dict)

            # 3. Golden Data 검증 결과 통합
            if golden_report:
                # Coverage Score를 Quality Gate에 반영
                golden_coverage = golden_report.coverage_score

                # 기존 Overall Score와 Golden Coverage Score 결합
                combined_score = (basic_result.overall_score * 0.5) + (golden_coverage * 0.5)

                # Golden Data 이슈를 Quality Gate에 추가
                for missing_item in golden_report.missing_items:
                    basic_result.errors.append(
                        f"[Golden Data] Missing {missing_item.item_type}: {missing_item.item_name}"
                    )

                for extra_item in golden_report.extra_items:
                    basic_result.warnings.append(
                        f"[Golden Data] Extra {extra_item.item_type}: {extra_item.item_name} (possible hallucination)"
                    )

                # Recommendations 추가
                basic_result.suggestions.extend(golden_report.recommendations)

                # Overall Score 업데이트
                basic_result.overall_score = combined_score

                # Status 재평가
                threshold = QualityGate.THRESHOLDS[phase]
                if combined_score >= threshold["target_score"]:
                    basic_result.status = QualityGateStatus.PASS
                    basic_result.can_proceed = True
                    basic_result.requires_rework = False
                elif combined_score >= threshold["min_score"]:
                    basic_result.status = QualityGateStatus.CONDITIONAL_PASS
                    basic_result.can_proceed = True
                    basic_result.requires_rework = False
                else:
                    basic_result.status = QualityGateStatus.FAIL
                    basic_result.can_proceed = False
                    basic_result.requires_rework = True

                logger.info(
                    f"📊 Golden Data Coverage: {golden_coverage:.2%}, "
                    f"Combined Score: {combined_score:.2%}, "
                    f"Status: {basic_result.status.value}"
                )

                # 4. 자동 수정 (needs_fixing=True인 경우)
                if golden_report.needs_fixing and enable_auto_fix and auto_fixer:
                    logger.info("🔧 Auto-fixing enabled - attempting to fix issues...")

                    try:
                        if phase == QualityGatePhase.DISCOVERY:
                            fix_result = auto_fixer.fix_discovery(phase_output, golden_report)
                        elif phase == QualityGatePhase.ARCHITECTURE:
                            fix_result = auto_fixer.fix_architecture(phase_output, golden_report)
                        elif phase == QualityGatePhase.DESIGN:
                            agent_specs = phase_output.get("agents", []) if isinstance(phase_output, dict) else []
                            task_specs = phase_output.get("tasks", []) if isinstance(phase_output, dict) else []
                            fix_result = auto_fixer.fix_design(agent_specs, task_specs, golden_report)
                        elif phase == QualityGatePhase.DEVELOPMENT:
                            spec_dict = phase_output if isinstance(phase_output, dict) else {}
                            fix_result = auto_fixer.fix_code(spec_dict, golden_report)
                        else:
                            fix_result = None

                        if fix_result and fix_result.success:
                            fixed_output = fix_result.fixed_output
                            logger.info(f"✅ Auto-fix successful - {len(fix_result.fixes_applied)} fixes applied")

                            for fix in fix_result.fixes_applied:
                                logger.info(f"  ✓ {fix}")

                            # 수정 후 상태 개선
                            basic_result.warnings.append("Auto-fix applied - output has been corrected")
                        else:
                            logger.warning("⚠️ Auto-fix failed or not applicable")

                    except Exception as e:
                        logger.error(f"❌ Auto-fix error: {str(e)}")

        except Exception as e:
            logger.error(f"❌ Golden Data validation error: {str(e)}")
            basic_result.warnings.append(f"Golden Data validation failed: {str(e)}")

        return (basic_result, fixed_output)
