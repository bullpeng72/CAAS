"""
Iteration Control Data Models

Defines models for 3-level iteration system:
- Macro: Epic-level iteration (multi-story retry)
- Micro: Story-level iteration (phase retry)
- Nano: TDD cycle iteration (test-code-refactor)

Part of CAAS-E Week 6 implementation (Task 6.2).
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime


class IterationLevel(Enum):
    """Iteration hierarchy levels"""
    MACRO = "macro"  # Epic-level (multiple stories)
    MICRO = "micro"  # Story-level (single story retry)
    NANO = "nano"  # TDD cycle (red-green-refactor)


class IterationStatus(Enum):
    """Iteration execution status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"
    EXHAUSTED = "exhausted"  # Max retries reached


class FailureReason(Enum):
    """Categorized failure reasons"""
    TEST_FAILURE = "test_failure"
    VALIDATION_ERROR = "validation_error"
    QUALITY_GATE_FAILURE = "quality_gate_failure"
    COMPILATION_ERROR = "compilation_error"
    RUNTIME_ERROR = "runtime_error"
    DEPENDENCY_ERROR = "dependency_error"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


@dataclass
class IterationAttempt:
    """Single iteration attempt"""
    attempt_number: int
    timestamp: datetime
    status: IterationStatus
    duration_seconds: float
    failure_reason: Optional[FailureReason] = None
    error_message: Optional[str] = None
    artifacts: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, float] = field(default_factory=dict)


@dataclass
class NanoIteration:
    """
    Nano-level iteration (TDD cycle).

    One RED-GREEN-REFACTOR cycle:
    1. RED: Write failing test
    2. GREEN: Minimal implementation
    3. REFACTOR: Improve code quality
    """
    iteration_id: str
    test_file: str
    implementation_file: str
    max_retries: int = 3
    current_attempt: int = 0
    status: IterationStatus = IterationStatus.PENDING
    attempts: List[IterationAttempt] = field(default_factory=list)
    test_passed: bool = False
    code_quality_score: float = 0.0
    refactored: bool = False


@dataclass
class MicroIteration:
    """
    Micro-level iteration (Story-level).

    Retry logic for a single user story:
    - Phase-level rollback
    - Incremental fixes
    - State preservation
    """
    iteration_id: str
    story_id: str
    story_name: str
    phase: str  # "discovery", "architecture", "design", etc.
    max_retries: int = 3
    current_attempt: int = 0
    status: IterationStatus = IterationStatus.PENDING
    attempts: List[IterationAttempt] = field(default_factory=list)
    nano_iterations: List[NanoIteration] = field(default_factory=list)
    checkpoint_data: Optional[Dict[str, Any]] = None


@dataclass
class MacroIteration:
    """
    Macro-level iteration (Epic-level).

    Manages multiple story iterations:
    - Story dependency tracking
    - Epic-level rollback
    - Progress checkpointing
    """
    iteration_id: str
    epic_id: str
    epic_name: str
    story_ids: List[str]
    max_retries: int = 3
    current_attempt: int = 0
    status: IterationStatus = IterationStatus.PENDING
    attempts: List[IterationAttempt] = field(default_factory=list)
    micro_iterations: List[MicroIteration] = field(default_factory=list)
    completed_stories: List[str] = field(default_factory=list)
    failed_stories: List[str] = field(default_factory=list)


@dataclass
class IterationResult:
    """Result of an iteration"""
    level: IterationLevel
    iteration_id: str
    status: IterationStatus
    total_attempts: int
    successful: bool
    final_attempt: Optional[IterationAttempt] = None
    error_summary: Optional[str] = None
    recovery_actions: List[str] = field(default_factory=list)


@dataclass
class IterationConfig:
    """Configuration for iteration control"""
    max_nano_retries: int = 3
    max_micro_retries: int = 3
    max_macro_retries: int = 3
    enable_auto_rollback: bool = True
    enable_checkpoint: bool = True
    retry_delay_seconds: float = 1.0
    exponential_backoff: bool = True
    backoff_multiplier: float = 2.0
    max_retry_delay_seconds: float = 60.0


@dataclass
class IterationMetrics:
    """Metrics for iteration performance"""
    total_iterations: int
    successful_iterations: int
    failed_iterations: int
    average_attempts: float
    total_retry_time_seconds: float
    success_rate: float
    most_common_failure: Optional[FailureReason] = None


@dataclass
class RecoveryAction:
    """Describes a recovery action to take after failure"""
    action_type: str  # "rollback", "retry", "skip", "manual_intervention"
    description: str
    automated: bool
    parameters: Dict[str, Any] = field(default_factory=dict)
