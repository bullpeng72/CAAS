"""
Checkpoint Models for Human Review

Data models for CAAS-E Human Checkpoint workflow.
7 checkpoints with approval/rejection workflow.

Part of CAAS-E Week 5 implementation (Task 5.3).
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field


class CheckpointPhase(str, Enum):
    """Checkpoint phases aligned with CAAS 6-Phase Methodology."""

    CONCRETIZATION = "concretization"  # Checkpoint 1: After Golden Data
    DISCOVERY = "discovery"  # Checkpoint 2: After Requirements Analysis
    ARCHITECTURE = "architecture"  # Checkpoint 3: After System Architecture
    DESIGN = "design"  # Checkpoint 4: After Agent/Task Design
    MEASUREMENT = "measurement"  # Checkpoint 5: After Spec Generation
    DELIVERY = "delivery"  # Checkpoint 6: After Code Generation
    QUALITY_ASSURANCE = "quality_assurance"  # Checkpoint 7: After Final QA


class ApprovalStatus(str, Enum):
    """Approval status for checkpoints."""

    PENDING = "pending"  # Awaiting human review
    APPROVED = "approved"  # Approved by human
    REJECTED = "rejected"  # Rejected - needs rework
    CHANGES_REQUESTED = "changes_requested"  # Changes requested
    SKIPPED = "skipped"  # Checkpoint skipped (optional)


class CheckpointCriteria(BaseModel):
    """Criteria for checkpoint evaluation."""

    name: str = Field(description="Criterion name")
    description: str = Field(description="What to check")
    required: bool = Field(default=True, description="Is this criterion required?")
    weight: float = Field(default=1.0, ge=0.0, le=1.0, description="Criterion weight")


class CheckpointDefinition(BaseModel):
    """Definition of a checkpoint."""

    id: str = Field(description="Checkpoint ID (e.g., 'checkpoint_1')")
    phase: CheckpointPhase = Field(description="Associated CAAS phase")
    name: str = Field(description="Checkpoint name")
    description: str = Field(description="What this checkpoint reviews")
    criteria: List[CheckpointCriteria] = Field(
        default_factory=list, description="Evaluation criteria"
    )
    required: bool = Field(default=True, description="Is this checkpoint mandatory?")
    auto_approve_threshold: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Auto-approve if quality score >= threshold",
    )


class CheckpointReviewComment(BaseModel):
    """A review comment for a checkpoint."""

    criterion_id: Optional[str] = Field(
        default=None, description="Related criterion ID"
    )
    comment: str = Field(description="Review comment")
    severity: str = Field(
        default="info", description="Severity: info, warning, error, critical"
    )
    timestamp: datetime = Field(default_factory=datetime.now)


class CheckpointResult(BaseModel):
    """Result of a checkpoint review."""

    checkpoint_id: str = Field(description="Checkpoint ID")
    phase: CheckpointPhase = Field(description="CAAS phase")
    status: ApprovalStatus = Field(
        default=ApprovalStatus.PENDING, description="Approval status"
    )
    reviewer: Optional[str] = Field(default=None, description="Reviewer name/ID")
    reviewed_at: Optional[datetime] = Field(
        default=None, description="Review timestamp"
    )
    approval_timestamp: Optional[datetime] = Field(
        default=None, description="Approval timestamp"
    )

    # Review details
    comments: List[CheckpointReviewComment] = Field(
        default_factory=list, description="Review comments"
    )
    criteria_scores: Dict[str, float] = Field(
        default_factory=dict, description="Scores per criterion (0.0-1.0)"
    )
    overall_score: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="Overall quality score"
    )

    # Artifact reference
    artifact_path: Optional[str] = Field(
        default=None, description="Path to reviewed artifact"
    )
    artifact_metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Artifact metadata"
    )

    # Action items
    required_changes: List[str] = Field(
        default_factory=list, description="Required changes before approval"
    )
    suggestions: List[str] = Field(
        default_factory=list, description="Optional suggestions"
    )


class CheckpointSession(BaseModel):
    """A checkpoint review session tracking all checkpoints."""

    session_id: str = Field(description="Unique session ID")
    project_name: str = Field(description="Project name")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    checkpoints: Dict[str, CheckpointResult] = Field(
        default_factory=dict, description="Checkpoint results by ID"
    )

    # Session metadata
    enable_auto_approve: bool = Field(
        default=False, description="Enable auto-approval based on thresholds"
    )
    strict_mode: bool = Field(
        default=True, description="Require all mandatory checkpoints"
    )

    @property
    def total_checkpoints(self) -> int:
        """Total number of checkpoints."""
        return len(self.checkpoints)

    @property
    def approved_count(self) -> int:
        """Number of approved checkpoints."""
        return sum(
            1
            for cp in self.checkpoints.values()
            if cp.status == ApprovalStatus.APPROVED
        )

    @property
    def pending_count(self) -> int:
        """Number of pending checkpoints."""
        return sum(
            1
            for cp in self.checkpoints.values()
            if cp.status == ApprovalStatus.PENDING
        )

    @property
    def rejected_count(self) -> int:
        """Number of rejected checkpoints."""
        return sum(
            1
            for cp in self.checkpoints.values()
            if cp.status == ApprovalStatus.REJECTED
        )

    @property
    def all_approved(self) -> bool:
        """Check if all checkpoints are approved."""
        return all(
            cp.status == ApprovalStatus.APPROVED for cp in self.checkpoints.values()
        )

    @property
    def completion_rate(self) -> float:
        """Completion rate (approved / total)."""
        if not self.checkpoints:
            return 0.0
        return self.approved_count / self.total_checkpoints


# Predefined 7 Checkpoints for CAAS-E
SEVEN_CHECKPOINTS: List[CheckpointDefinition] = [
    CheckpointDefinition(
        id="checkpoint_1",
        phase=CheckpointPhase.CONCRETIZATION,
        name="Golden Data Review",
        description="Review completeness and clarity of Golden Data specification",
        criteria=[
            CheckpointCriteria(
                name="completeness",
                description="All required fields present (features, scope, NFRs)",
                required=True,
                weight=0.3,
            ),
            CheckpointCriteria(
                name="clarity",
                description="Requirements are clear and unambiguous",
                required=True,
                weight=0.25,
            ),
            CheckpointCriteria(
                name="testability",
                description="Test scenarios are well-defined",
                required=True,
                weight=0.25,
            ),
            CheckpointCriteria(
                name="feasibility",
                description="Requirements are technically feasible",
                required=True,
                weight=0.2,
            ),
        ],
        required=True,
        auto_approve_threshold=0.9,
    ),
    CheckpointDefinition(
        id="checkpoint_2",
        phase=CheckpointPhase.DISCOVERY,
        name="Requirements Analysis Review",
        description="Review requirement analysis and domain classification",
        criteria=[
            CheckpointCriteria(
                name="domain_classification",
                description="Correct domain identified",
                required=True,
                weight=0.3,
            ),
            CheckpointCriteria(
                name="feature_extraction",
                description="All features correctly identified",
                required=True,
                weight=0.35,
            ),
            CheckpointCriteria(
                name="traceability",
                description="Features traceable to requirements",
                required=True,
                weight=0.35,
            ),
        ],
        required=True,
        auto_approve_threshold=0.85,
    ),
    CheckpointDefinition(
        id="checkpoint_3",
        phase=CheckpointPhase.ARCHITECTURE,
        name="System Architecture Review",
        description="Review system architecture and component design",
        criteria=[
            CheckpointCriteria(
                name="architecture_soundness",
                description="Architecture is well-designed and scalable",
                required=True,
                weight=0.3,
            ),
            CheckpointCriteria(
                name="component_boundaries",
                description="Clear component boundaries and interfaces",
                required=True,
                weight=0.25,
            ),
            CheckpointCriteria(
                name="dependencies",
                description="Dependencies are well-managed",
                required=True,
                weight=0.25,
            ),
            CheckpointCriteria(
                name="security_design",
                description="Security considerations addressed",
                required=True,
                weight=0.2,
            ),
        ],
        required=True,
        auto_approve_threshold=0.85,
    ),
    CheckpointDefinition(
        id="checkpoint_4",
        phase=CheckpointPhase.DESIGN,
        name="Agent/Task Design Review",
        description="Review CrewAI agent and task specifications",
        criteria=[
            CheckpointCriteria(
                name="agent_roles",
                description="Agent roles are clear and well-defined",
                required=True,
                weight=0.25,
            ),
            CheckpointCriteria(
                name="task_definitions",
                description="Tasks have clear descriptions and expected outputs",
                required=True,
                weight=0.25,
            ),
            CheckpointCriteria(
                name="tool_assignments",
                description="Tools are correctly assigned to agents",
                required=True,
                weight=0.2,
            ),
            CheckpointCriteria(
                name="delegation_strategy",
                description="Delegation and collaboration strategy is sound",
                required=True,
                weight=0.15,
            ),
            CheckpointCriteria(
                name="completeness_check",
                description="All features covered by agents/tasks",
                required=True,
                weight=0.15,
            ),
        ],
        required=True,
        auto_approve_threshold=0.8,
    ),
    CheckpointDefinition(
        id="checkpoint_5",
        phase=CheckpointPhase.MEASUREMENT,
        name="Specification Review",
        description="Review generated specifications (YAML/JSON)",
        criteria=[
            CheckpointCriteria(
                name="spec_completeness",
                description="All specs generated (agents, tasks, tools, models)",
                required=True,
                weight=0.3,
            ),
            CheckpointCriteria(
                name="spec_validity",
                description="Specs are valid and well-formed",
                required=True,
                weight=0.35,
            ),
            CheckpointCriteria(
                name="sdd_compliance",
                description="Specs follow SDD (Spec-Driven Development) format",
                required=True,
                weight=0.35,
            ),
        ],
        required=True,
        auto_approve_threshold=0.9,
    ),
    CheckpointDefinition(
        id="checkpoint_6",
        phase=CheckpointPhase.DELIVERY,
        name="Code Generation Review",
        description="Review generated production code",
        criteria=[
            CheckpointCriteria(
                name="code_quality",
                description="Code quality meets standards (≥8.0/10)",
                required=True,
                weight=0.25,
            ),
            CheckpointCriteria(
                name="test_coverage",
                description="Test coverage is adequate (≥80%)",
                required=True,
                weight=0.2,
            ),
            CheckpointCriteria(
                name="functionality",
                description="Code implements required functionality",
                required=True,
                weight=0.3,
            ),
            CheckpointCriteria(
                name="best_practices",
                description="Follows Python/CrewAI best practices",
                required=True,
                weight=0.15,
            ),
            CheckpointCriteria(
                name="documentation",
                description="Code is well-documented",
                required=True,
                weight=0.1,
            ),
        ],
        required=True,
        auto_approve_threshold=0.8,
    ),
    CheckpointDefinition(
        id="checkpoint_7",
        phase=CheckpointPhase.QUALITY_ASSURANCE,
        name="Final QA Review",
        description="Final quality assurance before production",
        criteria=[
            CheckpointCriteria(
                name="all_tests_pass",
                description="All tests passing (100%)",
                required=True,
                weight=0.3,
            ),
            CheckpointCriteria(
                name="security_scan",
                description="Security scan passed (no critical issues)",
                required=True,
                weight=0.25,
            ),
            CheckpointCriteria(
                name="deployment_ready",
                description="Deployment artifacts ready",
                required=True,
                weight=0.2,
            ),
            CheckpointCriteria(
                name="documentation_complete",
                description="README and docs complete",
                required=True,
                weight=0.15,
            ),
            CheckpointCriteria(
                name="performance_check",
                description="Performance meets requirements",
                required=False,
                weight=0.1,
            ),
        ],
        required=True,
        auto_approve_threshold=0.9,
    ),
]
