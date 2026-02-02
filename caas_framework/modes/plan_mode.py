"""
Plan Mode - Interactive Approval Gates

Allows users to review and approve each phase before proceeding to the next.
Implements approval gates at critical decision points to catch errors early.

This file provides backward compatibility by wrapping the new Protocol-based
implementation (PlanModeCore + ReviewHandler).
"""

from typing import Any, Dict, Optional

from rich.console import Console

from caas_framework.agents.base import AgentPhase
from caas_framework.modes.interfaces import ApprovalDecision

# Import Protocol-based implementation
from caas_framework.modes.plan_mode_core import ApprovalGate, PlanModeCore

# For backward compatibility, re-export key types
__all__ = ["PlanMode", "PlanModeCore", "ApprovalGate", "ApprovalDecision", "create_plan_mode"]


class PlanMode:
    """
    Plan Mode with Interactive Approval Gates (Backward Compatible Wrapper)

    This class wraps PlanModeCore and automatically uses RichReviewHandler for CLI.
    For UI independence, use PlanModeCore directly with a custom ReviewHandler.

    Implements user review checkpoints at critical phases:
    1. After Discovery (Phase 1) - Review requirements
    2. After Design (Phase 3) - Review agents/tasks
    3. After Delivery (Phase 4) - Review code

    Benefits:
    - Early error detection
    - User control over process
    - Iterative refinement
    - Better alignment with expectations

    Usage:
        # CLI (automatic - uses Rich)
        plan_mode = PlanMode(auto_approve=False)

        # Custom UI (Protocol-based)
        from caas_framework.modes.plan_mode_core import PlanModeCore
        from my_ui.review import MyCustomReviewHandler

        plan_mode_core = PlanModeCore(
            review_handler=MyCustomReviewHandler(),
            auto_approve=False
        )
    """

    def __init__(self, console: Optional[Console] = None, auto_approve: bool = False):
        """
        Initialize Plan Mode with CLI support.

        Args:
            console: Optional rich Console instance (for CLI)
            auto_approve: If True, auto-approve all gates (for testing)
        """
        # Import here to avoid circular dependencies
        from caas_cli.ui.rich_review_handler import RichReviewHandler

        # Create CLI review handler
        review_handler = RichReviewHandler(console=console)

        # Create core with CLI handler
        self.core = PlanModeCore(review_handler=review_handler, auto_approve=auto_approve)

        # For backward compatibility
        self.console = console or Console()
        self.auto_approve = auto_approve

    @property
    def approval_history(self):
        """Get approval history (backward compatibility)."""
        return self.core.approval_history

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
        return self.core.request_approval(
            phase=phase, phase_name=phase_name, description=description, output=output
        )

    def get_approval_summary(self) -> Dict[str, Any]:
        """
        Get summary of all approval decisions.

        Returns:
            Dictionary with approval statistics
        """
        return self.core.get_approval_summary()

    def display_summary(self):
        """Display approval summary."""
        self.core.display_summary()

    def reset_history(self):
        """Reset approval history (useful for testing)."""
        self.core.reset_history()


def create_plan_mode(auto_approve: bool = False, console: Optional[Console] = None) -> PlanMode:
    """
    Factory function to create Plan Mode instance.

    Args:
        auto_approve: Auto-approve all gates (for testing)
        console: Optional Console instance

    Returns:
        PlanMode instance
    """
    return PlanMode(console=console, auto_approve=auto_approve)
