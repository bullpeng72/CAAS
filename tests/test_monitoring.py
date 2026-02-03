"""
Tests for Enhanced Metrics and Monitoring

Tests metrics collector, cost tracker, quality tracker, alert system, and exporters.
"""

from datetime import datetime, timedelta

import pytest

from caas_framework.monitoring.alert_system import (
    AlertRule,
    AlertSeverity,
    AlertSystem,
    create_cost_alert_rule,
    create_quality_alert_rule,
)
from caas_framework.monitoring.cost_tracker import CostTracker
from caas_framework.monitoring.exporters import (
    DashboardDataExporter,
    JSONExporter,
    PrometheusExporter,
)
from caas_framework.monitoring.metrics_collector import (
    EnhancedMetricsCollector,
    Metric,
    MetricType,
)
from caas_framework.monitoring.quality_tracker import (
    QualityMetric,
    QualityTracker,
)

# ==================== Metrics Collector Tests ====================

def test_metrics_collector_counter():
    """Test counter metrics"""
    collector = EnhancedMetricsCollector()

    collector.increment("test_counter")
    collector.increment("test_counter", value=5)

    assert collector.counters["test_counter"] == 6


def test_metrics_collector_gauge():
    """Test gauge metrics"""
    collector = EnhancedMetricsCollector()

    collector.set_gauge("test_gauge", 42.0, unit="celsius")

    assert collector.gauges["test_gauge"] == 42.0


def test_metrics_collector_histogram():
    """Test histogram metrics"""
    collector = EnhancedMetricsCollector()

    collector.observe("test_histogram", 10.0)
    collector.observe("test_histogram", 20.0)
    collector.observe("test_histogram", 30.0)

    assert len(collector.histograms["test_histogram"]) == 3


def test_metrics_collector_timer():
    """Test timer metrics"""
    collector = EnhancedMetricsCollector()

    collector.time_operation("test_operation", 150.5)
    collector.time_operation("test_operation", 200.3)

    assert len(collector.timers["test_operation"]) == 2


def test_metrics_collector_llm_call():
    """Test LLM call recording"""
    collector = EnhancedMetricsCollector()

    collector.record_llm_call(
        model="gpt-4",
        tokens=100,
        cost=0.01,
        duration_ms=1500,
        phase="discovery"
    )

    summary = collector.get_summary()

    assert summary["llm"]["calls"] == 1
    assert summary["llm"]["tokens"] == 100


def test_metrics_collector_cache():
    """Test cache metrics"""
    collector = EnhancedMetricsCollector()

    collector.record_cache_hit("llm_response")
    collector.record_cache_hit("llm_response")
    collector.record_cache_miss("llm_response")

    summary = collector.get_summary()

    assert summary["cache"]["hits"] == 2
    assert summary["cache"]["misses"] == 1
    assert "66.7%" in summary["cache"]["hit_rate"]


def test_metrics_collector_quality():
    """Test quality metrics"""
    collector = EnhancedMetricsCollector()

    collector.record_quality_score("discovery", 8.5)
    collector.record_quality_score("discovery", 7.5)

    summary = collector.get_summary()
    assert "8.00" in summary["quality"]["avg_score"]


def test_metrics_collector_labels():
    """Test metrics with labels"""
    collector = EnhancedMetricsCollector()

    collector.increment("requests", labels={"method": "GET", "status": "200"})
    collector.increment("requests", labels={"method": "POST", "status": "201"})

    assert len(collector.counters) == 2


# ==================== Cost Tracker Tests ====================

def test_cost_tracker_record():
    """Test cost recording"""
    tracker = CostTracker()

    cost = tracker.record_llm_usage(
        model="gpt-4-turbo",
        tokens_input=100,
        tokens_output=50,
        operation="llm_call",
        phase="discovery"
    )

    assert cost > 0
    assert len(tracker.entries) == 1


def test_cost_tracker_summary():
    """Test cost summary"""
    tracker = CostTracker()

    tracker.record_llm_usage("gpt-4", 100, 50)
    tracker.record_llm_usage("gpt-3.5-turbo", 200, 100)

    summary = tracker.get_summary()

    assert summary.total_calls == 2
    assert summary.total_tokens == 450
    assert summary.total_cost_usd > 0


def test_cost_tracker_by_model():
    """Test cost breakdown by model"""
    tracker = CostTracker()

    tracker.record_llm_usage("gpt-4", 100, 50)
    tracker.record_llm_usage("gpt-4", 100, 50)
    tracker.record_llm_usage("gpt-3.5-turbo", 100, 50)

    summary = tracker.get_summary()

    assert "gpt-4" in summary.by_model
    assert "gpt-3.5-turbo" in summary.by_model
    assert summary.by_model["gpt-4"]["calls"] == 2


def test_cost_tracker_budget():
    """Test budget checking"""
    tracker = CostTracker()

    tracker.record_llm_usage("gpt-4", 1000, 1000)  # Expensive call

    budget_status = tracker.check_budget(budget_usd=1.0)

    assert "budget_usd" in budget_status
    assert "spent_usd" in budget_status


# ==================== Quality Tracker Tests ====================

def test_quality_tracker_record():
    """Test quality recording"""
    tracker = QualityTracker()

    tracker.record_quality(
        phase="discovery",
        metric_name="overall",
        score=8.5,
        approved=True,
        issues_count=2
    )

    assert len(tracker.metrics) == 1


