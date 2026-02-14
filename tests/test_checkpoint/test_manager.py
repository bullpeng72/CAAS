"""
Unit tests for CheckpointManager

Tests human checkpoint workflow management.

Part of CAAS-E Week 5 implementation (Task 5.3).
"""

import json
import pytest
from pathlib import Path
from datetime import datetime

from caas_framework.checkpoint.manager import CheckpointManager
from caas_framework.models.checkpoint import (
    ApprovalStatus,
    CheckpointPhase,
    CheckpointResult,
    SEVEN_CHECKPOINTS,
)


@pytest.fixture
def temp_checkpoint_dir(tmp_path):
    """Create temporary checkpoint directory."""
    checkpoint_dir = tmp_path / "checkpoints"
    checkpoint_dir.mkdir()
    return checkpoint_dir


@pytest.fixture
def manager(temp_checkpoint_dir):
    """Create CheckpointManager instance."""
    return CheckpointManager(
        project_name="test_project",
        checkpoint_dir=temp_checkpoint_dir,
        enable_auto_approve=False,
        strict_mode=False,
    )


@pytest.fixture
def manager_strict(temp_checkpoint_dir):
    """Create CheckpointManager with strict mode."""
    return CheckpointManager(
        project_name="test_project",
        checkpoint_dir=temp_checkpoint_dir,
        enable_auto_approve=False,
        strict_mode=True,
    )


@pytest.fixture
def manager_auto_approve(temp_checkpoint_dir):
    """Create CheckpointManager with auto-approve enabled."""
    return CheckpointManager(
        project_name="test_project",
        checkpoint_dir=temp_checkpoint_dir,
        enable_auto_approve=True,
        strict_mode=False,
    )


class TestCheckpointManagerInitialization:
    """Test CheckpointManager initialization."""

    def test_initialization(self, manager, temp_checkpoint_dir):
        """Test basic initialization."""
        assert manager.project_name == "test_project"
        assert manager.checkpoint_dir == temp_checkpoint_dir
        assert manager.enable_auto_approve is False
        assert manager.strict_mode is False
        assert len(manager.checkpoint_defs) == 7

    def test_checkpoint_definitions_loaded(self, manager):
        """Test that 7 checkpoints are loaded."""
        assert len(manager.checkpoint_defs) == 7

        # Verify all expected checkpoints are present
        expected_ids = [
            "checkpoint_1",
            "checkpoint_2",
            "checkpoint_3",
            "checkpoint_4",
            "checkpoint_5",
            "checkpoint_6",
            "checkpoint_7",
        ]
        for cp_id in expected_ids:
            assert cp_id in manager.checkpoint_defs

    def test_session_creation(self, manager):
        """Test that a new session is created."""
        assert manager.session is not None
        assert manager.session.project_name == "test_project"
        assert len(manager.session.checkpoints) == 0

    def test_checkpoint_directory_created(self, temp_checkpoint_dir):
        """Test that checkpoint directory is created."""
        assert temp_checkpoint_dir.exists()
        assert temp_checkpoint_dir.is_dir()


