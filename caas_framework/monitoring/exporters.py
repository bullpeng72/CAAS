"""
Metrics Exporters

Export metrics to various formats and monitoring tools.
"""

import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

from caas_framework.monitoring.metrics_collector import EnhancedMetricsCollector, Metric


class MetricsExporter(ABC):
    """Base class for metrics exporters"""

    @abstractmethod
    def export(self, metrics_collector: EnhancedMetricsCollector) -> str:
        """Export metrics to string format"""


class PrometheusExporter(MetricsExporter):
    """
    Export metrics in Prometheus format.

    Format:
    # HELP metric_name Description
    # TYPE metric_name type
    metric_name{label1="value1"} value timestamp
    """

    def __init__(self, namespace: str = "caas"):
        """
        Initialize Prometheus exporter.

        Args:
            namespace: Metrics namespace prefix
        """
        self.namespace = namespace

    def export(self, metrics_collector: EnhancedMetricsCollector) -> str:
        """
        Export metrics in Prometheus format.

        Args:
            metrics_collector: Metrics collector

        Returns:
            Prometheus formatted string
        """
        lines = []

        # Group metrics by name
        metrics_by_name: Dict[str, List[Metric]] = {}
        for metric in metrics_collector.metrics:
            if metric.name not in metrics_by_name:
                metrics_by_name[metric.name] = []
            metrics_by_name[metric.name].append(metric)

        # Export each metric group
        for name, metrics in metrics_by_name.items():
            if not metrics:
                continue

            metric_name = f"{self.namespace}_{name}"
            metric_type = metrics[0].type.value

            # HELP
            lines.append(f"# HELP {metric_name} {name}")

            # TYPE (map to Prometheus types)
            prom_type = {
                "counter": "counter",
                "gauge": "gauge",
                "histogram": "histogram",
                "timer": "histogram",
            }.get(metric_type, "gauge")

            lines.append(f"# TYPE {metric_name} {prom_type}")

            # Metrics
            for metric in metrics:
                labels = self._format_labels(metric.labels)
                timestamp_ms = int(metric.timestamp.timestamp() * 1000)

                lines.append(f"{metric_name}{labels} {metric.value} {timestamp_ms}")

        return "\n".join(lines)

    def _format_labels(self, labels: Dict[str, str]) -> str:
        """Format labels for Prometheus"""
        if not labels:
            return ""

        label_pairs = [f'{k}="{v}"' for k, v in sorted(labels.items())]
        return "{" + ",".join(label_pairs) + "}"


class JSONExporter(MetricsExporter):
    """Export metrics in JSON format"""

    def __init__(self, pretty: bool = True):
        """
        Initialize JSON exporter.

        Args:
            pretty: Pretty print JSON
        """
        self.pretty = pretty

    def export(self, metrics_collector: EnhancedMetricsCollector) -> str:
        """
        Export metrics in JSON format.

        Args:
            metrics_collector: Metrics collector

        Returns:
            JSON string
        """
        data = {
            "timestamp": datetime.now().isoformat(),
            "summary": metrics_collector.get_summary(),
            "metrics": metrics_collector.export_all(),
        }

        if self.pretty:
            return json.dumps(data, indent=2)
        else:
            return json.dumps(data)


class DashboardDataExporter:
    """
    Export data formatted for dashboard visualization.

    Provides time-series data, summaries, and aggregations.
    """

    def __init__(
        self, metrics_collector: EnhancedMetricsCollector, logger: Optional[logging.Logger] = None
    ):
        """
        Initialize dashboard exporter.

        Args:
            metrics_collector: Metrics collector
            logger: Optional logger
        """
        self.metrics = metrics_collector
        self.logger = logger or logging.getLogger(__name__)

    def export_dashboard_data(self) -> Dict[str, Any]:
        """
        Export comprehensive dashboard data.

        Returns:
            Dashboard data dictionary
        """
        return {
            "summary": self.metrics.get_summary(),
            "timeseries": self._get_timeseries(),
            "distributions": self._get_distributions(),
            "top_metrics": self._get_top_metrics(),
        }

    def _get_timeseries(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get time-series data for charts"""
        timeseries = {}

        # LLM calls over time
        llm_calls = self.metrics.get_metrics_by_name("llm_calls_total")
        timeseries["llm_calls"] = [
            {"timestamp": m.timestamp.isoformat(), "value": m.value, "labels": m.labels}
            for m in llm_calls
        ]

        # Quality scores over time
        quality_scores = self.metrics.get_metrics_by_name("quality_score")
        timeseries["quality_scores"] = [
            {"timestamp": m.timestamp.isoformat(), "value": m.value, "labels": m.labels}
            for m in quality_scores
        ]

        return timeseries

    def _get_distributions(self) -> Dict[str, Any]:
        """Get metric distributions"""
        distributions = {}

        # LLM duration distribution
        llm_durations = [m.value for m in self.metrics.get_metrics_by_name("llm_duration")]
        if llm_durations:
            distributions["llm_duration"] = {
                "min": min(llm_durations),
                "max": max(llm_durations),
                "avg": sum(llm_durations) / len(llm_durations),
                "count": len(llm_durations),
            }

        # Quality score distribution
        quality_scores = [m.value for m in self.metrics.get_metrics_by_name("quality_score")]
        if quality_scores:
            distributions["quality_score"] = {
                "min": min(quality_scores),
                "max": max(quality_scores),
                "avg": sum(quality_scores) / len(quality_scores),
                "count": len(quality_scores),
            }

        return distributions

    def _get_top_metrics(self, count: int = 10) -> Dict[str, List[Dict[str, Any]]]:
        """Get top metrics by value"""
        top_metrics = {}

        # Top phases by duration
        phase_durations = self.metrics.get_metrics_by_name("phase_duration")
        top_phases = sorted(phase_durations, key=lambda m: m.value, reverse=True)[:count]

        top_metrics["slowest_phases"] = [
            {"phase": m.labels.get("phase", "unknown"), "duration_ms": m.value} for m in top_phases
        ]

        return top_metrics
