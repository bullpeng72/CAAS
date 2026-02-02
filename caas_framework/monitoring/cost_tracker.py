"""
Cost Tracker

Detailed tracking of LLM usage costs.
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict


@dataclass
class CostEntry:
    """Single cost entry"""
    timestamp: datetime
    model: str
    operation: str  # e.g., "llm_call", "validation", "refinement"
    tokens_input: int
    tokens_output: int
    tokens_total: int
    cost_usd: float
    phase: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CostSummary:
    """Cost summary"""
    total_cost_usd: float
    total_tokens: int
    total_calls: int
    avg_cost_per_call: float
    avg_tokens_per_call: float
    by_model: Dict[str, Dict[str, Any]]
    by_phase: Dict[str, Dict[str, Any]]
    by_operation: Dict[str, Dict[str, Any]]
    time_period: str


class CostTracker:
    """
    Track LLM usage costs with detailed breakdowns.

    Features:
    - Per-model cost tracking
    - Per-phase cost tracking
    - Per-operation cost tracking
    - Time-based aggregation
    - Cost alerts
    """

    # Model pricing (per 1K tokens)
    MODEL_PRICING = {
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        "gpt-4": {"input": 0.03, "output": 0.06},
        "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
        "claude-3-opus": {"input": 0.015, "output": 0.075},
        "claude-3-sonnet": {"input": 0.003, "output": 0.015},
    }

    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize cost tracker"""
        self.logger = logger or logging.getLogger(__name__)
        self.entries: List[CostEntry] = []
        self.start_time = datetime.now()

    def record_llm_usage(
        self,
        model: str,
        tokens_input: int,
        tokens_output: int,
        operation: str = "llm_call",
        phase: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        Record LLM usage and calculate cost.

        Args:
            model: Model name
            tokens_input: Input tokens
            tokens_output: Output tokens
            operation: Operation type
            phase: Optional phase
            metadata: Optional metadata

        Returns:
            Cost in USD
        """
        # Calculate cost
        cost = self._calculate_cost(model, tokens_input, tokens_output)

        # Create entry
        entry = CostEntry(
            timestamp=datetime.now(),
            model=model,
            operation=operation,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            tokens_total=tokens_input + tokens_output,
            cost_usd=cost,
            phase=phase,
            metadata=metadata or {}
        )

        self.entries.append(entry)
        
        self.logger.debug(
            f"💰 Cost recorded: {model} - ${cost:.4f} "
            f"({tokens_input}+{tokens_output} tokens)"
        )

        return cost

    def _calculate_cost(
        self,
        model: str,
        tokens_input: int,
        tokens_output: int
    ) -> float:
        """Calculate cost for model usage"""
        # Get pricing for model
        pricing = self.MODEL_PRICING.get(model)
        
        if not pricing:
            self.logger.warning(f"No pricing for model: {model}, using GPT-3.5 pricing")
            pricing = self.MODEL_PRICING["gpt-3.5-turbo"]

        # Calculate cost (pricing is per 1K tokens)
        input_cost = (tokens_input / 1000) * pricing["input"]
        output_cost = (tokens_output / 1000) * pricing["output"]

        return input_cost + output_cost

    def get_summary(
        self,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None
    ) -> CostSummary:
        """
        Get cost summary for time period.

        Args:
            since: Start time (None = all time)
            until: End time (None = now)

        Returns:
            CostSummary
        """
        # Filter entries by time
        entries = self._filter_by_time(since, until)

        if not entries:
            return CostSummary(
                total_cost_usd=0.0,
                total_tokens=0,
                total_calls=0,
                avg_cost_per_call=0.0,
                avg_tokens_per_call=0.0,
                by_model={},
                by_phase={},
                by_operation={},
                time_period=self._format_time_period(since, until)
            )

        # Calculate totals
        total_cost = sum(e.cost_usd for e in entries)
        total_tokens = sum(e.tokens_total for e in entries)
        total_calls = len(entries)

        # By model
        by_model = defaultdict(lambda: {"cost": 0.0, "tokens": 0, "calls": 0})
        for entry in entries:
            by_model[entry.model]["cost"] += entry.cost_usd
            by_model[entry.model]["tokens"] += entry.tokens_total
            by_model[entry.model]["calls"] += 1

        # By phase
        by_phase = defaultdict(lambda: {"cost": 0.0, "tokens": 0, "calls": 0})
        for entry in entries:
            phase = entry.phase or "unknown"
            by_phase[phase]["cost"] += entry.cost_usd
            by_phase[phase]["tokens"] += entry.tokens_total
            by_phase[phase]["calls"] += 1

        # By operation
        by_operation = defaultdict(lambda: {"cost": 0.0, "tokens": 0, "calls": 0})
        for entry in entries:
            by_operation[entry.operation]["cost"] += entry.cost_usd
            by_operation[entry.operation]["tokens"] += entry.tokens_total
            by_operation[entry.operation]["calls"] += 1

        return CostSummary(
            total_cost_usd=total_cost,
            total_tokens=total_tokens,
            total_calls=total_calls,
            avg_cost_per_call=total_cost / total_calls,
            avg_tokens_per_call=total_tokens / total_calls,
            by_model=dict(by_model),
            by_phase=dict(by_phase),
            by_operation=dict(by_operation),
            time_period=self._format_time_period(since, until)
        )

    def get_daily_costs(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        Get daily cost breakdown.

        Args:
            days: Number of days to include

        Returns:
            List of daily summaries
        """
        daily_costs = []
        
        for i in range(days):
            day_start = datetime.now() - timedelta(days=i+1)
            day_end = datetime.now() - timedelta(days=i)
            
            day_entries = self._filter_by_time(day_start, day_end)
            day_cost = sum(e.cost_usd for e in day_entries)
            day_tokens = sum(e.tokens_total for e in day_entries)
            
            daily_costs.append({
                "date": day_start.strftime("%Y-%m-%d"),
                "cost_usd": day_cost,
                "tokens": day_tokens,
                "calls": len(day_entries)
            })

        return list(reversed(daily_costs))

    def check_budget(self, budget_usd: float) -> Dict[str, Any]:
        """
        Check if costs exceed budget.

        Args:
            budget_usd: Budget in USD

        Returns:
            Budget status
        """
        summary = self.get_summary()
        percentage = (summary.total_cost_usd / budget_usd * 100) if budget_usd > 0 else 0

        return {
            "budget_usd": budget_usd,
            "spent_usd": summary.total_cost_usd,
            "remaining_usd": budget_usd - summary.total_cost_usd,
            "percentage_used": percentage,
            "over_budget": summary.total_cost_usd > budget_usd
        }

    def _filter_by_time(
        self,
        since: Optional[datetime],
        until: Optional[datetime]
    ) -> List[CostEntry]:
        """Filter entries by time range"""
        entries = self.entries

        if since:
            entries = [e for e in entries if e.timestamp >= since]

        if until:
            entries = [e for e in entries if e.timestamp <= until]

        return entries

    def _format_time_period(
        self,
        since: Optional[datetime],
        until: Optional[datetime]
    ) -> str:
        """Format time period string"""
        if since and until:
            return f"{since.strftime('%Y-%m-%d')} to {until.strftime('%Y-%m-%d')}"
        elif since:
            return f"Since {since.strftime('%Y-%m-%d')}"
        elif until:
            return f"Until {until.strftime('%Y-%m-%d')}"
        else:
            return "All time"

    def export_entries(self) -> List[Dict[str, Any]]:
        """Export all cost entries"""
        return [
            {
                "timestamp": e.timestamp.isoformat(),
                "model": e.model,
                "operation": e.operation,
                "phase": e.phase,
                "tokens_input": e.tokens_input,
                "tokens_output": e.tokens_output,
                "tokens_total": e.tokens_total,
                "cost_usd": e.cost_usd,
                "metadata": e.metadata
            }
            for e in self.entries
        ]
