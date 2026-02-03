"""
Plan Mode Core - UI-Independent Logic

Contains the core approval gate logic without any UI dependencies.
Works with any ReviewHandler implementation (CLI, Streamlit, VSCode, etc.).
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from caas_framework.agents.base import AgentPhase
from caas_framework.modes.interfaces import (
    ApprovalDecision,
    NullReviewHandler,
    ReviewHandler,
)
from caas_framework.utils.logger import get_logger

logger = get_logger()


@dataclass
class ApprovalGate:
    """
    Approval gate at end of phase.

    Pauses execution and requests user review before proceeding.
    """

    phase: AgentPhase
    phase_name: str
    description: str
    output: Dict[str, Any]
    decision: Optional[ApprovalDecision] = None
    feedback: Optional[str] = None
    edited_output: Optional[Dict[str, Any]] = None


class PlanModeCore:
    """
    Plan Mode Core with Interactive Approval Gates (UI-Independent)

    Implements user review checkpoints at critical phases:
    1. After Discovery (Phase 1) - Review requirements
    2. After Design (Phase 3) - Review agents/tasks
    3. After Delivery (Phase 4) - Review code

    Benefits:
    - Early error detection
    - User control over process
    - Iterative refinement
    - Better alignment with expectations

    This core class is UI-independent and works with any ReviewHandler implementation.
    """

    def __init__(self, review_handler: Optional[ReviewHandler] = None, auto_approve: bool = False):
        """
        Initialize Plan Mode Core.

        Args:
            review_handler: ReviewHandler implementation (Protocol-based)
            auto_approve: If True, auto-approve all gates (for testing)
        """
        self.review_handler = review_handler or NullReviewHandler()
        self.auto_approve = auto_approve
        self.approval_history: List[ApprovalGate] = []

    def request_approval(
        self, phase: AgentPhase, phase_name: str, description: str, output: Dict[str, Any]
    ) -> ApprovalGate:
        """
        Request user approval for phase output.

        Args:
            phase: AgentPhase enum
            phase_name: Display name
            description: What to review
            output: Phase output to review

        Returns:
            ApprovalGate with user decision
        """
        logger.info(f"Requesting approval for {phase_name}")

        # Auto-approve if enabled
        if self.auto_approve:
            gate = ApprovalGate(
                phase=phase,
                phase_name=phase_name,
                description=description,
                output=output,
                decision=ApprovalDecision.APPROVE,
            )
            self.approval_history.append(gate)
            logger.info(f"Auto-approved {phase_name}")
            return gate

        # Display phase output via review handler
        self.review_handler.display_phase_output(
            phase_name=phase_name, description=description, output=output
        )

        # Request decision from user
        decision = self.review_handler.request_decision(phase_name=phase_name)

        # Handle edit request
        edited_output = None
        feedback = None

        if decision == ApprovalDecision.EDIT:
            edited_output, feedback = self.review_handler.request_feedback(
                phase_name=phase_name, current_output=output
            )
            # After edit, consider it approved
            decision = ApprovalDecision.APPROVE
            logger.info(f"{phase_name} approved after editing")

        # Create gate record
        gate = ApprovalGate(
            phase=phase,
            phase_name=phase_name,
            description=description,
            output=output,
            decision=decision,
            feedback=feedback,
            edited_output=edited_output,
        )

        self.approval_history.append(gate)
        logger.info(f"{phase_name} decision: {decision.value}")

        return gate

    def get_approval_summary(self) -> Dict[str, Any]:
        """
        Get summary of all approval decisions.

        Returns:
            Dictionary with approval statistics
        """
        total = len(self.approval_history)
        approved = sum(1 for g in self.approval_history if g.decision == ApprovalDecision.APPROVE)
        rejected = sum(1 for g in self.approval_history if g.decision == ApprovalDecision.REJECT)
        skipped = sum(1 for g in self.approval_history if g.decision == ApprovalDecision.SKIP)
        edited = sum(1 for g in self.approval_history if g.edited_output is not None)

        return {
            "total_gates": total,
            "approved": approved,
            "rejected": rejected,
            "skipped": skipped,
            "edited": edited,
            "approval_rate": approved / total if total > 0 else 0,
            "gates": [
                {
                    "phase": g.phase_name,
                    "decision": g.decision.value if g.decision else "none",
                    "had_edits": g.edited_output is not None,
                    "feedback": g.feedback if g.feedback else None,
                }
                for g in self.approval_history
            ],
        }

    def display_summary(self):
        """Display approval summary via review handler."""
        summary = self.get_approval_summary()
        self.review_handler.display_summary(summary)

    def reset_history(self):
        """Reset approval history (useful for testing)."""
        self.approval_history.clear()
        logger.info("Approval history reset")