class TestSubmitForReview:
    """Test checkpoint submission for review."""

    def test_submit_basic(self, manager):
        """Test basic checkpoint submission."""
        result = manager.submit_for_review(
            phase=CheckpointPhase.CONCRETIZATION,
        )

        assert result.checkpoint_id == "checkpoint_1"
        assert result.phase == CheckpointPhase.CONCRETIZATION
        assert result.status == ApprovalStatus.PENDING

    def test_submit_with_artifact(self, manager, tmp_path):
        """Test checkpoint submission with artifact."""
        artifact_path = tmp_path / "golden_data.json"
        artifact_path.write_text('{"test": "data"}')

        result = manager.submit_for_review(
            phase=CheckpointPhase.CONCRETIZATION,
            artifact_path=artifact_path,
            artifact_metadata={"features_count": 10},
        )

        assert result.checkpoint_id == "checkpoint_1"
        assert result.artifact_path == str(artifact_path)
        assert result.artifact_metadata["features_count"] == 10

    def test_submit_with_quality_score(self, manager):
        """Test checkpoint submission with quality score."""
        result = manager.submit_for_review(
            phase=CheckpointPhase.CONCRETIZATION,
            quality_score=0.85,  # 0-1 scale (85%)
        )

        assert result.overall_score == 0.85
        assert result.status == ApprovalStatus.PENDING

    def test_auto_approve_when_threshold_met(self, manager_auto_approve):
        """Test auto-approval when quality score meets threshold."""
        # checkpoint_1 has auto_approve_threshold=0.9 (90%)
        result = manager_auto_approve.submit_for_review(
            phase=CheckpointPhase.CONCRETIZATION,
            quality_score=0.92,  # Score of 0.92 (92%) >= 0.9 (90%)
        )

        assert result.status == ApprovalStatus.APPROVED
        assert result.reviewer == "auto_approve"
        assert len(result.comments) == 1
        assert "Auto-approved" in result.comments[0].comment

    def test_no_auto_approve_when_threshold_not_met(self, manager_auto_approve):
        """Test no auto-approval when quality score below threshold."""
        result = manager_auto_approve.submit_for_review(
            phase=CheckpointPhase.CONCRETIZATION,
            quality_score=0.75,  # Score of 0.75 (75%) < 0.9 (90%)
        )

        assert result.status == ApprovalStatus.PENDING

    def test_submit_invalid_phase(self, manager):
        """Test submission with invalid phase (no checkpoint defined)."""
        # Create a phase that doesn't map to any checkpoint
        # This should raise ValueError
        with pytest.raises(ValueError, match="No checkpoint defined for phase"):
            manager.submit_for_review(
                phase="invalid_phase",  # Invalid phase
            )


class TestApproveCheckpoint:
    """Test checkpoint approval."""

    def test_approve_basic(self, manager):
        """Test basic checkpoint approval."""
        # First submit for review
        manager.submit_for_review(phase=CheckpointPhase.CONCRETIZATION)

        # Then approve
        result = manager.approve(
            checkpoint_id="checkpoint_1",
            reviewer="john_doe",
        )

        assert result.status == ApprovalStatus.APPROVED
        assert result.reviewer == "john_doe"
        assert result.approval_timestamp is not None

    def test_approve_with_comments(self, manager):
        """Test approval with comments."""
        manager.submit_for_review(phase=CheckpointPhase.CONCRETIZATION)

        result = manager.approve(
            checkpoint_id="checkpoint_1",
            reviewer="jane_smith",
            comments=["Looks good", "Well documented"],
        )

        assert result.status == ApprovalStatus.APPROVED
        assert len(result.comments) == 2
        assert result.comments[0].comment == "Looks good"
        assert result.comments[1].comment == "Well documented"

    def test_approve_with_criteria_scores(self, manager):
        """Test approval with criteria scores."""
        manager.submit_for_review(phase=CheckpointPhase.CONCRETIZATION)

        criteria_scores = {
            "completeness": 9.0,
            "clarity": 8.5,
            "consistency": 9.5,
        }

        result = manager.approve(
            checkpoint_id="checkpoint_1",
            reviewer="john_doe",
            criteria_scores=criteria_scores,
        )

        assert result.criteria_scores == criteria_scores
        assert result.overall_score == sum(criteria_scores.values()) / len(
            criteria_scores
        )  # 9.0

    def test_approve_nonexistent_checkpoint(self, manager):
        """Test approving a checkpoint that doesn't exist."""
        with pytest.raises(ValueError, match="not found in session"):
            manager.approve(
                checkpoint_id="nonexistent",
                reviewer="john_doe",
            )


