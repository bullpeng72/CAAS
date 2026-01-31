"""
Tests for Quality Gate System

Tests the quality gate system for BMAD phase exit criteria.
"""

import pytest
from caas_framework.quality.quality_gates import (
    QualityGateSystem,
    QualityGate,
    QualityMetric,
    GateEvaluation,
    GateStatus,
    MetricType,
    create_quality_gate_system
)
from caas_framework.agents.base import AgentPhase


class TestQualityMetric:
    """Test Quality Metric"""

    def test_quality_metric_creation(self):
        """Test creating a quality metric"""
        metric = QualityMetric(
            name="code_quality",
            metric_type=MetricType.SCORE,
            threshold=7.0,
            actual_value=8.5,
            weight=1.5,
            critical=True
        )

        assert metric.name == "code_quality"
        assert metric.threshold == 7.0
        assert metric.actual_value == 8.5
        assert metric.passed is True
        assert metric.critical is True

    def test_metric_passed_property(self):
        """Test metric passed property"""
        # Passing metric
        metric1 = QualityMetric(
            name="test", metric_type=MetricType.SCORE,
            threshold=7.0, actual_value=8.0
        )
        assert metric1.passed is True

        # Failing metric
        metric2 = QualityMetric(
            name="test", metric_type=MetricType.SCORE,
            threshold=7.0, actual_value=6.0
        )
        assert metric2.passed is False

        # Missing value
        metric3 = QualityMetric(
            name="test", metric_type=MetricType.SCORE,
            threshold=7.0, actual_value=None
        )
        assert metric3.passed is False

    def test_metric_margin(self):
        """Test metric margin calculation"""
        metric = QualityMetric(
            name="test", metric_type=MetricType.SCORE,
            threshold=7.0, actual_value=8.5
        )
        assert metric.margin == 1.5  # 8.5 - 7.0


class TestGateEvaluation:
    """Test Gate Evaluation"""

    def test_gate_evaluation_creation(self):
        """Test creating gate evaluation"""
        metrics = [
            QualityMetric("m1", MetricType.SCORE, 7.0, 8.0, critical=True),
            QualityMetric("m2", MetricType.SCORE, 7.0, 9.0)
        ]

        evaluation = GateEvaluation(
            phase=AgentPhase.DESIGN,
            status=GateStatus.PASSED,
            metrics=metrics,
            passed_metrics=["m1", "m2"],
            failed_metrics=[],
            overall_score=8.5
        )

        assert evaluation.phase == AgentPhase.DESIGN
        assert evaluation.status == GateStatus.PASSED
        assert evaluation.can_proceed is True
        assert evaluation.pass_rate == 100.0

    def test_can_proceed_with_critical_failure(self):
        """Test can_proceed blocks on critical failure"""
        metrics = [
            QualityMetric("m1", MetricType.SCORE, 7.0, 6.0, critical=True),  # FAIL
            QualityMetric("m2", MetricType.SCORE, 7.0, 9.0, critical=False)
        ]

        evaluation = GateEvaluation(
            phase=AgentPhase.DESIGN,
            status=GateStatus.FAILED,
            metrics=metrics,
            passed_metrics=["m2"],
            failed_metrics=["m1"]
        )

        # Should block because critical metric failed
        assert evaluation.can_proceed is False

    def test_can_proceed_with_non_critical_failure(self):
        """Test can_proceed allows non-critical failures"""
        metrics = [
            QualityMetric("m1", MetricType.SCORE, 7.0, 8.0, critical=True),
            QualityMetric("m2", MetricType.SCORE, 7.0, 6.0, critical=False)  # FAIL
        ]

        evaluation = GateEvaluation(
            phase=AgentPhase.DESIGN,
            status=GateStatus.WARNING,
            metrics=metrics,
            passed_metrics=["m1"],
            failed_metrics=["m2"]
        )

        # Should allow proceed (only non-critical failed)
        assert evaluation.can_proceed is True

    def test_pass_rate_calculation(self):
        """Test pass rate calculation"""
        metrics = [
            QualityMetric("m1", MetricType.SCORE, 7.0, 8.0),  # PASS
            QualityMetric("m2", MetricType.SCORE, 7.0, 9.0),  # PASS
            QualityMetric("m3", MetricType.SCORE, 7.0, 6.0),  # FAIL
            QualityMetric("m4", MetricType.SCORE, 7.0, 5.0),  # FAIL
        ]

        evaluation = GateEvaluation(
            phase=AgentPhase.DESIGN,
            status=GateStatus.WARNING,
            metrics=metrics,
            passed_metrics=["m1", "m2"],
            failed_metrics=["m3", "m4"]
        )

        # 2 passed out of 4 = 50%
        assert evaluation.pass_rate == 50.0


