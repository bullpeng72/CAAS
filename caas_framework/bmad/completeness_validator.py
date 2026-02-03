"""
Completeness Validator

Phase 3: Validate that all features are implemented in generated code
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from caas_framework.utils.logger import get_logger

from caas_framework.bmad.code_analyzer import CodeAnalyzer
from caas_framework.bmad.semantic_mapper import FeatureImplementation, MappingResult, SemanticMapper
from caas_framework.bmad.traceability import ImplementationStatus, TraceabilityMatrix
from caas_framework.models.specifications import FeatureSpec
from caas_framework.plugins.llm.base import LLMPlugin

logger = get_logger()


@dataclass
class CompletenessReport:
    """Completeness validation report"""

    # Overall metrics
    total_features: int = 0
    fully_implemented: int = 0
    partially_implemented: int = 0
    not_implemented: int = 0
    implementation_rate: float = 0.0

    # Feature-level details
    feature_implementations: List[FeatureImplementation] = field(default_factory=list)
    unimplemented_features: List[FeatureSpec] = field(default_factory=list)

    # Recommendations
    missing_critical_features: List[str] = field(default_factory=list)
    quality_issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    # Summary
    is_complete: bool = False
    completeness_score: float = 0.0  # 0-100


class CompletenessValidator:
    """
    Completeness Validator

    Validates that generated code implements all required features.

    Process:
    1. Analyze generated code structure (via CodeAnalyzer)
    2. Map features to code (via SemanticMapper)
    3. Identify gaps and missing implementations
    4. Generate completeness report
    5. Update traceability matrix with actual implementation status
    """

    def __init__(self, llm_plugin: LLMPlugin):
        """
        Initialize completeness validator

        Args:
            llm_plugin: LLM plugin for semantic analysis
        """
        self.llm = llm_plugin
        self.code_analyzer = CodeAnalyzer()
        self.semantic_mapper = SemanticMapper(llm_plugin)
        self.logger = get_logger()

    async def validate(
        self,
        features: List[FeatureSpec],
        generated_code: Dict[str, str],
        traceability: Optional[TraceabilityMatrix] = None,
    ) -> CompletenessReport:
        """
        Validate completeness of generated code

        Args:
            features: List of features that should be implemented
            generated_code: Dictionary of file_path → content
            traceability: Optional traceability matrix to update

        Returns:
            CompletenessReport with validation results
        """
        self.logger.info(f"Validating completeness for {len(features)} features")

        # Step 1: Analyze code structure
        self.logger.info("Step 1/4: Analyzing code structure...")
        code_analyses = self.code_analyzer.analyze_code_base(generated_code)

        code_summary = self.code_analyzer.get_summary(code_analyses)
        self.logger.info(
            f"Code analysis: {code_summary['total_files']} files, "
            f"{code_summary['total_functions']} functions, "
            f"{code_summary['total_classes']} classes"
        )

        # Step 2: Semantic mapping
        self.logger.info("Step 2/4: Performing semantic mapping...")
        mapping_result = await self.semantic_mapper.map_features_to_code(features, code_analyses)

        self.logger.info(
            f"Semantic mapping: {len(mapping_result.feature_implementations)} "
            f"features mapped ({mapping_result.implementation_rate:.1f}%)"
        )

        # Step 3: Update traceability matrix
        if traceability:
            self.logger.info("Step 3/4: Updating traceability matrix...")
            self._update_traceability(mapping_result, traceability)
        else:
            self.logger.info("Step 3/4: Skipping traceability update (not provided)")

        # Step 4: Generate completeness report
        self.logger.info("Step 4/4: Generating completeness report...")
        report = self._generate_report(features, mapping_result)

        self.logger.info(
            f"Validation complete: {report.implementation_rate:.1f}% implemented, "
            f"completeness score: {report.completeness_score:.1f}"
        )

        return report

    def _update_traceability(
        self, mapping_result: MappingResult, traceability: TraceabilityMatrix
    ) -> None:
        """
        Update traceability matrix with actual implementation status

        Args:
            mapping_result: Semantic mapping result
            traceability: Traceability matrix to update
        """
        for impl in mapping_result.feature_implementations:
            feature_trace = traceability.get_feature_trace(impl.feature_id)

            if feature_trace:
                # Update status based on implementation
                if impl.is_fully_implemented:
                    feature_trace.status = ImplementationStatus.IMPLEMENTED
                    feature_trace.coverage_percentage = 100.0
                elif impl.is_partially_implemented:
                    feature_trace.status = ImplementationStatus.IN_PROGRESS
                    feature_trace.coverage_percentage = impl.implementation_percentage
                else:
                    feature_trace.status = ImplementationStatus.NOT_STARTED
                    feature_trace.coverage_percentage = 0.0

                # Update implementing files and functions
                feature_trace.implementing_files = impl.implementing_files
                feature_trace.implementing_functions = impl.implementing_functions

                # Update notes with evidence
                if impl.evidence:
                    feature_trace.notes = "\n".join(impl.evidence)

        self.logger.debug(f"Updated {len(mapping_result.feature_implementations)} feature traces")

    def _generate_report(
        self, features: List[FeatureSpec], mapping_result: MappingResult
    ) -> CompletenessReport:
        """
        Generate completeness report

        Args:
            features: All features
            mapping_result: Semantic mapping result

        Returns:
            CompletenessReport
        """
        report = CompletenessReport()

        # Calculate metrics
        report.total_features = len(features)
        report.feature_implementations = mapping_result.feature_implementations

        # Count implementation status
        for impl in mapping_result.feature_implementations:
            if impl.is_fully_implemented:
                report.fully_implemented += 1
            elif impl.is_partially_implemented:
                report.partially_implemented += 1

        report.not_implemented = (
            report.total_features - report.fully_implemented - report.partially_implemented
        )

        # Calculate implementation rate
        report.implementation_rate = (
            (report.fully_implemented + report.partially_implemented * 0.5)
            / report.total_features
            * 100
            if report.total_features > 0
            else 0
        )

        # Find unimplemented features
        implemented_ids = {impl.feature_id for impl in mapping_result.feature_implementations}
        report.unimplemented_features = [f for f in features if f.id not in implemented_ids]

        # Identify critical missing features
        for feature in report.unimplemented_features:
            if feature.priority.lower() in ("critical", "high"):
                report.missing_critical_features.append(
                    f"{feature.name} ({feature.id}) - Priority: {feature.priority}"
                )

        # Generate recommendations
        report.recommendations = self._generate_recommendations(report)

        # Calculate completeness score
        report.completeness_score = self._calculate_completeness_score(report)

        # Determine if complete
        report.is_complete = (
            report.completeness_score >= 90.0 and len(report.missing_critical_features) == 0
        )

        return report

    def _generate_recommendations(self, report: CompletenessReport) -> List[str]:
        """Generate recommendations based on report"""
        recommendations = []

        # Missing features
        if report.not_implemented > 0:
            recommendations.append(f"누락된 {report.not_implemented}개 기능을 구현하세요")

        # Partially implemented features
        if report.partially_implemented > 0:
            recommendations.append(
                f"부분 구현된 {report.partially_implemented}개 기능을 완료하세요"
            )

        # Critical features
        if report.missing_critical_features:
            recommendations.append(
                f"긴급: {len(report.missing_critical_features)}개의 핵심 기능이 누락되었습니다"
            )

        # Implementation rate
        if report.implementation_rate < 50:
            recommendations.append(
                "구현률이 매우 낮습니다. 더 구체적인 지시사항으로 코드를 재생성하는 것을 고려하세요."
            )
        elif report.implementation_rate < 80:
            recommendations.append("구현률이 중간 수준입니다. 검토하고 누락된 부분을 채우세요.")

        return recommendations

    def _calculate_completeness_score(self, report: CompletenessReport) -> float:
        """
        Calculate overall completeness score (0-100)

        Factors:
        - Full implementation: 100% weight
        - Partial implementation: 50% weight
        - Missing critical features: -20 points each (up to -100)
        """
        if report.total_features == 0:
            return 0.0

        # Base score from implementation rate
        base_score = report.implementation_rate

        # Penalty for missing critical features
        critical_penalty = len(report.missing_critical_features) * 20
        critical_penalty = min(critical_penalty, 100)  # Cap at 100

        # Final score
        score = max(0, base_score - critical_penalty)

        return score

    def generate_text_report(self, report: CompletenessReport) -> str:
        """
        Generate human-readable text report

        Args:
            report: Completeness report

        Returns:
            Formatted text report
        """
        lines = [
            "=" * 80,
            "완전성 검증 보고서 (COMPLETENESS VALIDATION REPORT)",
            "=" * 80,
            "",
            "전체 지표 (OVERALL METRICS)",
            "-" * 80,
            f"전체 기능:               {report.total_features}",
            (
                f"완전 구현:               {report.fully_implemented} ({report.fully_implemented/report.total_features*100:.1f}%)"
                if report.total_features > 0
                else "완전 구현:               0"
            ),
            (
                f"부분 구현:               {report.partially_implemented} ({report.partially_implemented/report.total_features*100:.1f}%)"
                if report.total_features > 0
                else "부분 구현:               0"
            ),
            (
                f"미구현:                  {report.not_implemented} ({report.not_implemented/report.total_features*100:.1f}%)"
                if report.total_features > 0
                else "미구현:                  0"
            ),
            f"구현률:                  {report.implementation_rate:.1f}%",
            f"완전성 점수:             {report.completeness_score:.1f}/100",
            f"상태:                    {'✅ 완료' if report.is_complete else '⚠️ 미완료'}",
            "",
        ]

        # Fully implemented features
        if report.fully_implemented > 0:
            lines.extend(
                [
                    "완전 구현된 기능 (FULLY IMPLEMENTED FEATURES)",
                    "-" * 80,
                ]
            )
            fully_impl = [
                impl for impl in report.feature_implementations if impl.is_fully_implemented
            ]
            for impl in fully_impl[:10]:  # Limit to 10
                lines.append(
                    f"  ✅ {impl.feature_name} ({impl.feature_id}) - "
                    f"신뢰도: {impl.confidence_score:.2f}"
                )
                if impl.implementing_files:
                    lines.append(f"     파일: {', '.join(impl.implementing_files[:3])}")
            if len(fully_impl) > 10:
                lines.append(f"  ... 외 {len(fully_impl) - 10}개")
            lines.append("")

        # Partially implemented features
        if report.partially_implemented > 0:
            lines.extend(
                [
                    "부분 구현된 기능 (PARTIALLY IMPLEMENTED FEATURES)",
                    "-" * 80,
                ]
            )
            partial_impl = [
                impl for impl in report.feature_implementations if impl.is_partially_implemented
            ]
            for impl in partial_impl[:5]:
                lines.append(
                    f"  ⚠️  {impl.feature_name} ({impl.feature_id}) - "
                    f"{impl.implementation_percentage:.0f}% 완료"
                )
            if len(partial_impl) > 5:
                lines.append(f"  ... 외 {len(partial_impl) - 5}개")
            lines.append("")

        # Missing features
        if report.unimplemented_features:
            lines.extend(
                [
                    "미구현 기능 (UNIMPLEMENTED FEATURES)",
                    "-" * 80,
                ]
            )
            for feature in report.unimplemented_features[:10]:
                priority_marker = "🔴" if feature.priority.lower() in ("critical", "high") else "⚪"
                lines.append(
                    f"  {priority_marker} {feature.name} ({feature.id}) - "
                    f"우선순위: {feature.priority}"
                )
            if len(report.unimplemented_features) > 10:
                lines.append(f"  ... 외 {len(report.unimplemented_features) - 10}개")
            lines.append("")

        # Missing critical features
        if report.missing_critical_features:
            lines.extend(
                [
                    "⚠️  누락된 핵심 기능 (MISSING CRITICAL FEATURES)",
                    "-" * 80,
                ]
            )
            for feature_desc in report.missing_critical_features:
                lines.append(f"  🔴 {feature_desc}")
            lines.append("")

        # Recommendations
        if report.recommendations:
            lines.extend(
                [
                    "권장사항 (RECOMMENDATIONS)",
                    "-" * 80,
                ]
            )
            for i, rec in enumerate(report.recommendations, 1):
                lines.append(f"  {i}. {rec}")
            lines.append("")

        lines.append("=" * 80)

        return "\n".join(lines)