class TestRejectCheckpoint:
    """Test checkpoint rejection."""

    def test_reject_basic(self, manager):
        """Test basic checkpoint rejection."""
        manager.submit_for_review(phase=CheckpointPhase.CONCRETIZATION)

        result = manager.reject(
            checkpoint_id="checkpoint_1",
            reviewer="john_doe",
            required_changes=["Add missing features", "Fix ambiguities"],
        )

        assert result.status == ApprovalStatus.REJECTED
        assert result.reviewer == "john_doe"
        assert len(result.required_changes) == 2
        assert "Add missing features" in result.required_changes

    def test_reject_with_comments(self, manager):
        """Test rejection with additional comments."""
        manager.submit_for_review(phase=CheckpointPhase.CONCRETIZATION)

        result = manager.reject(
            checkpoint_id="checkpoint_1",
            reviewer="jane_smith",
            required_changes=["Improve documentation"],
            comments=["This needs significant work", "See attached notes"],
        )

        assert result.status == ApprovalStatus.REJECTED
        assert len(result.comments) == 2
        assert result.comments[0].severity == "error"


class TestRequestChanges:
    """Test checkpoint change requests."""

    def test_request_changes_basic(self, manager):
        """Test basic change request."""
        manager.submit_for_review(phase=CheckpointPhase.CONCRETIZATION)

        result = manager.request_changes(
            checkpoint_id="checkpoint_1",
            reviewer="john_doe",
            required_changes=["Add test cases", "Update documentation"],
        )

        assert result.status == ApprovalStatus.CHANGES_REQUESTED
        assert len(result.required_changes) == 2

    def test_request_changes_with_suggestions(self, manager):
        """Test change request with suggestions."""
        manager.submit_for_review(phase=CheckpointPhase.CONCRETIZATION)

        result = manager.request_changes(
            checkpoint_id="checkpoint_1",
            reviewer="jane_smith",
            required_changes=["Fix bug"],
            suggestions=["Consider using pattern X", "Check library Y"],
        )

        assert len(result.suggestions) == 2
        assert "Consider using pattern X" in result.suggestions


class TestCanProceedToNextPhase:
    """Test workflow progression checks."""

    def test_can_proceed_when_approved(self, manager):
        """Test can proceed when checkpoint is approved."""
        manager.submit_for_review(phase=CheckpointPhase.CONCRETIZATION)
        manager.approve(checkpoint_id="checkpoint_1", reviewer="john_doe")

        can_proceed = manager.can_proceed_to_next_phase(
            CheckpointPhase.CONCRETIZATION
        )
        assert can_proceed is True

    def test_can_proceed_when_pending_non_strict(self, manager):
        """Test cannot proceed when pending (required checkpoint blocks regardless of strict mode)."""
        manager.submit_for_review(phase=CheckpointPhase.CONCRETIZATION)

        # Once a required checkpoint is submitted, it blocks until approved,
        # even in non-strict mode. strict_mode only affects whether submission is required.
        can_proceed = manager.can_proceed_to_next_phase(
            CheckpointPhase.CONCRETIZATION
        )
        assert can_proceed is False

    def test_cannot_proceed_when_pending_strict(self, manager_strict):
        """Test cannot proceed when pending in strict mode."""
        manager_strict.submit_for_review(phase=CheckpointPhase.CONCRETIZATION)

        # In strict mode, pending checkpoints block
        can_proceed = manager_strict.can_proceed_to_next_phase(
            CheckpointPhase.CONCRETIZATION
        )
        assert can_proceed is False

    def test_cannot_proceed_when_rejected(self, manager):
        """Test cannot proceed when checkpoint is rejected."""
        manager.submit_for_review(phase=CheckpointPhase.CONCRETIZATION)
        manager.reject(
            checkpoint_id="checkpoint_1",
            reviewer="john_doe",
            required_changes=["Fix issues"],
        )

        can_proceed = manager.can_proceed_to_next_phase(
            CheckpointPhase.CONCRETIZATION
        )
        assert can_proceed is False


