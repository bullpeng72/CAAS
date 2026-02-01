"""
Quality Gate System

Implements quality gates with exit criteria for each BMAD phase.
Ensures that each phase meets minimum quality standards before proceeding.
"""

import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

from caas_framework.agents.base import AgentPhase


class GateStatus(str, Enum):
    """Quality gate status"""
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"


class MetricType(str, Enum):
    """Types of quality metrics"""
    SCORE = "score"              # Numeric score (0-10)
    PERCENTAGE = "percentage"    # Percentage (0-100)
    COUNT = "count"              # Integer count
    BOOLEAN = "boolean"          # True/False
    COVERAGE = "coverage"        # Coverage percentage (0-100)


@dataclass
class QualityMetric:
    """A single quality metric with threshold"""
    name: str
    metric_type: MetricType
    threshold: float
    actual_value: Optional[float] = None
    weight: float = 1.0
    critical: bool = False  # If True, failure blocks phase transition
    description: str = ""

    @property
    def passed(self) -> bool:
        """Check if metric passes threshold"""
        if self.actual_value is None:
            return False
        return self.actual_value >= self.threshold

    @property
    def margin(self) -> float:
        """Margin from threshold (positive = passed, negative = failed)"""
        if self.actual_value is None:
            return -self.threshold
        return self.actual_value - self.threshold


@dataclass
class GateEvaluation:
    """Result of quality gate evaluation"""
    phase: AgentPhase
    status: GateStatus
    metrics: List[QualityMetric]
    passed_metrics: List[str] = field(default_factory=list)
    failed_metrics: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    overall_score: float = 0.0

    @property
    def can_proceed(self) -> bool:
        """Check if phase can proceed (all critical metrics passed)"""
        if self.status == GateStatus.SKIPPED:
            return True

        critical_failures = [
            m for m in self.metrics
            if m.critical and not m.passed
        ]
        return len(critical_failures) == 0

    @property
    def pass_rate(self) -> float:
        """Percentage of metrics that passed"""
        if not self.metrics:
            return 100.0
        return (len(self.passed_metrics) / len(self.metrics)) * 100.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "phase": self.phase.value if isinstance(self.phase, AgentPhase) else self.phase,
            "status": self.status.value,
            "can_proceed": self.can_proceed,
            "pass_rate": self.pass_rate,
            "overall_score": self.overall_score,
            "passed_metrics": self.passed_metrics,
            "failed_metrics": self.failed_metrics,
            "warnings": self.warnings,
            "recommendations": self.recommendations,
            "metrics": [
                {
                    "name": m.name,
                    "type": m.metric_type.value,
                    "threshold": m.threshold,
                    "actual": m.actual_value,
                    "passed": m.passed,
                    "critical": m.critical
                }
                for m in self.metrics
            ]
        }


