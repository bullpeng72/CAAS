"""
Performance Metrics Collector

Collects and tracks performance metrics for BMAD workflow execution:
- Phase execution times
- LLM API usage (calls, tokens, cost)
- Validation runs
- Feedback iterations
- Success rates
- Bottleneck identification
"""

import time
import json
import sqlite3
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
from enum import Enum


class MetricCategory(Enum):
    """Metric category"""
    PHASE_TIMING = "phase_timing"
    LLM_USAGE = "llm_usage"
    VALIDATION = "validation"
    RESOURCE = "resource"


@dataclass
class PhaseMetrics:
    """Metrics for a single phase execution"""
    phase: str  # Phase name (e.g., "concretization", "discovery")
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    llm_calls: int = 0
    llm_tokens_input: int = 0
    llm_tokens_output: int = 0
    llm_tokens_total: int = 0
    llm_cost_usd: float = 0.0
    validation_runs: int = 0
    feedback_iterations: int = 0
    retry_count: int = 0
    memory_mb: float = 0.0
    success: bool = True
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration_ms(self) -> float:
        """Duration in milliseconds"""
        return self.duration_seconds * 1000

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        # Convert datetime to ISO format
        data['start_time'] = self.start_time.isoformat()
        data['end_time'] = self.end_time.isoformat()
        return data


@dataclass
class WorkflowMetrics:
    """Metrics for entire workflow execution"""
    workflow_id: str
    requirement: str
    start_time: datetime
    end_time: datetime
    total_duration_seconds: float
    phases: List[PhaseMetrics] = field(default_factory=list)

    # Aggregate LLM metrics
    total_llm_calls: int = 0
    total_tokens_input: int = 0
    total_tokens_output: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0

    # Workflow stats
    total_phases: int = 0
    successful_phases: int = 0
    failed_phases: int = 0
    success_rate: float = 1.0

    # Performance analysis
    bottleneck_phase: Optional[str] = None
    slowest_phase_duration: float = 0.0
    fastest_phase_duration: float = 0.0
    avg_phase_duration: float = 0.0

    # Resource usage
    peak_memory_mb: float = 0.0

    # Comparison with previous runs
    speedup_vs_baseline: Optional[float] = None
    cost_savings_vs_baseline: Optional[float] = None

    metadata: Dict[str, Any] = field(default_factory=dict)

    def calculate_aggregates(self):
        """Calculate aggregate metrics from phase metrics"""
        if not self.phases:
            return

        # Count phases
        self.total_phases = len(self.phases)
        self.successful_phases = sum(1 for p in self.phases if p.success)
        self.failed_phases = self.total_phases - self.successful_phases
        self.success_rate = self.successful_phases / self.total_phases if self.total_phases > 0 else 0.0

        # Aggregate LLM metrics
        self.total_llm_calls = sum(p.llm_calls for p in self.phases)
        self.total_tokens_input = sum(p.llm_tokens_input for p in self.phases)
        self.total_tokens_output = sum(p.llm_tokens_output for p in self.phases)
        self.total_tokens = sum(p.llm_tokens_total for p in self.phases)
        self.total_cost_usd = sum(p.llm_cost_usd for p in self.phases)

        # Performance analysis
        if self.phases:
            durations = [p.duration_seconds for p in self.phases]
            self.slowest_phase_duration = max(durations)
            self.fastest_phase_duration = min(durations)
            self.avg_phase_duration = sum(durations) / len(durations)

            # Identify bottleneck (slowest phase)
            slowest = max(self.phases, key=lambda p: p.duration_seconds)
            self.bottleneck_phase = slowest.phase

        # Peak memory
        memory_values = [p.memory_mb for p in self.phases if p.memory_mb > 0]
        if memory_values:
            self.peak_memory_mb = max(memory_values)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        # Convert datetime
        data['start_time'] = self.start_time.isoformat()
        data['end_time'] = self.end_time.isoformat()
        # Convert phase metrics
        data['phases'] = [p.to_dict() for p in self.phases]
        return data


