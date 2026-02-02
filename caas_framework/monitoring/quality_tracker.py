"""
Quality Tracker

Track quality metrics and trends over time.
"""

import logging
import statistics
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional


@dataclass
class QualityMetric:
    """Quality metric measurement"""

    timestamp: datetime
    phase: str
    metric_name: str  # e.g., "overall", "clarity", "completeness"
    score: float  # 0-10
    approved: bool
    issues_count: int
    metadata: Dict[str, Any]


@dataclass
class QualityTrend:
    """Quality trend analysis"""

    metric_name: str
    current_avg: float
    previous_avg: float
    change_percent: float
    trend: str  # "improving", "declining", "stable"
    measurements_count: int


class QualityTracker:
    """
    Track quality metrics and trends.

    Features:
    - Track quality scores over time
    - Detect quality trends
    - Identify quality issues
    - Generate quality reports
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize quality tracker"""
        self.logger = logger or logging.getLogger(__name__)
        self.metrics: List[QualityMetric] = []

    def record_quality(
        self,
        phase: str,
        metric_name: str,
        score: float,
        approved: bool,
        issues_count: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Record quality measurement.

        Args:
            phase: Phase name
            metric_name: Metric name (e.g., "overall", "clarity")
            score: Score 0-10
            approved: Whether approved
            issues_count: Number of issues
            metadata: Optional metadata
        """
        metric = QualityMetric(
            timestamp=datetime.now(),
            phase=phase,
            metric_name=metric_name,
            score=score,
            approved=approved,
            issues_count=issues_count,
            metadata=metadata or {},
        )

        self.metrics.append(metric)

        self.logger.debug(
            f"📊 Quality recorded: {phase}/{metric_name} = {score:.1f}/10.0 "
            f"({'✓' if approved else '✗'})"
        )

    def get_current_avg(
        self, phase: Optional[str] = None, metric_name: Optional[str] = None, days: int = 7
    ) -> float:
        """
        Get current average score.

        Args:
            phase: Filter by phase
            metric_name: Filter by metric name
            days: Number of days to include

        Returns:
            Average score
        """
        since = datetime.now() - timedelta(days=days)
        metrics = self._filter_metrics(phase=phase, metric_name=metric_name, since=since)

        if not metrics:
            return 0.0

        return statistics.mean(m.score for m in metrics)

    def get_trend(
        self, metric_name: str = "overall", current_days: int = 7, previous_days: int = 7
    ) -> QualityTrend:
        """
        Get quality trend.

        Args:
            metric_name: Metric to analyze
            current_days: Days for current period
            previous_days: Days for previous period

        Returns:
            QualityTrend
        """
        # Current period
        current_since = datetime.now() - timedelta(days=current_days)
        current_metrics = self._filter_metrics(metric_name=metric_name, since=current_since)

        # Previous period
        previous_until = current_since
        previous_since = previous_until - timedelta(days=previous_days)
        previous_metrics = self._filter_metrics(
            metric_name=metric_name, since=previous_since, until=previous_until
        )

        current_avg = statistics.mean(m.score for m in current_metrics) if current_metrics else 0.0
        previous_avg = (
            statistics.mean(m.score for m in previous_metrics) if previous_metrics else 0.0
        )

        # Calculate change
        if previous_avg > 0:
            change_percent = ((current_avg - previous_avg) / previous_avg) * 100
        else:
            change_percent = 0.0

        # Determine trend
        if abs(change_percent) < 5:
            trend = "stable"
        elif change_percent > 0:
            trend = "improving"
        else:
            trend = "declining"

        return QualityTrend(
            metric_name=metric_name,
            current_avg=current_avg,
            previous_avg=previous_avg,
            change_percent=change_percent,
            trend=trend,
            measurements_count=len(current_metrics),
        )

    def get_approval_rate(self, phase: Optional[str] = None, days: int = 7) -> float:
        """
        Get approval rate.

        Args:
            phase: Optional phase filter
            days: Number of days

        Returns:
            Approval rate (0-100%)
        """
        since = datetime.now() - timedelta(days=days)
        metrics = self._filter_metrics(phase=phase, since=since)

        if not metrics:
            return 0.0

        approved_count = sum(1 for m in metrics if m.approved)
        return (approved_count / len(metrics)) * 100

    def get_summary(self, days: int = 7) -> Dict[str, Any]:
        """
        Get quality summary.

        Args:
            days: Number of days

        Returns:
            Summary dict
        """
        since = datetime.now() - timedelta(days=days)
        metrics = self._filter_metrics(since=since)

        if not metrics:
            return {"measurements": 0, "avg_score": 0.0, "approval_rate": 0.0, "by_phase": {}}

        # Overall stats
        avg_score = statistics.mean(m.score for m in metrics)
        approval_rate = self.get_approval_rate(days=days)

        # By phase
        by_phase = defaultdict(lambda: {"count": 0, "avg_score": 0.0, "approved": 0})

        for metric in metrics:
            by_phase[metric.phase]["count"] += 1
            by_phase[metric.phase]["avg_score"] += metric.score
            if metric.approved:
                by_phase[metric.phase]["approved"] += 1

        # Calculate averages
        for phase_stats in by_phase.values():
            if phase_stats["count"] > 0:
                phase_stats["avg_score"] /= phase_stats["count"]
                phase_stats["approval_rate"] = (
                    phase_stats["approved"] / phase_stats["count"]
                ) * 100

        return {
            "measurements": len(metrics),
            "avg_score": avg_score,
            "approval_rate": approval_rate,
            "by_phase": dict(by_phase),
        }

    def _filter_metrics(
        self,
        phase: Optional[str] = None,
        metric_name: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
    ) -> List[QualityMetric]:
        """Filter metrics by criteria"""
        metrics = self.metrics

        if phase:
            metrics = [m for m in metrics if m.phase == phase]

        if metric_name:
            metrics = [m for m in metrics if m.metric_name == metric_name]

        if since:
            metrics = [m for m in metrics if m.timestamp >= since]

        if until:
            metrics = [m for m in metrics if m.timestamp <= until]

        return metrics
