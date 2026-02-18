"""
Enhanced Metrics and Monitoring

Comprehensive monitoring system for tracking:
- Real-time metrics
- Cost tracking
- Quality trends
- Performance profiling
- Alerts and anomalies
- Export to monitoring tools
"""

from caas_framework.monitoring.alert_system import (
    Alert,
    AlertRule,
    AlertSeverity,
    AlertSystem,
)
from caas_framework.monitoring.cost_tracker import CostEntry, CostSummary, CostTracker
from caas_framework.monitoring.exporters import (
    JSONExporter,
    MetricsExporter,
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
    QualityTrend,
)

# Global singleton instances
_metrics_collector = None
_cost_tracker = None
_quality_tracker = None
_alert_system = None


def get_metrics_collector() -> EnhancedMetricsCollector:
    """Get or create the global EnhancedMetricsCollector instance."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = EnhancedMetricsCollector()
    return _metrics_collector


def get_cost_tracker() -> CostTracker:
    """Get or create the global CostTracker instance."""
    global _cost_tracker
    if _cost_tracker is None:
        _cost_tracker = CostTracker()
    return _cost_tracker


def get_quality_tracker() -> QualityTracker:
    """Get or create the global QualityTracker instance."""
    global _quality_tracker
    if _quality_tracker is None:
        _quality_tracker = QualityTracker()
    return _quality_tracker


def get_alert_system() -> AlertSystem:
    """Get or create the global AlertSystem instance."""
    global _alert_system
    if _alert_system is None:
        _alert_system = AlertSystem()
    return _alert_system


__all__ = [
    "EnhancedMetricsCollector",
    "get_metrics_collector",
    "MetricType",
    "Metric",
    "CostTracker",
    "CostEntry",
    "CostSummary",
    "QualityTracker",
    "QualityMetric",
    "QualityTrend",
    "AlertSystem",
    "Alert",
    "AlertRule",
    "AlertSeverity",
    "PrometheusExporter",
    "JSONExporter",
    "MetricsExporter",
    "get_cost_tracker",
    "get_quality_tracker",
    "get_alert_system",
]
