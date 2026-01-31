"""
Test Plan Mode Protocol Implementation

Verifies that Plan Mode Protocol-based implementation works correctly
and can be used with different UI implementations.
"""

import pytest
from typing import Dict, Any, Tuple, Optional

from caas_framework.modes import (
    PlanModeCore,
    ApprovalGate,
    ApprovalDecision,
    ReviewHandler,
    NullReviewHandler,
    PlanMode
)
from caas_framework.agents.base import AgentPhase


class MockReviewHandler:
    """Mock review handler for testing"""

    def __init__(self, decisions: list[ApprovalDecision]):
        """
        Initialize mock handler with predefined decisions.

        Args:
            decisions: List of decisions to return in order
        """
        self.decisions = decisions
        self.decision_index = 0
        self.displayed_outputs = []
        self.summary_displayed = False

    def display_phase_output(
        self,
        phase_name: str,
        description: str,
        output: Dict[str, Any]
    ) -> None:
        """Record that output was displayed"""
        self.displayed_outputs.append({
            'phase_name': phase_name,
            'description': description,
            'output': output
        })

    def request_decision(
        self,
        phase_name: str,
        options: Optional[Dict[str, str]] = None
    ) -> ApprovalDecision:
        """Return predefined decision"""
        decision = self.decisions[self.decision_index]
        self.decision_index = (self.decision_index + 1) % len(self.decisions)
        return decision

    def request_feedback(
        self,
        phase_name: str,
        current_output: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], str]:
        """Return mock feedback"""
        return current_output, "Mock feedback"

    def display_summary(
        self,
        summary_data: Dict[str, Any]
    ) -> None:
        """Record that summary was displayed"""
        self.summary_displayed = True


def test_protocol_implementation():
    """Test that handlers implement the Protocol"""
    # All implementations should have required methods
    null_handler = NullReviewHandler()
    mock_handler = MockReviewHandler([ApprovalDecision.APPROVE])

    assert hasattr(null_handler, 'display_phase_output')
    assert hasattr(null_handler, 'request_decision')
    assert hasattr(null_handler, 'request_feedback')
    assert hasattr(null_handler, 'display_summary')

    assert hasattr(mock_handler, 'display_phase_output')
    assert hasattr(mock_handler, 'request_decision')
    assert hasattr(mock_handler, 'request_feedback')
    assert hasattr(mock_handler, 'display_summary')


def test_plan_mode_core_with_mock_handler():
    """Test PlanModeCore with mock review handler"""
    mock_handler = MockReviewHandler([
        ApprovalDecision.APPROVE,
        ApprovalDecision.REJECT,
        ApprovalDecision.EDIT
    ])

    plan_mode = PlanModeCore(
        review_handler=mock_handler,
        auto_approve=False
    )

    # Test approval
    gate1 = plan_mode.request_approval(
        phase=AgentPhase.DISCOVERY,
        phase_name="Phase 1",
        description="Test phase 1",
        output={"test": "data"}
    )

    assert gate1.decision == ApprovalDecision.APPROVE
    assert len(mock_handler.displayed_outputs) == 1
    assert mock_handler.displayed_outputs[0]['phase_name'] == "Phase 1"

    # Test rejection
    gate2 = plan_mode.request_approval(
        phase=AgentPhase.ARCHITECTURE,
        phase_name="Phase 2",
        description="Test phase 2",
        output={"test": "data2"}
    )

    assert gate2.decision == ApprovalDecision.REJECT
    assert len(mock_handler.displayed_outputs) == 2

    # Test edit (should become APPROVE after editing)
    gate3 = plan_mode.request_approval(
        phase=AgentPhase.DESIGN,
        phase_name="Phase 3",
        description="Test phase 3",
        output={"test": "data3"}
    )

    assert gate3.decision == ApprovalDecision.APPROVE  # Edit becomes approve
    assert gate3.feedback == "Mock feedback"
    assert len(mock_handler.displayed_outputs) == 3


def test_auto_approve():
    """Test auto-approve mode"""
    mock_handler = MockReviewHandler([ApprovalDecision.REJECT])  # Should be ignored

    plan_mode = PlanModeCore(
        review_handler=mock_handler,
        auto_approve=True  # Auto-approve enabled
    )

    gate = plan_mode.request_approval(
        phase=AgentPhase.DISCOVERY,
        phase_name="Phase 1",
        description="Test phase",
        output={"test": "data"}
    )

    # Should be approved despite mock handler returning REJECT
    assert gate.decision == ApprovalDecision.APPROVE
    # Display should be skipped in auto-approve mode
    assert len(mock_handler.displayed_outputs) == 0


