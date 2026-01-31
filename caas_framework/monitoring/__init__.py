"""
Monitoring Module

Performance monitoring and metrics collection for CAAS workflows:
- MetricsCollector: Collect and store performance metrics
- PerformanceDashboard: Visualize metrics with Rich console
- Report generation: Markdown and HTML reports
"""

from caas_framework.monitoring.metrics_collector import (
    MetricsCollector,
    WorkflowMetrics,
    PhaseMetrics,
    MetricCategory
)

from caas_framework.monitoring.dashboard import PerformanceDashboard

__all__ = [
    "MetricsCollector",
    "WorkflowMetrics",
    "PhaseMetrics",
    "MetricCategory",
    "PerformanceDashboard"
]
