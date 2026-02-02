"""
Alert System

Monitor metrics and trigger alerts on anomalies.
"""

import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class AlertSeverity(str, Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Alert:
    """Alert notification"""
    timestamp: datetime
    severity: AlertSeverity
    title: str
    message: str
    metric_name: str
    metric_value: Any
    threshold: Any
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "severity": self.severity.value,
            "title": self.title,
            "message": self.message,
            "metric_name": self.metric_name,
            "metric_value": self.metric_value,
            "threshold": self.threshold,
            "metadata": self.metadata
        }


@dataclass
class AlertRule:
    """Alert rule configuration"""
    name: str
    metric_name: str
    condition: Callable[[Any], bool]  # Function that returns True to trigger alert
    severity: AlertSeverity
    message_template: str
    cooldown_seconds: int = 300  # Don't re-alert for 5 minutes
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


class AlertSystem:
    """
    Monitor metrics and trigger alerts.

    Features:
    - Configurable alert rules
    - Cooldown to prevent alert spam
    - Multiple severity levels
    - Alert callbacks
    """

    def __init__(
        self,
        alert_callback: Optional[Callable[[Alert], None]] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize alert system.

        Args:
            alert_callback: Optional callback for alerts
            logger: Optional logger
        """
        self.logger = logger or logging.getLogger(__name__)
        self.alert_callback = alert_callback
        self.rules: Dict[str, AlertRule] = {}
        self.alerts: List[Alert] = []
        self.last_alert_time: Dict[str, datetime] = {}

    def add_rule(self, rule: AlertRule):
        """Add alert rule"""
        self.rules[rule.name] = rule
        self.logger.info(f"📢 Alert rule added: {rule.name}")

    def remove_rule(self, name: str):
        """Remove alert rule"""
        if name in self.rules:
            del self.rules[name]
            self.logger.info(f"🔇 Alert rule removed: {name}")

    def check_metric(
        self,
        metric_name: str,
        value: Any,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Check metric against all rules.

        Args:
            metric_name: Metric name
            value: Metric value
            metadata: Optional metadata
        """
        for rule in self.rules.values():
            if not rule.enabled:
                continue

            if rule.metric_name != metric_name:
                continue

            # Check cooldown
            if self._is_in_cooldown(rule.name, rule.cooldown_seconds):
                continue

            # Check condition
            try:
                if rule.condition(value):
                    self._trigger_alert(rule, value, metadata or {})
            except Exception as e:
                self.logger.error(f"Error checking rule {rule.name}: {e}")

    def _trigger_alert(
        self,
        rule: AlertRule,
        value: Any,
        metadata: Dict[str, Any]
    ):
        """Trigger an alert"""
        alert = Alert(
            timestamp=datetime.now(),
            severity=rule.severity,
            title=rule.name,
            message=rule.message_template.format(value=value),
            metric_name=rule.metric_name,
            metric_value=value,
            threshold=rule.metadata.get("threshold"),
            metadata=metadata
        )

        self.alerts.append(alert)
        self.last_alert_time[rule.name] = alert.timestamp

        # Log alert
        emoji = {
            AlertSeverity.INFO: "ℹ️",
            AlertSeverity.WARNING: "⚠️",
            AlertSeverity.ERROR: "❌",
            AlertSeverity.CRITICAL: "🚨"
        }[rule.severity]

        self.logger.warning(
            f"{emoji} ALERT [{rule.severity.value.upper()}] {rule.name}: "
            f"{alert.message}"
        )

        # Call callback
        if self.alert_callback:
            try:
                self.alert_callback(alert)
            except Exception as e:
                self.logger.error(f"Error in alert callback: {e}")

    def _is_in_cooldown(self, rule_name: str, cooldown_seconds: int) -> bool:
        """Check if rule is in cooldown period"""
        if rule_name not in self.last_alert_time:
            return False

        last_alert = self.last_alert_time[rule_name]
        elapsed = (datetime.now() - last_alert).total_seconds()

        return elapsed < cooldown_seconds

    def get_recent_alerts(
        self,
        severity: Optional[AlertSeverity] = None,
        count: int = 10
    ) -> List[Alert]:
        """
        Get recent alerts.

        Args:
            severity: Filter by severity
            count: Number of alerts to return

        Returns:
            List of alerts
        """
        alerts = self.alerts

        if severity:
            alerts = [a for a in alerts if a.severity == severity]

        # Sort by timestamp descending
        alerts = sorted(alerts, key=lambda a: a.timestamp, reverse=True)

        return alerts[:count]

    def get_alert_summary(self) -> Dict[str, Any]:
        """Get alert summary"""
        by_severity = {
            AlertSeverity.INFO: 0,
            AlertSeverity.WARNING: 0,
            AlertSeverity.ERROR: 0,
            AlertSeverity.CRITICAL: 0
        }

        for alert in self.alerts:
            by_severity[alert.severity] += 1

        return {
            "total_alerts": len(self.alerts),
            "by_severity": {
                k.value: v for k, v in by_severity.items()
            },
            "active_rules": len([r for r in self.rules.values() if r.enabled])
        }

    def clear_alerts(self):
        """Clear all alerts"""
        self.alerts.clear()
        self.last_alert_time.clear()


# Predefined alert rules
def create_cost_alert_rule(budget_usd: float) -> AlertRule:
    """Create alert rule for budget exceeded"""
    return AlertRule(
        name="budget_exceeded",
        metric_name="total_cost",
        condition=lambda cost: cost > budget_usd,
        severity=AlertSeverity.WARNING,
        message_template=f"Budget exceeded: ${{value:.2f}} > ${budget_usd}",
        metadata={"threshold": budget_usd}
    )


def create_quality_alert_rule(min_score: float = 6.0) -> AlertRule:
    """Create alert rule for low quality"""
    return AlertRule(
        name="low_quality_score",
        metric_name="quality_score",
        condition=lambda score: score < min_score,
        severity=AlertSeverity.WARNING,
        message_template=f"Low quality score: {{value:.1f}} < {min_score}",
        metadata={"threshold": min_score}
    )


def create_cache_miss_alert_rule(max_miss_rate: float = 80.0) -> AlertRule:
    """Create alert rule for high cache miss rate"""
    return AlertRule(
        name="high_cache_miss_rate",
        metric_name="cache_miss_rate",
        condition=lambda rate: rate > max_miss_rate,
        severity=AlertSeverity.INFO,
        message_template=f"High cache miss rate: {{value:.1f}}% > {max_miss_rate}%",
        metadata={"threshold": max_miss_rate}
    )