class TestSessionPersistence:
    """Test checkpoint session save/load."""

    def test_save_session(self, manager, temp_checkpoint_dir):
        """Test session is saved to disk."""
        manager.submit_for_review(phase=CheckpointPhase.CONCRETIZATION)
        manager.save_session()

        session_file = temp_checkpoint_dir / "test_project_session.json"
        assert session_file.exists()

        # Load and verify
        with open(session_file, "r") as f:
            data = json.load(f)
        assert data["project_name"] == "test_project"
        assert len(data["checkpoints"]) == 1

    def test_load_existing_session(self, temp_checkpoint_dir):
        """Test loading existing session from disk."""
        # Create first manager and submit checkpoint
        manager1 = CheckpointManager(
            project_name="test_project",
            checkpoint_dir=temp_checkpoint_dir,
        )
        manager1.submit_for_review(phase=CheckpointPhase.CONCRETIZATION)
        manager1.approve(checkpoint_id="checkpoint_1", reviewer="john_doe")
        manager1.save_session()

        # Create second manager - should load existing session
        manager2 = CheckpointManager(
            project_name="test_project",
            checkpoint_dir=temp_checkpoint_dir,
        )

        # Verify session was loaded
        assert len(manager2.session.checkpoints) == 1
        result = manager2.session.checkpoints["checkpoint_1"]
        assert result.status == ApprovalStatus.APPROVED
        assert result.reviewer == "john_doe"

    def test_reset_session(self, manager):
        """Test session reset."""
        # Create some checkpoints
        manager.submit_for_review(phase=CheckpointPhase.CONCRETIZATION)
        manager.approve(checkpoint_id="checkpoint_1", reviewer="john_doe")

        # Reset
        manager.reset_session()

        # Verify session is empty
        assert len(manager.session.checkpoints) == 0


class TestCheckpointSummary:
    """Test checkpoint summary reporting."""

    def test_summary_with_no_checkpoints(self, manager):
        """Test summary when no checkpoints submitted."""
        summary = manager.get_checkpoint_summary()

        assert summary["total"] == 0
        assert summary["approved"] == 0
        assert summary["pending"] == 0
        assert summary["rejected"] == 0
        assert summary["completion_rate"] == 0.0

    def test_summary_with_mixed_checkpoints(self, manager):
        """Test summary with various checkpoint states."""
        # Submit 3 checkpoints
        manager.submit_for_review(phase=CheckpointPhase.CONCRETIZATION)
        manager.submit_for_review(phase=CheckpointPhase.DISCOVERY)
        manager.submit_for_review(phase=CheckpointPhase.ARCHITECTURE)

        # Approve first
        manager.approve(checkpoint_id="checkpoint_1", reviewer="john_doe")

        # Reject second
        manager.reject(
            checkpoint_id="checkpoint_2",
            reviewer="jane_smith",
            required_changes=["Fix issues"],
        )

        # Leave third pending

        summary = manager.get_checkpoint_summary()

        assert summary["total"] == 3
        assert summary["approved"] == 1
        assert summary["pending"] == 1
        assert summary["rejected"] == 1
        assert summary["completion_rate"] == 1 / 3  # Only approved counts


class TestGetPendingCheckpoints:
    """Test retrieval of pending checkpoints."""

    def test_get_pending_checkpoints(self, manager):
        """Test getting pending checkpoints."""
        # Submit 3 checkpoints
        manager.submit_for_review(phase=CheckpointPhase.CONCRETIZATION)
        manager.submit_for_review(phase=CheckpointPhase.DISCOVERY)
        manager.submit_for_review(phase=CheckpointPhase.ARCHITECTURE)

        # Approve one
        manager.approve(checkpoint_id="checkpoint_1", reviewer="john_doe")

        # Get pending
        pending = manager.get_pending_checkpoints()

        assert len(pending) == 2
        assert all(cp.status == ApprovalStatus.PENDING for cp in pending)
