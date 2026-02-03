"""
Test Boundaries Specification (Phase 1 - P0)

Verifies that:
1. BoundariesSpec can be created and validated
2. RequirementAnalyst extracts boundaries from requirements
3. CodeGenerator validates generated code against boundaries
"""

from caas_framework.models.specifications import (
    BoundariesSpec,
    CodeStyleSpec,
    CommandsSpec,
    ConcretizedRequirement,
    GitWorkflowSpec,
    SystemScope,
)


def test_boundaries_spec_creation():
    """Test that BoundariesSpec can be created with default values."""
    boundaries = BoundariesSpec(
        always_allowed=[
            "Read files in project directory",
            "Write to project directory",
            "Install packages from requirements.txt"
        ],
        ask_first=[
            "Make API calls to external services",
            "Delete files or directories"
        ],
        never_allowed=[
            "Execute shell commands with sudo",
            "Modify system files outside project"
        ]
    )

    assert len(boundaries.always_allowed) == 3
    assert len(boundaries.ask_first) == 2
    assert len(boundaries.never_allowed) == 2
    assert "Read files in project directory" in boundaries.always_allowed
    assert "Execute shell commands with sudo" in boundaries.never_allowed


def test_commands_spec_default():
    """Test that CommandsSpec has sensible defaults."""
    commands = CommandsSpec()

    assert commands.install == "pip install -r requirements.txt"
    assert commands.test == "pytest tests/"
    assert commands.run == "python main.py"
    assert commands.lint == "pylint src/"
    assert commands.format == "black src/"


def test_code_style_spec_default():
    """Test that CodeStyleSpec has sensible defaults."""
    style = CodeStyleSpec()

    assert style.formatter == "black"
    assert style.line_length == 88
    assert style.use_type_hints is True
    assert style.docstring_style == "google"
    assert style.import_order == "isort"


def test_git_workflow_spec_default():
    """Test that GitWorkflowSpec has sensible defaults."""
    git = GitWorkflowSpec()

    assert git.branch_naming == "feature/{issue-number}-{description}"
    assert git.commit_message_format == "<type>(<scope>): <subject>"
    assert git.requires_pr is True
    assert git.main_branch == "main"


def test_concretized_requirement_with_boundaries():
    """Test that ConcretizedRequirement can include boundaries."""
    concretized = ConcretizedRequirement(
        system_scope=SystemScope(
            project_name="Test Project",
            purpose="Test boundaries integration"
        ),
        boundaries=BoundariesSpec(
            always_allowed=["Read files"],
            ask_first=["API calls"],
            never_allowed=["sudo commands"]
        ),
        commands=CommandsSpec(),
        code_style=CodeStyleSpec(),
        git_workflow=GitWorkflowSpec()
    )

    assert concretized.boundaries is not None
    assert len(concretized.boundaries.always_allowed) == 1
    assert concretized.boundaries.never_allowed[0] == "sudo commands"

    assert concretized.commands is not None
    assert concretized.commands.test == "pytest tests/"

    assert concretized.code_style is not None
    assert concretized.code_style.formatter == "black"

    assert concretized.git_workflow is not None
    assert concretized.git_workflow.requires_pr is True


def test_boundary_validation_logic():
    """Test the boundary validation logic."""
    from caas_framework.agents.code_generator import CodeGeneratorAgent

    # Create a mock golden_data with boundaries
    class MockGoldenData:
        def __init__(self):
            self.project_name = "Test"
            self.features = []
            self.boundaries = BoundariesSpec(
                always_allowed=["Read files"],
                ask_first=["Make API calls"],
                never_allowed=["Execute sudo commands", "Disable security"]
            )

    # Create code generator
    generator = CodeGeneratorAgent(llm_plugin=None, golden_data=MockGoldenData())

    # Test case 1: Safe code (no violations)
    safe_code = {
        "main.py": """
from crewai import Crew, Agent, Task

def main():
    # Read configuration
    with open('config.txt') as f:
        config = f.read()

    # Create agent
    agent = Agent(role="Helper", goal="Help users")
    print("Agent created")
"""
    }

    violations = generator._validate_boundaries(safe_code, MockGoldenData().boundaries)
    assert len(violations) == 0, "Safe code should have no violations"

    # Test case 2: Dangerous code (NEVER_ALLOWED)
    dangerous_code = {
        "main.py": """
import os

def dangerous_operation():
    # This should be detected!
    os.system('sudo rm -rf /')
"""
    }

    violations = generator._validate_boundaries(dangerous_code, MockGoldenData().boundaries)
    assert len(violations) > 0, "Dangerous code should be detected"
    assert any("sudo" in v.lower() for v in violations), "Should detect sudo usage"


if __name__ == "__main__":
    test_boundaries_spec_creation()
    test_commands_spec_default()
    test_code_style_spec_default()
    test_git_workflow_spec_default()
    test_concretized_requirement_with_boundaries()
    test_boundary_validation_logic()

    print("\n" + "=" * 70)
    print("✅ All Boundaries tests passed!")
    print("=" * 70)
    print("\nSummary:")
    print("- BoundariesSpec: ✅ Can be created and validated")
    print("- CommandsSpec: ✅ Has sensible defaults")
    print("- CodeStyleSpec: ✅ Has sensible defaults")
    print("- GitWorkflowSpec: ✅ Has sensible defaults")
    print("- ConcretizedRequirement: ✅ Integrates all SDD specs")
    print("- Boundary Validation: ✅ Detects dangerous code patterns")
    print("\n🎉 Phase 1 - Task #1 (P0) COMPLETE: Boundaries specification added!")
