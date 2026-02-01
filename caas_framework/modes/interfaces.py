"""
Plan Mode Interfaces

UI-independent interfaces for Plan Mode approval gates.
Allows different UIs (CLI, Streamlit, VSCode) to implement their own review handlers.
"""

from typing import Protocol, Dict, Any, Optional, Tuple
from enum import Enum


class ApprovalDecision(str, Enum):
    """User approval decisions"""
    APPROVE = "approve"
    REJECT = "reject"
    EDIT = "edit"
    SKIP = "skip"


class ReviewHandler(Protocol):
    """
    UI-independent Review Handler Interface

    All UI implementations (CLI, Streamlit, VSCode) must implement this protocol
    to provide phase output review and user decision collection.

    Examples:
        # CLI Implementation
        class RichReviewHandler:
            def display_phase_output(self, phase_name: str, description: str, output: Dict) -> None:
                console.print(Panel(f"{phase_name}: {description}"))

        # Streamlit Implementation
        class StreamlitReviewHandler:
            def display_phase_output(self, phase_name: str, description: str, output: Dict) -> None:
                st.header(phase_name)
                st.json(output)

        # VSCode Implementation
        class VSCodeReviewHandler:
            def display_phase_output(self, phase_name: str, description: str, output: Dict) -> None:
                vscode.window.showInformationMessage(f"{phase_name}: {description}")
    """

    def display_phase_output(
        self,
        phase_name: str,
        description: str,
        output: Dict[str, Any]
    ) -> None:
        """
        Display phase output for user review.

        Args:
            phase_name: Name of the phase (e.g., "Phase 1: Discovery")
            description: Description of what to review
            output: Phase output data to display
        """
        ...

    def request_decision(
        self,
        phase_name: str,
        options: Optional[Dict[str, str]] = None
    ) -> ApprovalDecision:
        """
        Request user decision on phase output.

        Args:
            phase_name: Name of the phase
            options: Optional custom options/descriptions

        Returns:
            User's approval decision
        """
        ...

    def request_feedback(
        self,
        phase_name: str,
        current_output: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], str]:
        """
        Request user feedback for refinement.

        Args:
            phase_name: Name of the phase
            current_output: Current phase output

        Returns:
            Tuple of (edited_output, feedback_text)
        """
        ...

    def display_summary(
        self,
        summary_data: Dict[str, Any]
    ) -> None:
        """
        Display approval gates summary.

        Args:
            summary_data: Summary statistics and gate information
        """
        ...


class NullReviewHandler:
    """
    Null implementation of ReviewHandler.

    Auto-approves everything - useful for testing or when review is disabled.
    """

    def display_phase_output(
        self,
        phase_name: str,
        description: str,
        output: Dict[str, Any]
    ) -> None:
        """Do nothing - null implementation"""

    def request_decision(
        self,
        phase_name: str,
        options: Optional[Dict[str, str]] = None
    ) -> ApprovalDecision:
        """Auto-approve"""
        return ApprovalDecision.APPROVE

    def request_feedback(
        self,
        phase_name: str,
        current_output: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], str]:
        """Return original output with no feedback"""
        return current_output, ""

    def display_summary(
        self,
        summary_data: Dict[str, Any]
    ) -> None:
        """Do nothing - null implementation"""