def test_quality_tracker_current_avg():
    """Test current average calculation"""
    tracker = QualityTracker()

    tracker.record_quality("discovery", "overall", 8.0, True)
    tracker.record_quality("discovery", "overall", 9.0, True)

    avg = tracker.get_current_avg(phase="discovery", metric_name="overall", days=7)

    assert avg == 8.5


def test_quality_tracker_trend():
    """Test trend detection"""
    tracker = QualityTracker()

    # Add old metrics
    old_metric = QualityMetric(
        timestamp=datetime.now() - timedelta(days=10),
        phase="discovery",
        metric_name="overall",
        score=6.0,
        approved=False,
        issues_count=5,
        metadata={}
    )
    tracker.metrics.append(old_metric)

    # Add recent metrics
    tracker.record_quality("discovery", "overall", 8.0, True)
    tracker.record_quality("discovery", "overall", 9.0, True)

    trend = tracker.get_trend(metric_name="overall", current_days=7, previous_days=7)

    assert trend.trend in ["improving", "stable", "declining"]


def test_quality_tracker_approval_rate():
    """Test approval rate calculation"""
    tracker = QualityTracker()

    tracker.record_quality("discovery", "overall", 8.0, True)
    tracker.record_quality("discovery", "overall", 6.0, False)
    tracker.record_quality("discovery", "overall", 9.0, True)

    approval_rate = tracker.get_approval_rate(days=7)

    assert approval_rate == pytest.approx(66.67, abs=0.1)


# ==================== Alert System Tests ====================

def test_alert_system_add_rule():
    """Test adding alert rules"""
    system = AlertSystem()

    rule = AlertRule(
        name="test_rule",
        metric_name="test_metric",
        condition=lambda x: x > 10,
        severity=AlertSeverity.WARNING,
        message_template="Value too high: {value}"
    )

    system.add_rule(rule)

    assert "test_rule" in system.rules


def test_alert_system_trigger():
    """Test alert triggering"""
    alerts_triggered = []

    def alert_callback(alert):
        alerts_triggered.append(alert)

    system = AlertSystem(alert_callback=alert_callback)

    rule = AlertRule(
        name="high_cost",
        metric_name="cost",
        condition=lambda x: x > 100,
        severity=AlertSeverity.WARNING,
        message_template="Cost exceeded: ${value}"
    )

    system.add_rule(rule)

    # Should not trigger
    system.check_metric("cost", 50)
    assert len(alerts_triggered) == 0

    # Should trigger
    system.check_metric("cost", 150)
    assert len(alerts_triggered) == 1


def test_alert_system_cooldown():
    """Test alert cooldown"""
    system = AlertSystem()

    rule = AlertRule(
        name="test_rule",
        metric_name="test_metric",
        condition=lambda x: x > 10,
        severity=AlertSeverity.WARNING,
        message_template="Value: {value}",
        cooldown_seconds=10
    )

    system.add_rule(rule)

    # First alert
    system.check_metric("test_metric", 20)
    assert len(system.alerts) == 1

    # Second alert (should be blocked by cooldown)
    system.check_metric("test_metric", 30)
    assert len(system.alerts) == 1  # Still just 1


def test_create_cost_alert_rule():
    """Test predefined cost alert rule"""
    rule = create_cost_alert_rule(budget_usd=100.0)

    assert rule.name == "budget_exceeded"
    assert rule.condition(150) is True
    assert rule.condition(50) is False


def test_create_quality_alert_rule():
    """Test predefined quality alert rule"""
    rule = create_quality_alert_rule(min_score=7.0)

    assert rule.name == "low_quality_score"
    assert rule.condition(6.0) is True
    assert rule.condition(8.0) is False


# ==================== Exporter Tests ====================

def test_prometheus_exporter():
    """Test Prometheus exporter"""
    collector = EnhancedMetricsCollector()

    collector.increment("test_counter", labels={"env": "test"})
    collector.set_gauge("test_gauge", 42.0)

    exporter = PrometheusExporter(namespace="test")
    output = exporter.export(collector)

    assert "# HELP" in output
    assert "# TYPE" in output
    assert "test_test_counter" in output


def test_json_exporter():
    """Test JSON exporter"""
    collector = EnhancedMetricsCollector()

    collector.increment("test_counter")

    exporter = JSONExporter(pretty=True)
    output = exporter.export(collector)

    assert "summary" in output
    assert "metrics" in output


def test_dashboard_data_exporter():
    """Test dashboard data exporter"""
    collector = EnhancedMetricsCollector()

    collector.record_llm_call("gpt-4", 100, 0.01, 1500)
    collector.record_quality_score("discovery", 8.5)

    exporter = DashboardDataExporter(collector)
    data = exporter.export_dashboard_data()

    assert "summary" in data
    assert "timeseries" in data
    assert "distributions" in data


def test_metric_to_dict():
    """Test Metric serialization"""
    metric = Metric(
        name="test_metric",
        type=MetricType.COUNTER,
        value=42.0,
        labels={"env": "test"},
        unit="count"
    )

    data = metric.to_dict()

    assert data["name"] == "test_metric"
    assert data["type"] == "counter"
    assert data["value"] == 42.0
