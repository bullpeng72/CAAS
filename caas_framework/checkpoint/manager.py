"""
Checkpoint Manager

Manages human review checkpoints in CAAS-E workflow.

Part of CAAS-E Week 5 implementation (Task 5.3).
"""

import json
import uuid
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from caas_framework.models.checkpoint import (
    ApprovalStatus,
    CheckpointDefinition,
    CheckpointPhase,
    CheckpointResult,
    CheckpointReviewComment,
    CheckpointSession,
    SEVEN_CHECKPOINTS,
)
from caas_framework.utils.logger import get_logger


class CheckpointManager:
    """
    Manages human checkpoint workflow for CAAS-E.

    Features:
    - Create and track checkpoint sessions
    - Submit artifacts for review
    - Approve/reject/request changes
    - Auto-approve based on quality thresholds
    - Save/load checkpoint state
    """

    def __init__(
        self,
        project_name: str,
        checkpoint_dir: Optional[Path] = None,
        enable_auto_approve: bool = False,
        strict_mode: bool = True,
    ):
        """
        Initialize Checkpoint Manager.

        Args:
            project_name: Project name
            checkpoint_dir: Directory to save checkpoint state
            enable_auto_approve: Enable auto-approval based on thresholds
            strict_mode: Require all mandatory checkpoints
        """
        self.project_name = project_name
        self.checkpoint_dir = checkpoint_dir or Path("./checkpoints")
        self.enable_auto_approve = enable_auto_approve
        self.strict_mode = strict_mode
        self.logger = get_logger(__name__)

        # Create checkpoint directory
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        # Load or create session
        self.session = self._load_or_create_session()

        # Load checkpoint definitions
        self.checkpoint_defs: Dict[str, CheckpointDefinition] = {
            cp.id: cp for cp in SEVEN_CHECKPOINTS
        }

    def _load_or_create_session(self) -> CheckpointSession:
        """Load existing session or create new one."""
        session_file = self.checkpoint_dir / f"{self.project_name}_session.json"

        if session_file.exists():
            self.logger.info(f"Loading checkpoint session from {session_file}")
            with open(session_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return CheckpointSession(**data)
        else:
            self.logger.info(f"Creating new checkpoint session for {self.project_name}")
            return CheckpointSession(
                session_id=str(uuid.uuid4()),
                project_name=self.project_name,
                enable_auto_approve=self.enable_auto_approve,
                strict_mode=self.strict_mode,
            )

    def save_session(self):
        """Save checkpoint session to disk."""
        session_file = self.checkpoint_dir / f"{self.project_name}_session.json"

        self.session.updated_at = datetime.now()

        with open(session_file, 'w', encoding='utf-8') as f:
            json.dump(self.session.model_dump(), f, indent=2, default=str)

        self.logger.info(f"Saved checkpoint session to {session_file}")

    def submit_for_review(
        self,
        phase: CheckpointPhase,
        artifact_path: Optional[Path] = None,
        artifact_metadata: Optional[Dict] = None,
        quality_score: Optional[float] = None,
    ) -> CheckpointResult:
        """
        Submit artifact for checkpoint review.

        Args:
            phase: Checkpoint phase
            artifact_path: Path to artifact (optional)
            artifact_metadata: Artifact metadata (optional)
            quality_score: Quality score for auto-approval (optional)

        Returns:
            CheckpointResult
        """
        # Find checkpoint definition for this phase
        checkpoint_def = self._get_checkpoint_for_phase(phase)

        if not checkpoint_def:
            raise ValueError(f"No checkpoint defined for phase {phase}")

        self.logger.info(f"Submitting for review: {checkpoint_def.name} ({phase.value})")

        # Create checkpoint result
        result = CheckpointResult(
            checkpoint_id=checkpoint_def.id,
            phase=phase,
            status=ApprovalStatus.PENDING,
            artifact_path=str(artifact_path) if artifact_path else None,
            artifact_metadata=artifact_metadata or {},
            overall_score=quality_score,
        )

        # Auto-approve if enabled and threshold met
        if (
            self.enable_auto_approve
            and checkpoint_def.auto_approve_threshold is not None
            and quality_score is not None
            and quality_score >= checkpoint_def.auto_approve_threshold
        ):
            self.logger.info(
                f"Auto-approving {checkpoint_def.name}: "
                f"score {quality_score:.2f} >= {checkpoint_def.auto_approve_threshold:.2f}"
            )
            result.status = ApprovalStatus.APPROVED
            result.approval_timestamp = datetime.now()
            result.reviewer = "auto_approve"
            result.comments.append(
                CheckpointReviewComment(
                    comment=f"Auto-approved (quality score: {quality_score:.2f})",
                    severity="info",
                )
            )

        # Add to session
        self.session.checkpoints[checkpoint_def.id] = result
        self.save_session()

        return result

    def approve(
        self,
        checkpoint_id: str,
        reviewer: str,
        comments: Optional[List[str]] = None,
        criteria_scores: Optional[Dict[str, float]] = None,
    ) -> CheckpointResult:
        """
        Approve a checkpoint.

        Args:
            checkpoint_id: Checkpoint ID
            reviewer: Reviewer name/ID
            comments: Review comments (optional)
            criteria_scores: Scores per criterion (optional)

        Returns:
            Updated CheckpointResult
        """
        if checkpoint_id not in self.session.checkpoints:
            raise ValueError(f"Checkpoint {checkpoint_id} not found in session")

        result = self.session.checkpoints[checkpoint_id]

        self.logger.info(f"Approving checkpoint: {checkpoint_id} by {reviewer}")

        result.status = ApprovalStatus.APPROVED
        result.reviewer = reviewer
        result.reviewed_at = datetime.now()
        result.approval_timestamp = datetime.now()

        if criteria_scores:
            result.criteria_scores = criteria_scores
            result.overall_score = sum(criteria_scores.values()) / len(criteria_scores)

        if comments:
            for comment in comments:
                result.comments.append(
                    CheckpointReviewComment(comment=comment, severity="info")
                )

        self.save_session()

        return result

    def reject(
        self,
        checkpoint_id: str,
        reviewer: str,
        required_changes: List[str],
        comments: Optional[List[str]] = None,
    ) -> CheckpointResult:
        """
        Reject a checkpoint and request changes.

        Args:
            checkpoint_id: Checkpoint ID
            reviewer: Reviewer name/ID
            required_changes: List of required changes
            comments: Additional comments (optional)

        Returns:
            Updated CheckpointResult
        """
        if checkpoint_id not in self.session.checkpoints:
            raise ValueError(f"Checkpoint {checkpoint_id} not found in session")

        result = self.session.checkpoints[checkpoint_id]

        self.logger.info(f"Rejecting checkpoint: {checkpoint_id} by {reviewer}")

        result.status = ApprovalStatus.REJECTED
        result.reviewer = reviewer
        result.reviewed_at = datetime.now()
        result.required_changes = required_changes

        if comments:
            for comment in comments:
                result.comments.append(
                    CheckpointReviewComment(comment=comment, severity="error")
                )

        self.save_session()

        return result

    def request_changes(
        self,
        checkpoint_id: str,
        reviewer: str,
        required_changes: List[str],
        suggestions: Optional[List[str]] = None,
        comments: Optional[List[str]] = None,
    ) -> CheckpointResult:
        """
        Request changes for a checkpoint.

        Args:
            checkpoint_id: Checkpoint ID
            reviewer: Reviewer name/ID
            required_changes: List of required changes
            suggestions: Optional suggestions
            comments: Additional comments (optional)

        Returns:
            Updated CheckpointResult
        """
        if checkpoint_id not in self.session.checkpoints:
            raise ValueError(f"Checkpoint {checkpoint_id} not found in session")

        result = self.session.checkpoints[checkpoint_id]

        self.logger.info(f"Requesting changes for checkpoint: {checkpoint_id} by {reviewer}")

        result.status = ApprovalStatus.CHANGES_REQUESTED
        result.reviewer = reviewer
        result.reviewed_at = datetime.now()
        result.required_changes = required_changes
        result.suggestions = suggestions or []

        if comments:
            for comment in comments:
                result.comments.append(
                    CheckpointReviewComment(comment=comment, severity="warning")
                )

        self.save_session()

        return result

    def get_checkpoint_status(self, checkpoint_id: str) -> Optional[CheckpointResult]:
        """Get status of a specific checkpoint."""
        return self.session.checkpoints.get(checkpoint_id)

    def get_pending_checkpoints(self) -> List[CheckpointResult]:
        """Get all pending checkpoints."""
        return [
            cp
            for cp in self.session.checkpoints.values()
            if cp.status == ApprovalStatus.PENDING
        ]

    def get_checkpoint_summary(self) -> Dict:
        """Get summary of all checkpoints."""
        return {
            "total": self.session.total_checkpoints,
            "approved": self.session.approved_count,
            "pending": self.session.pending_count,
            "rejected": self.session.rejected_count,
            "completion_rate": self.session.completion_rate,
            "all_approved": self.session.all_approved,
        }

    def can_proceed_to_next_phase(self, current_phase: CheckpointPhase) -> bool:
        """
        Check if workflow can proceed to next phase.

        Args:
            current_phase: Current checkpoint phase

        Returns:
            True if checkpoint is approved or skipped, False otherwise
        """
        checkpoint_def = self._get_checkpoint_for_phase(current_phase)

        if not checkpoint_def:
            return True  # No checkpoint for this phase

        if checkpoint_def.id not in self.session.checkpoints:
            if self.strict_mode and checkpoint_def.required:
                return False  # Strict mode: checkpoint must be submitted
            return True  # Non-strict: can proceed

        result = self.session.checkpoints[checkpoint_def.id]

        if result.status in [ApprovalStatus.APPROVED, ApprovalStatus.SKIPPED]:
            return True

        if not checkpoint_def.required:
            return True  # Optional checkpoint can be bypassed

        return False

    def _get_checkpoint_for_phase(self, phase: CheckpointPhase) -> Optional[CheckpointDefinition]:
        """Get checkpoint definition for a specific phase."""
        for cp_def in self.checkpoint_defs.values():
            if cp_def.phase == phase:
                return cp_def
        return None

    def reset_session(self):
        """Reset checkpoint session (clear all checkpoints)."""
        self.logger.warning(f"Resetting checkpoint session for {self.project_name}")

        self.session = CheckpointSession(
            session_id=str(uuid.uuid4()),
            project_name=self.project_name,
            enable_auto_approve=self.enable_auto_approve,
            strict_mode=self.strict_mode,
        )

        self.save_session()