def test_approval_summary():
    """Test approval summary generation"""
    mock_handler = MockReviewHandler([
        ApprovalDecision.APPROVE,
        ApprovalDecision.REJECT,
        ApprovalDecision.EDIT,
        ApprovalDecision.SKIP
    ])

    plan_mode = PlanModeCore(
        review_handler=mock_handler,
        auto_approve=False
    )

    # Create multiple gates
    plan_mode.request_approval(AgentPhase.DISCOVERY, "P1", "Test", {"a": 1})
    plan_mode.request_approval(AgentPhase.ARCHITECTURE, "P2", "Test", {"b": 2})
    plan_mode.request_approval(AgentPhase.DESIGN, "P3", "Test", {"c": 3})
    plan_mode.request_approval(AgentPhase.DELIVERY, "P4", "Test", {"d": 4})

    summary = plan_mode.get_approval_summary()

    assert summary['total_gates'] == 4
    assert summary['approved'] == 2  # APPROVE + EDIT (becomes APPROVE)
    assert summary['rejected'] == 1
    assert summary['skipped'] == 1
    assert summary['edited'] == 1  # EDIT gate has feedback
    assert summary['approval_rate'] == 0.5  # 2/4

    # Test summary display
    plan_mode.display_summary()
    assert mock_handler.summary_displayed


def test_backward_compatible_plan_mode():
    """Test backward compatible PlanMode wrapper"""
    # Test that PlanMode still works with auto_approve
    plan_mode = PlanMode(auto_approve=True)

    gate = plan_mode.request_approval(
        phase=AgentPhase.DISCOVERY,
        phase_name="Phase 1",
        description="Test phase",
        output={"test": "data"}
    )

    assert gate.decision == ApprovalDecision.APPROVE
    assert len(plan_mode.approval_history) == 1

    summary = plan_mode.get_approval_summary()
    assert summary['total_gates'] == 1
    assert summary['approved'] == 1


def test_null_review_handler():
    """Test NullReviewHandler auto-approves everything"""
    null_handler = NullReviewHandler()

    # Display methods should do nothing
    null_handler.display_phase_output("Phase", "Description", {"data": "test"})
    null_handler.display_summary({"total": 5})

    # Should always approve
    decision = null_handler.request_decision("Phase 1")
    assert decision == ApprovalDecision.APPROVE

    # Should return original output
    output, feedback = null_handler.request_feedback("Phase 1", {"data": "test"})
    assert output == {"data": "test"}
    assert feedback == ""


def test_protocol_usage():
    """Test that Protocol can be used as type hint"""
    def use_review_handler(handler: ReviewHandler) -> None:
        """Function that accepts any ReviewHandler implementation"""
        handler.display_phase_output("Test", "Description", {"data": 1})
        decision = handler.request_decision("Test")
        assert isinstance(decision, ApprovalDecision)

    # All implementations should work
    null_handler = NullReviewHandler()
    mock_handler = MockReviewHandler([ApprovalDecision.APPROVE])

    use_review_handler(null_handler)
    use_review_handler(mock_handler)


def test_reset_history():
    """Test reset history functionality"""
    plan_mode = PlanModeCore(auto_approve=True)

    plan_mode.request_approval(AgentPhase.DISCOVERY, "P1", "Test", {"a": 1})
    plan_mode.request_approval(AgentPhase.ARCHITECTURE, "P2", "Test", {"b": 2})

    assert len(plan_mode.approval_history) == 2

    plan_mode.reset_history()

    assert len(plan_mode.approval_history) == 0
    summary = plan_mode.get_approval_summary()
    assert summary['total_gates'] == 0


if __name__ == "__main__":
    test_protocol_implementation()
    test_plan_mode_core_with_mock_handler()
    test_auto_approve()
    test_approval_summary()
    test_backward_compatible_plan_mode()
    test_null_review_handler()
    test_protocol_usage()
    test_reset_history()
    print("✅ All Plan Mode Protocol tests passed!")
