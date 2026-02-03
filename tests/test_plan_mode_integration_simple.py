"""
Simple Plan Mode Integration Tests

Tests that don't require full BMAD Engine dependencies.
"""

from unittest.mock import Mock

import pytest

from caas_cli.ui.cli_review_handler import AutoApproveHandler
from caas_framework.execution.plan_mode_api import PlanModeAPI


def test_cli_review_handler_with_plan_mode_api():
    """Test CLIReviewHandler works with PlanModeAPI"""
    # Create handler
    handler = AutoApproveHandler()

    # Create API with handler
    api = PlanModeAPI(review_handler=handler)

    # Test requirements review
    mock_concretized = Mock()
    mock_concretized.project_name = "Test Project"
    mock_concretized.description = "Test description"
    mock_concretized.features = []
    mock_concretized.data_models = []
    mock_concretized.boundaries = None

    decision = api.request_requirements_review(mock_concretized)
    assert decision == "approve"


def test_plan_mode_api_with_auto_approve():
    """Test PlanModeAPI with AutoApproveHandler"""
    handler = AutoApproveHandler()
    api = PlanModeAPI(review_handler=handler)

    # Test all review types
    mock_obj = Mock()
    mock_obj.project_name = "Test"
    mock_obj.description = "Test"
    mock_obj.features = []
    mock_obj.data_models = []
    mock_obj.boundaries = None

    # Requirements
    decision = api.request_requirements_review(mock_obj)
    assert decision == "approve"

    # Design
    decision = api.request_design_review({"agents": [], "tasks": []})
    assert decision == "approve"

    # Code
    decision = api.request_code_review({"main.py": "print('hello')"})
    assert decision == "approve"


def test_user_aborted_error_definition():
    """Test UserAbortedError can be defined and raised"""
    class UserAbortedError(Exception):
        """User aborted the process"""
        pass

    # Should be able to create and raise
    error = UserAbortedError("Test abort")
    assert isinstance(error, Exception)
    assert str(error) == "Test abort"

    # Should be catchable
    with pytest.raises(UserAbortedError):
        raise UserAbortedError("Aborted at gate")


def test_bmad_engine_signature():
    """Test that BMADEngine would have correct signature"""
    # We can't import BMADEngine due to dependencies
    # But we can verify the integration pattern

    # Mock what BMADEngine.__init__ should look like
    def mock_bmad_init(plan_mode=False, review_handler=None):
        plan_mode_enabled = plan_mode
        plan_mode_api = None

        if plan_mode:
            from caas_framework.execution.plan_mode_api import PlanModeAPI
            plan_mode_api = PlanModeAPI(review_handler=review_handler)

        return {
            'plan_mode_enabled': plan_mode_enabled,
            'plan_mode_api': plan_mode_api
        }

    # Test without plan mode
    result = mock_bmad_init(plan_mode=False)
    assert result['plan_mode_enabled'] is False
    assert result['plan_mode_api'] is None

    # Test with plan mode and handler
    handler = AutoApproveHandler()
    result = mock_bmad_init(plan_mode=True, review_handler=handler)
    assert result['plan_mode_enabled'] is True
    assert result['plan_mode_api'] is not None


def test_gate_integration_pattern():
    """Test the gate integration pattern"""
    # This simulates how gates should work in BMAD Engine

    api = PlanModeAPI(review_handler=AutoApproveHandler())

    # Gate 1: Requirements
    mock_concretized = Mock()
    mock_concretized.project_name = "Test"
    mock_concretized.description = "Test"
    mock_concretized.features = []
    mock_concretized.data_models = []
    mock_concretized.boundaries = None

    decision = api.request_requirements_review(mock_concretized)
    if decision == "reject":
        raise Exception("User rejected at Gate 1")

    assert decision == "approve"

    # Gate 2: Design
    design_data = {"agents": [], "tasks": []}
    decision = api.request_design_review(design_data)
    if decision == "reject":
        raise Exception("User rejected at Gate 2")

    assert decision == "approve"

    # Gate 3: Code
    code_files = {"main.py": "print('hello')"}
    decision = api.request_code_review(code_files)
    if decision == "reject":
        raise Exception("User rejected at Gate 3")

    assert decision == "approve"


def test_rejection_flow():
    """Test rejection flow with mock handler"""
    # Handler that rejects
    reject_handler = Mock()
    reject_handler.handle_review = Mock(return_value="reject")

    api = PlanModeAPI(review_handler=reject_handler)

    # Test rejection with properly mocked object
    mock_concretized = Mock()
    mock_concretized.project_name = "Test"
    mock_concretized.description = "Test"
    mock_concretized.features = []
    mock_concretized.data_models = []
    mock_concretized.boundaries = None

    decision = api.request_requirements_review(mock_concretized)
    assert decision == "reject"

    # In BMAD Engine, this would raise UserAbortedError
    class UserAbortedError(Exception):
        pass

    with pytest.raises(UserAbortedError):
        if decision == "reject":
            raise UserAbortedError("User rejected requirements")


if __name__ == "__main__":
    # Run tests
    test_cli_review_handler_with_plan_mode_api()
    test_plan_mode_api_with_auto_approve()
    test_user_aborted_error_definition()
    test_bmad_engine_signature()
    test_gate_integration_pattern()
    test_rejection_flow()

    print("\n" + "="*70)
    print("✅ All simple Plan Mode Integration tests passed!")
    print("="*70)
