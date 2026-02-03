"""
Test UI Independence (Phase 1.5)

Verifies that:
1. Framework API is UI-independent
2. PlanModeAPI works without UI
3. Multiple UI implementations can use the same API
4. No direct print() or input() in Framework core
"""

from caas_framework.api.interfaces import EventData, ReviewRequest, ReviewType
from caas_framework.execution.plan_mode_api import PlanModeAPI
from caas_framework.models.specifications import (
    ConcretizedRequirement,
    FeatureSpec,
    SystemScope,
)


class MockReviewHandler:
    """Mock review handler for testing"""

    def __init__(self, decision: str = "approve"):
        self.decision = decision
        self.requests_received = []

    def handle_review(self, request: ReviewRequest) -> str:
        """Record request and return predetermined decision"""
        self.requests_received.append(request)
        return self.decision


class MockUICallback:
    """Mock UI callback for testing"""

    def __init__(self):
        self.events_received = []

    def on_event(self, event: EventData) -> None:
        """Record events"""
        self.events_received.append(event)


def test_plan_mode_api_without_ui():
    """Test PlanModeAPI works without UI (auto-approve)"""

    # Create API without handler (headless mode)
    api = PlanModeAPI(review_handler=None)

    # Create mock requirements
    concretized = ConcretizedRequirement(
        system_scope=SystemScope(project_name="Test", purpose="Test project"),
        features=[
            FeatureSpec(
                id="f1", name="Feature 1", description="Test feature", priority="high"
            )
        ],
    )

    # Should auto-approve
    decision = api.request_requirements_review(concretized)
    assert decision == "approve"


def test_plan_mode_api_with_custom_handler():
    """Test PlanModeAPI with custom review handler"""

    # Create mock handler that rejects
    handler = MockReviewHandler(decision="reject")

    # Create API with handler
    api = PlanModeAPI(review_handler=handler)

    # Create mock requirements
    concretized = ConcretizedRequirement(
        system_scope=SystemScope(project_name="Test", purpose="Test project")
    )

    # Request review
    decision = api.request_requirements_review(concretized)

    # Should use handler's decision
    assert decision == "reject"

    # Handler should have received request
    assert len(handler.requests_received) == 1
    request = handler.requests_received[0]
    assert request.review_type == ReviewType.REQUIREMENTS
    assert request.data["project_name"] == "Test"


def test_design_review_ui_independent():
    """Test design review with UI-independent data"""

    handler = MockReviewHandler(decision="approve")
    api = PlanModeAPI(review_handler=handler)

    # Mock design output
    design = {
        "agents": [
            {
                "id": "agent1",
                "role": "Researcher",
                "goal": "Research topics",
                "tools": ["web_search"],
            }
        ],
        "tasks": [
            {"id": "task1", "description": "Research a topic", "agent": "agent1"}
        ],
    }

    # Request review
    decision = api.request_design_review(design)

    assert decision == "approve"

    # Check request data structure
    request = handler.requests_received[0]
    assert request.review_type == ReviewType.DESIGN
    assert len(request.data["agents"]) == 1
    assert len(request.data["tasks"]) == 1
    assert request.data["agents"][0]["id"] == "agent1"


def test_code_review_ui_independent():
    """Test code review with UI-independent data"""

    handler = MockReviewHandler(decision="approve")
    api = PlanModeAPI(review_handler=handler)

    # Mock generated files
    files = {"main.py": "print('Hello')\n" * 20, "requirements.txt": "crewai>=0.65.0\n"}

    # Request review
    decision = api.request_code_review(files)

    assert decision == "approve"

    # Check request data structure
    request = handler.requests_received[0]
    assert request.review_type == ReviewType.CODE
    assert request.data["total_files"] == 2
    assert "main.py" in request.data["files"]
    assert request.data["files"]["main.py"]["lines"] == 21  # 20 newlines + 1


def test_multiple_ui_implementations():
    """Test that multiple UIs can use the same API"""

    # Simulate CLI handler
    class CLIHandler:
        def handle_review(self, request: ReviewRequest) -> str:
            # CLI would use print/input here
            return "approve"

    # Simulate Streamlit handler
    class StreamlitHandler:
        def handle_review(self, request: ReviewRequest) -> str:
            # Streamlit would use st.radio here
            return "approve"

    # Simulate VSCode Extension handler
    class VSCodeHandler:
        def handle_review(self, request: ReviewRequest) -> str:
            # VSCode would show quick pick here
            return "approve"

    # All can use the same PlanModeAPI
    concretized = ConcretizedRequirement(
        system_scope=SystemScope(project_name="Test", purpose="Test")
    )

    for handler_class in [CLIHandler, StreamlitHandler, VSCodeHandler]:
        handler = handler_class()
        api = PlanModeAPI(review_handler=handler)
        decision = api.request_requirements_review(concretized)
        assert decision == "approve"


def test_ui_independent_data_structure():
    """Test that data structure is truly UI-independent"""

    handler = MockReviewHandler()
    api = PlanModeAPI(review_handler=handler)

    concretized = ConcretizedRequirement(
        system_scope=SystemScope(project_name="My Project", purpose="My Purpose"),
        features=[
            FeatureSpec(
                id="f1", name="Auth", description="User authentication", priority="high"
            ),
            FeatureSpec(
                id="f2", name="Posts", description="Post management", priority="medium"
            ),
        ],
    )

    api.request_requirements_review(concretized)

    request = handler.requests_received[0]
    data = request.data

    # Data should be simple dicts/lists (UI-independent)
    assert isinstance(data, dict)
    assert isinstance(data["features"], list)
    assert len(data["features"]) == 2

    # Features should be simple dicts
    feature = data["features"][0]
    assert isinstance(feature, dict)
    assert feature["name"] == "Auth"
    assert feature["priority"] == "high"

    # No Pydantic objects or complex types
    assert not hasattr(data, "model_dump")


def test_no_ui_dependencies_in_framework():
    """Test that framework core has no UI dependencies"""

    # PlanModeAPI should not import or use:
    # - input()
    # - print()
    # - sys.stdin/stdout
    # - CLI-specific libraries

    import inspect

    from caas_framework.execution import plan_mode_api

    source = inspect.getsource(plan_mode_api)

    # Check for prohibited UI operations
    prohibited = ["input(", "print(", "sys.stdin", "sys.stdout"]

    for item in prohibited:
        assert item not in source, f"PlanModeAPI should not use {item} (UI-dependent)"


if __name__ == "__main__":
    test_plan_mode_api_without_ui()
    test_plan_mode_api_with_custom_handler()
    test_design_review_ui_independent()
    test_code_review_ui_independent()
    test_multiple_ui_implementations()
    test_ui_independent_data_structure()
    test_no_ui_dependencies_in_framework()

    print("\n" + "=" * 70)
    print("✅ All UI Independence tests passed!")
    print("=" * 70)
    print("\nSummary:")
    print("- PlanModeAPI: ✅ UI-independent (no print/input)")
    print("- Auto-approve: ✅ Works without UI (headless mode)")
    print("- Custom Handlers: ✅ Multiple UI implementations supported")
    print("- Data Structure: ✅ Simple dicts/lists (UI-independent)")
    print("- Framework Core: ✅ No UI dependencies")
    print("\n🎉 Phase 1.5 COMPLETE: UI Independence achieved!")
    print("\n📌 Now supports:")
    print("  - CLI (via CLIReviewHandler)")
    print("  - Streamlit (via StreamlitReviewHandler)")
    print("  - VSCode Extension (via VSCodeReviewHandler)")
    print("  - Any other UI (implement ReviewHandler)")