class QualityGate:
    """
    Quality Gate for a specific BMAD phase

    Defines exit criteria and evaluates whether phase output meets standards.
    """

    def __init__(
        self,
        phase: AgentPhase,
        metrics: List[QualityMetric],
        min_pass_rate: float = 80.0,  # Minimum % of metrics that must pass
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize quality gate.

        Args:
            phase: BMAD phase this gate applies to
            metrics: List of quality metrics with thresholds
            min_pass_rate: Minimum percentage of metrics that must pass
            logger: Optional logger
        """
        self.phase = phase
        self.metrics = metrics
        self.min_pass_rate = min_pass_rate
        self.logger = logger or logging.getLogger(__name__)

    def evaluate(
        self,
        output: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> GateEvaluation:
        """
        Evaluate phase output against quality gate.

        Args:
            output: Phase output to evaluate
            context: Optional context (validation results, scores, etc.)

        Returns:
            GateEvaluation with results
        """
        self.logger.info(f"🚪 Evaluating quality gate for {self.phase.name}")

        # Collect metric values from output and context
        evaluated_metrics = []
        passed = []
        failed = []
        warnings = []
        recommendations = []

        for metric in self.metrics:
            # Get actual value from context or output
            actual_value = self._get_metric_value(metric, output, context)

            # Create evaluated metric
            evaluated_metric = QualityMetric(
                name=metric.name,
                metric_type=metric.metric_type,
                threshold=metric.threshold,
                actual_value=actual_value,
                weight=metric.weight,
                critical=metric.critical,
                description=metric.description
            )

            evaluated_metrics.append(evaluated_metric)

            # Check pass/fail
            if evaluated_metric.passed:
                passed.append(metric.name)
                self.logger.debug(f"  ✅ {metric.name}: {actual_value} >= {metric.threshold}")
            else:
                failed.append(metric.name)
                level = "CRITICAL" if metric.critical else "WARNING"
                self.logger.warning(
                    f"  ❌ [{level}] {metric.name}: {actual_value} < {metric.threshold}"
                )

                if metric.critical:
                    recommendations.append(
                        f"CRITICAL: {metric.name} must be >= {metric.threshold} "
                        f"(current: {actual_value})"
                    )
                else:
                    warnings.append(
                        f"{metric.name} below threshold ({actual_value} < {metric.threshold})"
                    )

        # Calculate overall score (weighted average of metrics)
        overall_score = self._calculate_overall_score(evaluated_metrics)

        # Calculate pass rate
        pass_rate = (len(passed) / len(self.metrics)) * 100.0 if self.metrics else 100.0

        # Determine status
        if pass_rate >= self.min_pass_rate:
            # Check critical metrics
            critical_failures = [m for m in evaluated_metrics if m.critical and not m.passed]
            if critical_failures:
                status = GateStatus.FAILED
            else:
                status = GateStatus.PASSED if pass_rate >= 95.0 else GateStatus.WARNING
        else:
            status = GateStatus.FAILED

        evaluation = GateEvaluation(
            phase=self.phase,
            status=status,
            metrics=evaluated_metrics,
            passed_metrics=passed,
            failed_metrics=failed,
            warnings=warnings,
            recommendations=recommendations,
            overall_score=overall_score
        )

        # Log result
        if evaluation.can_proceed:
            self.logger.info(
                f"✅ Quality gate PASSED for {self.phase.name} "
                f"({pass_rate:.1f}% pass rate, score: {overall_score:.1f}/10.0)"
            )
        else:
            self.logger.error(
                f"❌ Quality gate FAILED for {self.phase.name} "
                f"({len(failed)} critical failures)"
            )

        return evaluation

    def _get_metric_value(
        self,
        metric: QualityMetric,
        output: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> Optional[float]:
        """Extract metric value from output or context"""

        # Common metric value sources
        sources = []

        if context:
            sources.append(context)
        sources.append(output)

        # Try to find metric value in sources
        for source in sources:
            # Try direct key match
            if metric.name in source:
                value = source[metric.name]
                return self._convert_to_float(value)

            # Try nested paths (e.g., "validation.score")
            if "." in metric.name:
                value = self._get_nested_value(source, metric.name)
                if value is not None:
                    return self._convert_to_float(value)

        # Metric value not found
        self.logger.warning(f"Metric '{metric.name}' not found in output or context")
        return None

    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Any:
        """Get nested value from dict using dot notation"""
        keys = path.split(".")
        current = data

        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None

        return current

    def _convert_to_float(self, value: Any) -> float:
        """Convert value to float"""
        if isinstance(value, (int, float)):
            return float(value)
        elif isinstance(value, bool):
            return 1.0 if value else 0.0
        elif isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                return 0.0
        else:
            return 0.0

    def _calculate_overall_score(self, metrics: List[QualityMetric]) -> float:
        """Calculate weighted overall score"""
        if not metrics:
            return 0.0

        total_weight = sum(m.weight for m in metrics)
        if total_weight == 0:
            return 0.0

        weighted_sum = sum(
            (m.actual_value or 0.0) * m.weight
            for m in metrics
        )

        return weighted_sum / total_weight


class QualityGateSystem:
    """
    Quality Gate System for BMAD workflow

    Manages quality gates for all phases and enforces exit criteria.
    """

    def __init__(
        self,
        enable_gates: bool = True,
        strict_mode: bool = False,  # If True, block on any failure
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize quality gate system.

        Args:
            enable_gates: Enable quality gates (False = all gates pass)
            strict_mode: Strict mode blocks on any failure
            logger: Optional logger
        """
        self.enable_gates = enable_gates
        self.strict_mode = strict_mode
        self.logger = logger or logging.getLogger(__name__)

        # Define gates for each phase
        self.gates: Dict[AgentPhase, QualityGate] = self._create_default_gates()

    def _create_default_gates(self) -> Dict[AgentPhase, QualityGate]:
        """Create default quality gates for each phase"""

        gates = {}

        # DISCOVERY Phase Gate
        gates[AgentPhase.DISCOVERY] = QualityGate(
            phase=AgentPhase.DISCOVERY,
            metrics=[
                QualityMetric(
                    name="requirement_clarity",
                    metric_type=MetricType.SCORE,
                    threshold=7.0,
                    weight=1.5,
                    critical=True,
                    description="Requirements must be clear and unambiguous"
                ),
                QualityMetric(
                    name="feature_completeness",
                    metric_type=MetricType.SCORE,
                    threshold=7.0,
                    weight=1.5,
                    critical=True,
                    description="All necessary features identified"
                ),
                QualityMetric(
                    name="golden_data_alignment",
                    metric_type=MetricType.PERCENTAGE,
                    threshold=80.0,
                    weight=2.0,
                    critical=True,
                    description="Alignment with golden data requirements"
                ),
            ],
            min_pass_rate=85.0
        )

        # ARCHITECTURE Phase Gate
        gates[AgentPhase.ARCHITECTURE] = QualityGate(
            phase=AgentPhase.ARCHITECTURE,
            metrics=[
                QualityMetric(
                    name="component_clarity",
                    metric_type=MetricType.SCORE,
                    threshold=7.0,
                    weight=1.5,
                    critical=True,
                    description="Component responsibilities clearly defined"
                ),
                QualityMetric(
                    name="architectural_coherence",
                    metric_type=MetricType.SCORE,
                    threshold=7.0,
                    weight=1.5,
                    critical=True,
                    description="Components interact logically"
                ),
                QualityMetric(
                    name="scalability_score",
                    metric_type=MetricType.SCORE,
                    threshold=6.0,
                    weight=1.0,
                    critical=False,
                    description="Architecture supports scaling"
                ),
            ],
            min_pass_rate=80.0
        )

        # DESIGN Phase Gate
        gates[AgentPhase.DESIGN] = QualityGate(
            phase=AgentPhase.DESIGN,
            metrics=[
                QualityMetric(
                    name="agent_role_clarity",
                    metric_type=MetricType.SCORE,
                    threshold=7.0,
                    weight=2.0,
                    critical=True,
                    description="Agent roles are clear and non-overlapping"
                ),
                QualityMetric(
                    name="task_completeness",
                    metric_type=MetricType.SCORE,
                    threshold=7.0,
                    weight=2.0,
                    critical=True,
                    description="All necessary tasks defined"
                ),
                QualityMetric(
                    name="dependency_correctness",
                    metric_type=MetricType.SCORE,
                    threshold=8.0,
                    weight=1.5,
                    critical=True,
                    description="Task dependencies are logical and acyclic"
                ),
                QualityMetric(
                    name="tool_appropriateness",
                    metric_type=MetricType.SCORE,
                    threshold=7.0,
                    weight=1.0,
                    critical=False,
                    description="Tools appropriate for agent roles"
                ),
            ],
            min_pass_rate=85.0
        )

        # DELIVERY Phase Gate
        gates[AgentPhase.DELIVERY] = QualityGate(
            phase=AgentPhase.DELIVERY,
            metrics=[
                QualityMetric(
                    name="code_quality",
                    metric_type=MetricType.SCORE,
                    threshold=7.0,
                    weight=2.0,
                    critical=True,
                    description="Code is readable and well-structured"
                ),
                QualityMetric(
                    name="implementation_completeness",
                    metric_type=MetricType.SCORE,
                    threshold=8.0,
                    weight=2.0,
                    critical=True,
                    description="All required features implemented"
                ),
                QualityMetric(
                    name="security_score",
                    metric_type=MetricType.SCORE,
                    threshold=8.0,
                    weight=1.5,
                    critical=True,
                    description="No critical security issues"
                ),
                QualityMetric(
                    name="test_coverage",
                    metric_type=MetricType.PERCENTAGE,
                    threshold=70.0,
                    weight=1.0,
                    critical=False,
                    description="Adequate test coverage"
                ),
            ],
            min_pass_rate=80.0
        )

        # QUALITY_ASSURANCE Phase Gate
        gates[AgentPhase.QUALITY_ASSURANCE] = QualityGate(
            phase=AgentPhase.QUALITY_ASSURANCE,
            metrics=[
                QualityMetric(
                    name="test_completeness",
                    metric_type=MetricType.SCORE,
                    threshold=7.0,
                    weight=2.0,
                    critical=True,
                    description="All critical aspects tested"
                ),
                QualityMetric(
                    name="test_correctness",
                    metric_type=MetricType.SCORE,
                    threshold=8.0,
                    weight=1.5,
                    critical=True,
                    description="Test assertions are correct"
                ),
                QualityMetric(
                    name="coverage_percentage",
                    metric_type=MetricType.PERCENTAGE,
                    threshold=75.0,
                    weight=1.0,
                    critical=False,
                    description="Test coverage percentage"
                ),
            ],
            min_pass_rate=85.0
        )

        return gates

    def evaluate_gate(
        self,
        phase: AgentPhase,
        output: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> GateEvaluation:
        """
        Evaluate quality gate for a phase.

        Args:
            phase: Phase to evaluate
            output: Phase output
            context: Optional context with additional metrics

        Returns:
            GateEvaluation result
        """
        if not self.enable_gates:
            self.logger.info(f"Quality gates disabled, skipping {phase.name} gate")
            return GateEvaluation(
                phase=phase,
                status=GateStatus.SKIPPED,
                metrics=[],
                overall_score=10.0
            )

        gate = self.gates.get(phase)
        if not gate:
            self.logger.warning(f"No quality gate defined for {phase.name}")
            return GateEvaluation(
                phase=phase,
                status=GateStatus.SKIPPED,
                metrics=[],
                overall_score=10.0
            )

        # Evaluate gate
        evaluation = gate.evaluate(output, context)

        # Strict mode: any failure blocks
        if self.strict_mode and evaluation.status == GateStatus.FAILED:
            self.logger.error(
                f"🚫 Strict mode: blocking {phase.name} due to gate failure"
            )

        return evaluation

    def can_proceed_to_next_phase(self, evaluation: GateEvaluation) -> bool:
        """Check if workflow can proceed to next phase"""
        if not self.enable_gates:
            return True

        if self.strict_mode:
            return evaluation.status == GateStatus.PASSED

        # Normal mode: allow proceed if critical metrics pass
        return evaluation.can_proceed


# ==================== Convenience Functions ====================

def create_quality_gate_system(
    enable_gates: bool = True,
    strict_mode: bool = False
) -> QualityGateSystem:
    """Create quality gate system with default gates"""
    return QualityGateSystem(
        enable_gates=enable_gates,
        strict_mode=strict_mode
    )
