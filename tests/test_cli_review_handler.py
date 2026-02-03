"""
Test CLI Review Handler

Tests for CLI-based review handler implementation.
"""

from unittest.mock import patch

from rich.console import Console

from caas_cli.ui.cli_review_handler import AutoApproveHandler, CLIReviewHandler
from caas_framework.api import ReviewRequest, ReviewType


def test_cli_review_handler_creation():
    """Test CLIReviewHandler can be created"""
    handler = CLIReviewHandler()
    assert handler is not None
    assert handler.console is not None


def test_cli_review_handler_with_custom_console():
    """Test CLIReviewHandler with custom console"""
    console = Console()
    handler = CLIReviewHandler(console=console)
    assert handler.console is console


def test_requirements_review_display():
    """Test requirements review display (no user input)"""
    handler = CLIReviewHandler()

    # Mock data
    data = {
        "project_name": "Test Project",
        "description": "A test project",
        "features": [
            {"name": "Feature 1", "description": "First feature", "priority": "high"},
            {
                "name": "Feature 2",
                "description": "Second feature",
                "priority": "medium",
            },
        ],
        "data_models": [{"name": "User", "attributes_count": 5}],
        "boundaries": {
            "always_allowed": ["Read files"],
            "ask_first": ["API calls"],
            "never_allowed": ["sudo commands"],
        },
    }

    # Test display method (should not raise)
    try:
        handler._display_requirements_review(data)
        success = True
    except Exception as e:
        success = False
        print(f"Error: {e}")

    assert success, "Requirements review display should not raise exception"


def test_design_review_display():
    """Test design review display"""
    handler = CLIReviewHandler()

    data = {
        "agents": [
            {
                "id": "agent1",
                "role": "Researcher",
                "goal": "Research topics",
                "tools": ["web_search", "calculator"],
            }
        ],
        "tasks": [
            {"id": "task1", "description": "Research a topic", "agent": "agent1"}
        ],
    }

    # Test display method
    try:
        handler._display_design_review(data)
        success = True
    except Exception:
        success = False

    assert success, "Design review display should not raise exception"


def test_code_review_display():
    """Test code review display"""
    handler = CLIReviewHandler()

    data = {
        "total_files": 2,
        "total_lines": 150,
        "files": {
            "main.py": {
                "lines": 100,
                "size_kb": 3.5,
                "preview": 'def main():\n    print("Hello")\n',
            },
            "requirements.txt": {"lines": 50, "size_kb": 1.2, "preview": None},
        },
    }

    # Test display method
    try:
        handler._display_code_review(data)
        success = True
    except Exception:
        success = False

    assert success, "Code review display should not raise exception"


def test_display_boundaries():
    """Test security boundaries display"""
    handler = CLIReviewHandler()

    boundaries = {
        "always_allowed": ["Read files", "Write to project folder"],
        "ask_first": ["API calls", "Database operations"],
        "never_allowed": ["sudo commands", "Delete system files"],
    }

    # Test display method
    try:
        handler._display_boundaries(boundaries)
        success = True
    except Exception:
        success = False

    assert success, "Boundaries display should not raise exception"


def test_get_user_decision_approve():
    """Test getting user decision - approve"""
    handler = CLIReviewHandler()

    with patch("builtins.input", return_value="approve"):
        decision = handler._get_user_decision(["approve", "edit", "reject"])
        assert decision == "approve"


def test_get_user_decision_reject():
    """Test getting user decision - reject"""
    handler = CLIReviewHandler()

    with patch("builtins.input", return_value="reject"):
        decision = handler._get_user_decision(["approve", "reject"])
        assert decision == "reject"


def test_get_user_decision_invalid_then_valid():
    """Test getting user decision - invalid input then valid"""
    handler = CLIReviewHandler()

    # Mock input: first invalid, then valid
    with patch("builtins.input", side_effect=["invalid", "wrong", "approve"]):
        decision = handler._get_user_decision(["approve", "reject"])
        assert decision == "approve"


def test_get_user_decision_keyboard_interrupt():
    """Test getting user decision - keyboard interrupt"""
    handler = CLIReviewHandler()

    with patch("builtins.input", side_effect=KeyboardInterrupt()):
        decision = handler._get_user_decision(["approve", "reject"])
        assert decision == "reject"  # Should return reject on interrupt


def test_handle_review_requirements():
    """Test full handle_review for requirements"""
    handler = CLIReviewHandler()

    request = ReviewRequest(
        review_type=ReviewType.REQUIREMENTS,
        data={"project_name": "Test", "description": "Test project", "features": []},
        options=["approve", "edit", "reject"],
    )

    with patch("builtins.input", return_value="approve"):
        decision = handler.handle_review(request)
        assert decision == "approve"


def test_handle_review_design():
    """Test full handle_review for design"""
    handler = CLIReviewHandler()

    request = ReviewRequest(
        review_type=ReviewType.DESIGN,
        data={"agents": [], "tasks": []},
        options=["approve", "redesign", "reject"],
    )

    with patch("builtins.input", return_value="approve"):
        decision = handler.handle_review(request)
        assert decision == "approve"


def test_handle_review_code():
    """Test full handle_review for code"""
    handler = CLIReviewHandler()

    request = ReviewRequest(
        review_type=ReviewType.CODE,
        data={"total_files": 1, "total_lines": 10, "files": {}},
        options=["approve", "reject"],
    )

    with patch("builtins.input", return_value="approve"):
        decision = handler.handle_review(request)
        assert decision == "approve"


def test_auto_approve_handler_creation():
    """Test AutoApproveHandler creation"""
    handler = AutoApproveHandler()
    assert handler is not None


def test_auto_approve_handler_always_approves():
    """Test AutoApproveHandler always returns approve"""
    handler = AutoApproveHandler()

    request = ReviewRequest(
        review_type=ReviewType.REQUIREMENTS,
        data={"project_name": "Test"},
        options=["approve", "reject"],
    )

    decision = handler.handle_review(request)
    assert decision == "approve"


def test_auto_approve_handler_all_review_types():
    """Test AutoApproveHandler works for all review types"""
    handler = AutoApproveHandler()

    for review_type in [ReviewType.REQUIREMENTS, ReviewType.DESIGN, ReviewType.CODE]:
        request = ReviewRequest(
            review_type=review_type, data={}, options=["approve", "reject"]
        )

        decision = handler.handle_review(request)
        assert decision == "approve"


if __name__ == "__main__":
    # Run basic tests
    test_cli_review_handler_creation()
    test_requirements_review_display()
    test_design_review_display()
    test_code_review_display()
    test_display_boundaries()
    test_auto_approve_handler_creation()
    test_auto_approve_handler_always_approves()

    print("\n" + "=" * 70)
    print("✅ All CLI Review Handler tests passed!")
    print("=" * 70)