class TestQualityGate:
    """Test Quality Gate"""

    def test_quality_gate_creation(self):
        """Test creating a quality gate"""
        metrics = [
            QualityMetric("m1", MetricType.SCORE, 7.0, weight=1.5, critical=True),
            QualityMetric("m2", MetricType.SCORE, 7.0, weight=1.0)
        ]

        gate = QualityGate(
            phase=AgentPhase.DESIGN,
            metrics=metrics,
            min_pass_rate=80.0
        )

        assert gate.phase == AgentPhase.DESIGN
        assert len(gate.metrics) == 2
        assert gate.min_pass_rate == 80.0

    def test_gate_evaluation_all_pass(self):
        """Test gate evaluation when all metrics pass"""
        metrics = [
            QualityMetric("agent_role_clarity", MetricType.SCORE, 7.0),
            QualityMetric("task_completeness", MetricType.SCORE, 7.0)
        ]

        gate = QualityGate(AgentPhase.DESIGN, metrics)

        # Provide output with metric values
        context = {
            "agent_role_clarity": 8.5,
            "task_completeness": 9.0
        }

        evaluation = gate.evaluate({}, context)

        assert evaluation.status == GateStatus.PASSED
        assert evaluation.can_proceed is True
        assert len(evaluation.passed_metrics) == 2
        assert len(evaluation.failed_metrics) == 0

    def test_gate_evaluation_critical_fail(self):
        """Test gate evaluation when critical metric fails"""
        metrics = [
            QualityMetric("critical_metric", MetricType.SCORE, 7.0, critical=True),
            QualityMetric("normal_metric", MetricType.SCORE, 7.0, critical=False)
        ]

        gate = QualityGate(AgentPhase.DESIGN, metrics)

        context = {
            "critical_metric": 5.0,  # FAIL (critical)
            "normal_metric": 8.0      # PASS
        }

        evaluation = gate.evaluate({}, context)

        assert evaluation.status == GateStatus.FAILED
        assert evaluation.can_proceed is False  # Blocked by critical failure
        assert "critical_metric" in evaluation.failed_metrics

    def test_gate_evaluation_low_pass_rate(self):
        """Test gate evaluation with low pass rate"""
        metrics = [
            QualityMetric("m1", MetricType.SCORE, 7.0),
            QualityMetric("m2", MetricType.SCORE, 7.0),
            QualityMetric("m3", MetricType.SCORE, 7.0),
            QualityMetric("m4", MetricType.SCORE, 7.0),
        ]

        gate = QualityGate(AgentPhase.DESIGN, metrics, min_pass_rate=75.0)

        context = {
            "m1": 8.0,  # PASS
            "m2": 6.0,  # FAIL
            "m3": 5.0,  # FAIL
            "m4": 4.0,  # FAIL
        }

        evaluation = gate.evaluate({}, context)

        # Only 1/4 = 25% pass rate (< 75% minimum)
        assert evaluation.status == GateStatus.FAILED
        assert evaluation.pass_rate == 25.0


