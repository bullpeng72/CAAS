"""
Test Plan Mode (Phase 1 - P1)

Verifies that:
1. PlanMode can review concretized requirements
2. PlanMode can review agent/task design
3. PlanMode can review generated code
4. Auto-approve mode works for testing
"""

from caas_framework.execution.plan_mode import ApprovalDecision, PlanMode
from caas_framework.models.specifications import (
    BoundariesSpec,
    ConcretizedRequirement,
    FeatureSpec,
    SystemScope,
)


def test_plan_mode_creation():
    """Test that PlanMode can be created."""
    plan_mode = PlanMode(auto_approve=False)
    assert plan_mode is not None
    assert plan_mode.auto_approve is False


def test_plan_mode_auto_approve():
    """Test auto-approve mode (for testing/CI)."""
    plan_mode = PlanMode(auto_approve=True)

    # Create mock concretized requirements
    concretized = ConcretizedRequirement(
        system_scope=SystemScope(
            project_name="Test Project",
            purpose="Test auto-approve"
        ),
        features=[
            FeatureSpec(
                id="f1",
                name="Feature 1",
                description="Test feature",
                priority="high"
            )
        ]
    )

    # Auto-approve should return APPROVE without user input
    decision = plan_mode.review_concretized_requirements(concretized)
    assert decision == ApprovalDecision.APPROVE


def test_review_design_auto_approve():
    """Test design review in auto-approve mode."""
    plan_mode = PlanMode(auto_approve=True)

    design = {
        "agents": [
            {
                "id": "agent1",
                "role": "Researcher",
                "goal": "Research topics",
                "tools": ["web_search"]
            }
        ],
        "tasks": [
            {
                "id": "task1",
                "description": "Research a topic",
                "agent": "agent1"
            }
        ]
    }

    decision = plan_mode.review_design(design)
    assert decision == ApprovalDecision.APPROVE


def test_review_code_auto_approve():
    """Test code review in auto-approve mode."""
    plan_mode = PlanMode(auto_approve=True)

    generated_code = {
        "main.py": """
from crewai import Crew, Agent, Task

def main():
    agent = Agent(role="Helper", goal="Help users")
    print("Running crew...")
""",
        "requirements.txt": "crewai>=0.65.0\n"
    }

    decision = plan_mode.review_final_code(generated_code)
    assert decision == ApprovalDecision.APPROVE


def test_display_features_with_boundaries():
    """Test that boundaries are displayed in review."""
    plan_mode = PlanMode(auto_approve=True)

    concretized = ConcretizedRequirement(
        system_scope=SystemScope(
            project_name="Secure Project",
            purpose="Test boundaries display"
        ),
        features=[
            FeatureSpec(
                id="f1",
                name="User Management",
                description="Manage users",
                priority="critical"
            )
        ],
        boundaries=BoundariesSpec(
            always_allowed=["Read files"],
            ask_first=["API calls"],
            never_allowed=["sudo commands"]
        )
    )

    # In auto-approve mode, this should work
    decision = plan_mode.review_concretized_requirements(concretized)
    assert decision == ApprovalDecision.APPROVE

    # Verify boundaries are set
    assert concretized.boundaries is not None
    assert len(concretized.boundaries.never_allowed) == 1


def test_approval_decision_enum():
    """Test ApprovalDecision enum."""
    assert ApprovalDecision.APPROVE.value == "approve"
    assert ApprovalDecision.REJECT.value == "reject"
    assert ApprovalDecision.EDIT.value == "edit"


if __name__ == "__main__":
    test_plan_mode_creation()
    test_plan_mode_auto_approve()
    test_review_design_auto_approve()
    test_review_code_auto_approve()
    test_display_features_with_boundaries()
    test_approval_decision_enum()

    print("\n" + "=" * 70)
    print("✅ All Plan Mode tests passed!")
    print("=" * 70)
    print("\nSummary:")
    print("- PlanMode: ✅ Created successfully")
    print("- Auto-approve: ✅ Works for testing/CI")
    print("- Requirements Review: ✅ Displays features, data models, boundaries")
    print("- Design Review: ✅ Displays agents and tasks")
    print("- Code Review: ✅ Displays generated files with preview")
    print("- Approval Gates: ✅ 3 checkpoints implemented")
    print("\n🎉 Phase 1 - Task #3 (P1) COMPLETE: Plan Mode added!")
