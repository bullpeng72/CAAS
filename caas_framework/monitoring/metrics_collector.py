"""
Enhanced Metrics Collector

Comprehensive metrics collection integrating:
- LLM usage and costs
- Cache hit rates
- Quality scores
- Performance metrics
- Model usage
"""

import time
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from collections import defaultdict


class MetricType(str, Enum):
    """Types of metrics"""
    COUNTER = "counter"          # Incrementing count
    GAUGE = "gauge"              # Current value
    HISTOGRAM = "histogram"      # Distribution
    TIMER = "timer"              # Duration measurement


@dataclass
class Metric:
    """Individual metric"""
    name: str
    type: MetricType
    value: float
    timestamp: datetime = field(default_factory=datetime.now)
    labels: Dict[str, str] = field(default_factory=dict)
    unit: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "type": self.type.value,
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "labels": self.labels,
            "unit": self.unit
        }


class EnhancedMetricsCollector:
    """
    Enhanced metrics collector with comprehensive tracking.

    Collects:
    - LLM metrics (calls, tokens, costs)
    - Cache metrics (hits, misses, savings)
    - Quality metrics (scores, issues, trends)
    - Performance metrics (latency, throughput)
    - Phase metrics (duration, success rate)
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize metrics collector"""
        self.logger = logger or logging.getLogger(__name__)
        
        # Metric storage
        self.metrics: List[Metric] = []
        self.counters: Dict[str, float] = defaultdict(float)
        self.gauges: Dict[str, float] = {}
        self.histograms: Dict[str, List[float]] = defaultdict(list)
        self.timers: Dict[str, List[float]] = defaultdict(list)
        
        # Start time for uptime
        self.start_time = datetime.now()

    def increment(
        self,
        name: str,
        value: float = 1.0,
        labels: Optional[Dict[str, str]] = None
    ):
        """
        Increment a counter.

        Args:
            name: Counter name
            value: Increment by this value
            labels: Optional labels
        """
        key = self._make_key(name, labels)
        self.counters[key] += value
        
        self.metrics.append(Metric(
            name=name,
            type=MetricType.COUNTER,
            value=self.counters[key],
            labels=labels or {}
        ))

    def set_gauge(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
        unit: str = ""
    ):
        """
        Set a gauge value.

        Args:
            name: Gauge name
            value: Current value
            labels: Optional labels
            unit: Optional unit
        """
        key = self._make_key(name, labels)
        self.gauges[key] = value
        
        self.metrics.append(Metric(
            name=name,
            type=MetricType.GAUGE,
            value=value,
            labels=labels or {},
            unit=unit
        ))

    def observe(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None
    ):
        """
        Observe a value (for histograms).

        Args:
            name: Histogram name
            value: Observed value
            labels: Optional labels
        """
        key = self._make_key(name, labels)
        self.histograms[key].append(value)
        
        self.metrics.append(Metric(
            name=name,
            type=MetricType.HISTOGRAM,
            value=value,
            labels=labels or {}
        ))

    def time_operation(
        self,
        name: str,
        duration_ms: float,
        labels: Optional[Dict[str, str]] = None
    ):
        """
        Record operation duration.

        Args:
            name: Operation name
            duration_ms: Duration in milliseconds
            labels: Optional labels
        """
        key = self._make_key(name, labels)
        self.timers[key].append(duration_ms)
        
        self.metrics.append(Metric(
            name=name,
            type=MetricType.TIMER,
            value=duration_ms,
            labels=labels or {},
            unit="ms"
        ))

    def record_llm_call(
        self,
        model: str,
        tokens: int,
        cost: float,
        duration_ms: float,
        phase: Optional[str] = None
    ):
        """
        Record LLM API call metrics.

        Args:
            model: Model name
            tokens: Tokens used
            cost: Cost in USD
            duration_ms: Duration in ms
            phase: Optional phase name
        """
        labels = {"model": model}
        if phase:
            labels["phase"] = phase

        self.increment("llm_calls_total", labels=labels)
        self.increment("llm_tokens_total", value=tokens, labels=labels)
        self.increment("llm_cost_total", value=cost, labels=labels)
        self.time_operation("llm_duration", duration_ms, labels=labels)

    def record_cache_hit(self, namespace: str):
        """Record cache hit"""
        self.increment("cache_hits_total", labels={"namespace": namespace})

    def record_cache_miss(self, namespace: str):
        """Record cache miss"""
        self.increment("cache_misses_total", labels={"namespace": namespace})

    def record_quality_score(
        self,
        phase: str,
        score: float,
        metric_name: str = "overall"
    ):
        """
        Record quality score.

        Args:
            phase: Phase name
            score: Quality score (0-10)
            metric_name: Metric name (e.g., "overall", "clarity")
        """
        self.observe(
            "quality_score",
            score,
            labels={"phase": phase, "metric": metric_name}
        )

    def record_phase_completion(
        self,
        phase: str,
        duration_ms: float,
        success: bool
    ):
        """
        Record phase completion.

        Args:
            phase: Phase name
            duration_ms: Duration in ms
            success: Whether phase succeeded
        """
        self.time_operation("phase_duration", duration_ms, labels={"phase": phase})
        self.increment(
            "phase_completions_total",
            labels={"phase": phase, "status": "success" if success else "failure"}
        )

    def get_summary(self) -> Dict[str, Any]:
        """
        Get metrics summary.

        Returns:
            Summary dictionary
        """
        # Calculate uptime
        uptime_seconds = (datetime.now() - self.start_time).total_seconds()

        # Aggregate counters
        llm_calls = sum(v for k, v in self.counters.items() if "llm_calls_total" in k)
        llm_tokens = sum(v for k, v in self.counters.items() if "llm_tokens_total" in k)
        llm_cost = sum(v for k, v in self.counters.items() if "llm_cost_total" in k)
        
        cache_hits = sum(v for k, v in self.counters.items() if "cache_hits_total" in k)
        cache_misses = sum(v for k, v in self.counters.items() if "cache_misses_total" in k)
        cache_requests = cache_hits + cache_misses
        cache_hit_rate = (cache_hits / cache_requests * 100) if cache_requests > 0 else 0

        # Average quality scores
        quality_scores = [
            v for k, values in self.histograms.items()
            if "quality_score" in k
            for v in values
        ]
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0

        return {
            "uptime_seconds": uptime_seconds,
            "total_metrics": len(self.metrics),
            "llm": {
                "calls": int(llm_calls),
                "tokens": int(llm_tokens),
                "cost_usd": f"${llm_cost:.4f}",
                "avg_cost_per_call": f"${llm_cost/llm_calls:.4f}" if llm_calls > 0 else "$0"
            },
            "cache": {
                "hits": int(cache_hits),
                "misses": int(cache_misses),
                "hit_rate": f"{cache_hit_rate:.1f}%"
            },
            "quality": {
                "avg_score": f"{avg_quality:.2f}/10.0",
                "measurements": len(quality_scores)
            }
        }

    def get_metrics_by_type(self, metric_type: MetricType) -> List[Metric]:
        """Get metrics filtered by type"""
        return [m for m in self.metrics if m.type == metric_type]

    def get_metrics_by_name(self, name: str) -> List[Metric]:
        """Get metrics filtered by name"""
        return [m for m in self.metrics if m.name == name]

    def clear(self):
        """Clear all metrics"""
        self.metrics.clear()
        self.counters.clear()
        self.gauges.clear()
        self.histograms.clear()
        self.timers.clear()
        self.start_time = datetime.now()

    def _make_key(
        self,
        name: str,
        labels: Optional[Dict[str, str]] = None
    ) -> str:
        """Make unique key for metric with labels"""
        if not labels:
            return name
        
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"

    def export_all(self) -> List[Dict[str, Any]]:
        """Export all metrics as list of dicts"""
        return [m.to_dict() for m in self.metrics]