class TestQualityGateSystem:
    """Test Quality Gate System"""

    def test_quality_gate_system_creation(self):
        """Test creating quality gate system"""
        system = QualityGateSystem(enable_gates=True, strict_mode=False)

        assert system.enable_gates is True
        assert system.strict_mode is False
        assert len(system.gates) == 5  # One for each BMAD phase

    def test_default_gates_created(self):
        """Test that default gates are created for all phases"""
        system = QualityGateSystem()

        # Check gates for all phases
        assert AgentPhase.DISCOVERY in system.gates
        assert AgentPhase.ARCHITECTURE in system.gates
        assert AgentPhase.DESIGN in system.gates
        assert AgentPhase.DELIVERY in system.gates
        assert AgentPhase.QUALITY_ASSURANCE in system.gates

    def test_design_phase_gate_metrics(self):
        """Test Design phase gate has appropriate metrics"""
        system = QualityGateSystem()
        design_gate = system.gates[AgentPhase.DESIGN]

        metric_names = [m.name for m in design_gate.metrics]

        # Design phase should check these metrics
        assert "agent_role_clarity" in metric_names
        assert "task_completeness" in metric_names
        assert "dependency_correctness" in metric_names

    def test_evaluate_gate_disabled(self):
        """Test gate evaluation when gates are disabled"""
        system = QualityGateSystem(enable_gates=False)

        evaluation = system.evaluate_gate(
            phase=AgentPhase.DESIGN,
            output={},
            context={}
        )

        # Should skip when disabled
        assert evaluation.status == GateStatus.SKIPPED
        assert evaluation.can_proceed is True

    def test_evaluate_gate_with_good_metrics(self):
        """Test gate evaluation with good metrics"""
        system = QualityGateSystem(enable_gates=True)

        context = {
            "agent_role_clarity": 8.5,
            "task_completeness": 9.0,
            "dependency_correctness": 8.0,
            "tool_appropriateness": 7.5
        }

        evaluation = system.evaluate_gate(
            phase=AgentPhase.DESIGN,
            output={},
            context=context
        )

        assert evaluation.status in [GateStatus.PASSED, GateStatus.WARNING]
        assert evaluation.can_proceed is True

    def test_evaluate_gate_with_poor_metrics(self):
        """Test gate evaluation with poor metrics"""
        system = QualityGateSystem(enable_gates=True)

        context = {
            "agent_role_clarity": 5.0,      # FAIL (critical)
            "task_completeness": 6.0,        # FAIL (critical)
            "dependency_correctness": 4.0,   # FAIL (critical)
            "tool_appropriateness": 5.0      # FAIL
        }

        evaluation = system.evaluate_gate(
            phase=AgentPhase.DESIGN,
            output={},
            context=context
        )

        assert evaluation.status == GateStatus.FAILED
        assert evaluation.can_proceed is False  # Critical failures

    def test_strict_mode_blocks_warnings(self):
        """Test strict mode blocks even warnings"""
        system = QualityGateSystem(enable_gates=True, strict_mode=True)

        # Metrics that would normally pass but with warnings
        context = {
            "agent_role_clarity": 8.0,       # PASS
            "task_completeness": 8.5,        # PASS
            "dependency_correctness": 8.5,   # PASS
            "tool_appropriateness": 6.0      # FAIL (non-critical)
        }

        evaluation = system.evaluate_gate(
            phase=AgentPhase.DESIGN,
            output={},
            context=context
        )

        # In strict mode, can_proceed checks if status is exactly PASSED
        can_proceed = system.can_proceed_to_next_phase(evaluation)

        # Should depend on whether evaluation status is PASSED or WARNING
        # With one failure, status would be WARNING or FAILED
        if evaluation.status != GateStatus.PASSED:
            assert can_proceed is False

    def test_can_proceed_to_next_phase(self):
        """Test can_proceed_to_next_phase logic"""
        system = QualityGateSystem(enable_gates=True, strict_mode=False)

        # PASSED evaluation
        eval_passed = GateEvaluation(
            phase=AgentPhase.DESIGN,
            status=GateStatus.PASSED,
            metrics=[]
        )
        assert system.can_proceed_to_next_phase(eval_passed) is True

        # WARNING evaluation (no critical failures)
        eval_warning = GateEvaluation(
            phase=AgentPhase.DESIGN,
            status=GateStatus.WARNING,
            metrics=[]
        )
        assert system.can_proceed_to_next_phase(eval_warning) is True

        # FAILED evaluation with critical failure
        eval_failed = GateEvaluation(
            phase=AgentPhase.DESIGN,
            status=GateStatus.FAILED,
            metrics=[
                QualityMetric("m1", MetricType.SCORE, 7.0, 5.0, critical=True)
            ]
        )
        assert system.can_proceed_to_next_phase(eval_failed) is False

    def test_convenience_function(self):
        """Test create_quality_gate_system convenience function"""
        system = create_quality_gate_system(enable_gates=True, strict_mode=True)

        assert isinstance(system, QualityGateSystem)
        assert system.enable_gates is True
        assert system.strict_mode is True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
