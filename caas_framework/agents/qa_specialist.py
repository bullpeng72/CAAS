"""
QA Specialist Agent

Expert agent responsible for Phase 6 (Quality Assurance):
- Validates all phase outputs
- Performs end-to-end testing
- Checks Golden Data compliance
- Ensures production readiness
"""

from typing import Any, Dict, List, Optional

from caas_framework.agents.base import AgentPhase, BaseExpertAgent, ValidationIssue
from caas_framework.agents.registry import register_agent
from caas_framework.config.settings import LLMConstants
from caas_framework.models.specifications import ConcretizedRequirement
from caas_framework.plugins.llm.base import LLMPlugin
from caas_framework.utils import GoldenDataMatcher, ResponseParser


@register_agent(phase=AgentPhase.QUALITY_ASSURANCE)
class QASpecialistAgent(BaseExpertAgent):
    """
    QA Specialist Agent

    Specializes in quality assurance across all phases.
    Performs comprehensive validation and compliance checking.
    """

    def __init__(
        self,
        llm_plugin: LLMPlugin,
        golden_data: Optional[ConcretizedRequirement] = None,
    ):
        super().__init__(llm_plugin, golden_data, AgentPhase.QUALITY_ASSURANCE)

    @property
    def agent_name(self) -> str:
        return "QASpecialist"

    @property
    def agent_role(self) -> str:
        return "Expert Quality Assurance Specialist"

    @property
    def agent_expertise(self) -> List[str]:
        return [
            "Quality assurance",
            "Test planning",
            "Golden Data compliance checking",
            "End-to-end validation",
            "Security auditing",
            "Performance testing",
            "Code review",
            "Production readiness assessment",
        ]

    async def _do_work(
        self,
        requirement: Optional[str],
        context: Optional[Dict[str, Any]],
        previous_outputs: Optional[Dict[AgentPhase, Any]],
    ) -> Dict[str, Any]:
        """
        Perform comprehensive QA on all outputs.

        Returns:
            Dict with:
            - qa_report: Dict - Comprehensive QA report
            - compliance_check: Dict - Golden Data compliance
            - test_results: Dict - Test execution results
            - recommendations: List[str] - Improvement recommendations
            - readiness_score: float - Production readiness score
        """
        context_summary = self._build_context_summary(context, previous_outputs)

        prompt = self._build_qa_prompt(requirement, previous_outputs, context_summary)

        response = await self.llm.ainvoke(
            messages=[{"role": "user", "content": prompt}],
            response_format=LLMConstants.RESPONSE_FORMAT_JSON,
            temperature=LLMConstants.TEMPERATURE_PRECISE,  # Very low temperature for QA
        )

        qa_report = ResponseParser.parse_structured_response(
            response,
            expected_fields=["test_coverage", "validation_results", "recommendations"],
            fallback_factory=self._create_fallback_qa_report,
        )

        # Enhance with Golden Data compliance check
        if self.golden_data:
            qa_report = self._check_golden_data_compliance(qa_report, previous_outputs)

        return qa_report

    def _build_qa_prompt(
        self,
        requirement: str,
        previous_outputs: Optional[Dict[AgentPhase, Any]],
        context: str,
    ) -> str:
        """Build LLM prompt for QA analysis."""
        # ✅ v0.5.0: 한국어 출력 강제 (P0 수정)
        # Use base class template method
        output_format = {
            "qa_report": {
                "overall_quality": "excellent|good|fair|poor (우수|양호|보통|불량)",
                "phase_assessments": {
                    "discovery": {"score": "0-10", "issues": ["문제점"], "strengths": ["강점"]},
                    "architecture": {
                        "score": "0-10",
                        "issues": ["문제점"],
                        "strengths": ["강점"],
                    },
                    "design": {"score": "0-10", "issues": ["문제점"], "strengths": ["강점"]},
                    "delivery": {"score": "0-10", "issues": ["문제점"], "strengths": ["강점"]},
                },
            },
            "compliance_check": {
                "golden_data_alignment": "0-100",
                "requirement_coverage": "0-100",
                "completeness": "0-100",
                "non_compliant_items": ["미준수 항목"],
            },
            "test_results": {
                "unit_tests": "pass|fail|not_run (통과|실패|미실행)",
                "integration_tests": "pass|fail|not_run (통과|실패|미실행)",
                "e2e_tests": "pass|fail|not_run (통과|실패|미실행)",
                "test_coverage": "0-100",
            },
            "security_assessment": {
                "vulnerabilities": ["취약점 설명"],
                "security_score": "0-10",
                "recommendations": ["보안 권장사항"],
            },
            "performance_assessment": {
                "scalability": "0-10",
                "efficiency": "0-10",
                "bottlenecks": ["성능 병목 지점"],
            },
            "recommendations": [
                "구체적인 권장사항 1",
                "구체적인 권장사항 2",
            ],
            "readiness_score": "0-100",
            "production_ready": "true|false",
        }

        guidelines = [
            "**중요: 모든 텍스트 값(issues, strengths, recommendations 등)을 한국어로 작성하세요**",
            "JSON 키(key)는 영어로 유지하되, 값(value)은 반드시 한국어로 작성하세요",
            "철저하고 비판적으로 분석하세요",
            "모든 문제점을 식별하고 실행 가능한 권장사항을 제공하세요",
            "Golden Data 명세와의 정렬을 검증하세요",
            "프로덕션 준비 상태를 객관적으로 평가하세요",
        ]

        return self._build_standard_prompt(
            requirement=requirement,
            output_format=output_format,
            guidelines=guidelines,
            context={"additional_context": context} if context else None,
            previous_outputs=previous_outputs,
        )

    def _create_fallback_qa_report(self) -> Dict[str, Any]:
        """Create basic QA report when LLM fails."""
        return {
            "qa_report": {"overall_quality": "unknown", "phase_assessments": {}},
            "compliance_check": {
                "golden_data_alignment": 0,
                "requirement_coverage": 0,
                "completeness": 0,
                "non_compliant_items": [],
            },
            "test_results": {
                "unit_tests": "not_run",
                "integration_tests": "not_run",
                "e2e_tests": "not_run",
                "test_coverage": 0,
            },
            "security_assessment": {
                "vulnerabilities": [],
                "security_score": 0,
                "recommendations": [],
            },
            "performance_assessment": {
                "scalability": 0,
                "efficiency": 0,
                "bottlenecks": [],
            },
            "recommendations": ["QA analysis could not be completed"],
            "readiness_score": 0,
            "production_ready": False,
        }

    def _check_golden_data_compliance(
        self,
        qa_report: Dict[str, Any],
        previous_outputs: Optional[Dict[AgentPhase, Any]],
    ) -> Dict[str, Any]:
        """Check compliance with Golden Data."""
        if not self.golden_data or not previous_outputs:
            return qa_report

        compliance = qa_report.setdefault("compliance_check", {})

        # Check feature coverage using task_feature_map from design phase
        design_output = previous_outputs.get(AgentPhase.DESIGN, {})
        if isinstance(design_output, dict):
            task_feature_map = design_output.get("task_feature_map", {})

            # Calculate coverage metrics
            coverage_metrics = GoldenDataMatcher.calculate_coverage(
                features=self.golden_data.features, item_feature_map=task_feature_map
            )

            compliance["feature_coverage"] = coverage_metrics["coverage_percentage"]
            compliance["uncovered_features"] = coverage_metrics["uncovered_features"]

        # Check data model coverage
        architecture_output = previous_outputs.get(AgentPhase.ARCHITECTURE, {})
        if isinstance(architecture_output, dict):
            components = architecture_output.get("components", [])
            has_db = any(c.get("type") == "database" for c in components)

            if self.golden_data.data_models and not has_db:
                compliance.setdefault("non_compliant_items", []).append(
                    "Data models defined but no database component in architecture"
                )

        return qa_report

    async def _refine_implementation(
        self,
        output: Dict[str, Any],
        issues: List[ValidationIssue],
        context: Optional[Dict[str, Any]],
        iteration: int,
    ) -> Dict[str, Any]:
        """
        Refine QA report based on feedback.

        QA Specialist typically doesn't need refinement as it's the final checker.
        This method is here for completeness.
        """
        return output