class MetricsCollector:
    """
    Performance Metrics Collector

    Collects and manages performance metrics for BMAD workflow execution.
    Supports real-time collection, storage, and analysis.
    """

    def __init__(
        self,
        workflow_id: Optional[str] = None,
        requirement: str = "",
        storage_path: Optional[Path] = None,
        enable_sqlite: bool = False
    ):
        """
        Initialize metrics collector

        Args:
            workflow_id: Unique workflow identifier
            requirement: Requirement being processed
            storage_path: Path to store metrics (JSON/SQLite)
            enable_sqlite: Enable SQLite storage (default: False, use JSON)
        """
        self.workflow_id = workflow_id or f"workflow_{int(time.time())}"
        self.requirement = requirement
        self.storage_path = storage_path or Path("./metrics")
        self.enable_sqlite = enable_sqlite

        # Ensure storage directory exists
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # Current workflow metrics
        self.workflow_start_time: Optional[datetime] = None
        self.workflow_end_time: Optional[datetime] = None
        self.phase_metrics: List[PhaseMetrics] = []

        # Phase timers
        self.phase_timers: Dict[str, float] = {}
        self.phase_counters: Dict[str, Dict[str, int]] = {}

        # SQLite connection (if enabled)
        self.db_conn: Optional[sqlite3.Connection] = None
        if enable_sqlite:
            self._init_sqlite()

    def _init_sqlite(self):
        """Initialize SQLite database"""
        db_path = self.storage_path / "metrics.db"
        self.db_conn = sqlite3.connect(str(db_path))

        # Create tables
        self.db_conn.execute('''
            CREATE TABLE IF NOT EXISTS workflows (
                workflow_id TEXT PRIMARY KEY,
                requirement TEXT,
                start_time TEXT,
                end_time TEXT,
                total_duration REAL,
                total_llm_calls INTEGER,
                total_tokens INTEGER,
                total_cost REAL,
                success_rate REAL,
                bottleneck_phase TEXT,
                metadata TEXT
            )
        ''')

        self.db_conn.execute('''
            CREATE TABLE IF NOT EXISTS phases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workflow_id TEXT,
                phase TEXT,
                start_time TEXT,
                end_time TEXT,
                duration REAL,
                llm_calls INTEGER,
                tokens_total INTEGER,
                cost REAL,
                success BOOLEAN,
                error TEXT,
                FOREIGN KEY (workflow_id) REFERENCES workflows(workflow_id)
            )
        ''')

        self.db_conn.commit()

    def start_workflow(self):
        """Start workflow timing"""
        self.workflow_start_time = datetime.now()

    def end_workflow(self):
        """End workflow timing"""
        self.workflow_end_time = datetime.now()

    def start_phase(self, phase: str):
        """
        Start phase timing

        Args:
            phase: Phase name
        """
        self.phase_timers[phase] = time.time()

        # Initialize counters
        if phase not in self.phase_counters:
            self.phase_counters[phase] = {
                'llm_calls': 0,
                'tokens_input': 0,
                'tokens_output': 0,
                'validation_runs': 0,
                'feedback_iterations': 0,
                'retry_count': 0
            }

    def record_llm_call(
        self,
        phase: str,
        tokens_input: int,
        tokens_output: int,
        cost_usd: float
    ):
        """
        Record LLM API call

        Args:
            phase: Phase name
            tokens_input: Input tokens used
            tokens_output: Output tokens generated
            cost_usd: Cost in USD
        """
        if phase in self.phase_counters:
            self.phase_counters[phase]['llm_calls'] += 1
            self.phase_counters[phase]['tokens_input'] += tokens_input
            self.phase_counters[phase]['tokens_output'] += tokens_output

    def record_validation(self, phase: str):
        """Record validation run"""
        if phase in self.phase_counters:
            self.phase_counters[phase]['validation_runs'] += 1

    def record_feedback_iteration(self, phase: str):
        """Record feedback iteration"""
        if phase in self.phase_counters:
            self.phase_counters[phase]['feedback_iterations'] += 1

    def record_retry(self, phase: str):
        """Record retry attempt"""
        if phase in self.phase_counters:
            self.phase_counters[phase]['retry_count'] += 1

    def end_phase(
        self,
        phase: str,
        success: bool = True,
        error: Optional[str] = None,
        memory_mb: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> PhaseMetrics:
        """
        End phase and create metrics

        Args:
            phase: Phase name
            success: Whether phase succeeded
            error: Error message if failed
            memory_mb: Memory usage in MB
            metadata: Additional metadata

        Returns:
            PhaseMetrics for this phase
        """
        if phase not in self.phase_timers:
            raise ValueError(f"Phase {phase} was not started")

        end_time = datetime.now()
        start_timestamp = self.phase_timers[phase]
        start_time = datetime.fromtimestamp(start_timestamp)
        duration = time.time() - start_timestamp

        # Get counters
        counters = self.phase_counters.get(phase, {})

        # Calculate cost (OpenAI pricing example)
        # Input: $0.01 per 1K tokens, Output: $0.03 per 1K tokens
        tokens_input = counters.get('tokens_input', 0)
        tokens_output = counters.get('tokens_output', 0)
        cost = (tokens_input / 1000 * 0.01) + (tokens_output / 1000 * 0.03)

        metric = PhaseMetrics(
            phase=phase,
            start_time=start_time,
            end_time=end_time,
            duration_seconds=duration,
            llm_calls=counters.get('llm_calls', 0),
            llm_tokens_input=tokens_input,
            llm_tokens_output=tokens_output,
            llm_tokens_total=tokens_input + tokens_output,
            llm_cost_usd=cost,
            validation_runs=counters.get('validation_runs', 0),
            feedback_iterations=counters.get('feedback_iterations', 0),
            retry_count=counters.get('retry_count', 0),
            memory_mb=memory_mb,
            success=success,
            error=error,
            metadata=metadata or {}
        )

        self.phase_metrics.append(metric)

        # Cleanup
        del self.phase_timers[phase]

        return metric

    def get_workflow_metrics(self) -> WorkflowMetrics:
        """
        Get complete workflow metrics

        Returns:
            WorkflowMetrics with all aggregates calculated
        """
        if not self.workflow_start_time:
            raise ValueError("Workflow was not started")

        end_time = self.workflow_end_time or datetime.now()
        duration = (end_time - self.workflow_start_time).total_seconds()

        metrics = WorkflowMetrics(
            workflow_id=self.workflow_id,
            requirement=self.requirement,
            start_time=self.workflow_start_time,
            end_time=end_time,
            total_duration_seconds=duration,
            phases=self.phase_metrics
        )

        # Calculate aggregates
        metrics.calculate_aggregates()

        return metrics

    def save_metrics(self, metrics: Optional[WorkflowMetrics] = None):
        """
        Save metrics to storage

        Args:
            metrics: WorkflowMetrics to save (default: get current)
        """
        if metrics is None:
            metrics = self.get_workflow_metrics()

        # Save to JSON
        json_path = self.storage_path / f"{self.workflow_id}.json"
        with open(json_path, 'w') as f:
            json.dump(metrics.to_dict(), f, indent=2)

        # Save to SQLite if enabled
        if self.enable_sqlite and self.db_conn:
            self._save_to_sqlite(metrics)

    def _save_to_sqlite(self, metrics: WorkflowMetrics):
        """Save metrics to SQLite database"""
        # Insert workflow
        self.db_conn.execute('''
            INSERT OR REPLACE INTO workflows VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            metrics.workflow_id,
            metrics.requirement,
            metrics.start_time.isoformat(),
            metrics.end_time.isoformat(),
            metrics.total_duration_seconds,
            metrics.total_llm_calls,
            metrics.total_tokens,
            metrics.total_cost_usd,
            metrics.success_rate,
            metrics.bottleneck_phase,
            json.dumps(metrics.metadata)
        ))

        # Insert phases
        for phase in metrics.phases:
            self.db_conn.execute('''
                INSERT INTO phases (workflow_id, phase, start_time, end_time, duration,
                                   llm_calls, tokens_total, cost, success, error)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                metrics.workflow_id,
                phase.phase,
                phase.start_time.isoformat(),
                phase.end_time.isoformat(),
                phase.duration_seconds,
                phase.llm_calls,
                phase.llm_tokens_total,
                phase.llm_cost_usd,
                phase.success,
                phase.error
            ))

        self.db_conn.commit()

    @staticmethod
    def load_metrics(workflow_id: str, storage_path: Path = Path("./metrics")) -> WorkflowMetrics:
        """
        Load metrics from storage

        Args:
            workflow_id: Workflow ID to load
            storage_path: Path to storage directory

        Returns:
            WorkflowMetrics
        """
        json_path = storage_path / f"{workflow_id}.json"

        if not json_path.exists():
            raise FileNotFoundError(f"Metrics file not found: {json_path}")

        with open(json_path, 'r') as f:
            data = json.load(f)

        # Reconstruct WorkflowMetrics
        workflow_metrics = WorkflowMetrics(
            workflow_id=data['workflow_id'],
            requirement=data['requirement'],
            start_time=datetime.fromisoformat(data['start_time']),
            end_time=datetime.fromisoformat(data['end_time']),
            total_duration_seconds=data['total_duration_seconds'],
            phases=[
                PhaseMetrics(
                    phase=p['phase'],
                    start_time=datetime.fromisoformat(p['start_time']),
                    end_time=datetime.fromisoformat(p['end_time']),
                    duration_seconds=p['duration_seconds'],
                    llm_calls=p['llm_calls'],
                    llm_tokens_input=p['llm_tokens_input'],
                    llm_tokens_output=p['llm_tokens_output'],
                    llm_tokens_total=p['llm_tokens_total'],
                    llm_cost_usd=p['llm_cost_usd'],
                    validation_runs=p['validation_runs'],
                    feedback_iterations=p['feedback_iterations'],
                    retry_count=p['retry_count'],
                    memory_mb=p['memory_mb'],
                    success=p['success'],
                    error=p.get('error'),
                    metadata=p.get('metadata', {})
                )
                for p in data['phases']
            ],
            total_llm_calls=data['total_llm_calls'],
            total_tokens_input=data['total_tokens_input'],
            total_tokens_output=data['total_tokens_output'],
            total_tokens=data['total_tokens'],
            total_cost_usd=data['total_cost_usd'],
            total_phases=data['total_phases'],
            successful_phases=data['successful_phases'],
            failed_phases=data['failed_phases'],
            success_rate=data['success_rate'],
            bottleneck_phase=data.get('bottleneck_phase'),
            slowest_phase_duration=data['slowest_phase_duration'],
            fastest_phase_duration=data['fastest_phase_duration'],
            avg_phase_duration=data['avg_phase_duration'],
            peak_memory_mb=data['peak_memory_mb'],
            metadata=data.get('metadata', {})
        )

        return workflow_metrics

    def compare_with_baseline(
        self,
        current: WorkflowMetrics,
        baseline: WorkflowMetrics
    ) -> Dict[str, Any]:
        """
        Compare current metrics with baseline

        Args:
            current: Current workflow metrics
            baseline: Baseline workflow metrics

        Returns:
            Comparison dict with improvements/regressions
        """
        duration_diff = current.total_duration_seconds - baseline.total_duration_seconds
        duration_pct = (duration_diff / baseline.total_duration_seconds) * 100 if baseline.total_duration_seconds > 0 else 0

        cost_diff = current.total_cost_usd - baseline.total_cost_usd
        cost_pct = (cost_diff / baseline.total_cost_usd) * 100 if baseline.total_cost_usd > 0 else 0

        speedup = baseline.total_duration_seconds / current.total_duration_seconds if current.total_duration_seconds > 0 else 1.0

        return {
            "duration_improvement": {
                "baseline_seconds": baseline.total_duration_seconds,
                "current_seconds": current.total_duration_seconds,
                "difference_seconds": duration_diff,
                "difference_percent": duration_pct,
                "improved": duration_diff < 0
            },
            "cost_improvement": {
                "baseline_usd": baseline.total_cost_usd,
                "current_usd": current.total_cost_usd,
                "difference_usd": cost_diff,
                "difference_percent": cost_pct,
                "improved": cost_diff < 0
            },
            "speedup": speedup,
            "tokens_saved": baseline.total_tokens - current.total_tokens,
            "llm_calls_saved": baseline.total_llm_calls - current.total_llm_calls
        }

    def close(self):
        """Close collector and cleanup resources"""
        if self.db_conn:
            self.db_conn.close()

    def __enter__(self):
        """Context manager entry"""
        self.start_workflow()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.end_workflow()
        self.save_metrics()
        self.close()
