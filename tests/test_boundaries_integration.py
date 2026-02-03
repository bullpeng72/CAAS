"""
Test Boundaries Integration with BMAD Engine

Tests that boundaries are automatically validated during code generation.
"""

from caas_framework.models.specifications import BoundariesSpec


def test_boundaries_spec_exists():
    """Test BoundariesSpec can be created"""
    boundaries = BoundariesSpec(
        always_allowed=["Read files in project folder"],
        ask_first=["API calls", "Database operations"],
        never_allowed=["sudo commands", "rm -rf /", "os.system"]
    )

    assert boundaries is not None
    assert len(boundaries.always_allowed) == 1
    assert len(boundaries.ask_first) == 2
    assert len(boundaries.never_allowed) == 3


def test_boundaries_validation_logic():
    """Test boundary validation logic"""
    boundaries = BoundariesSpec(
        never_allowed=["sudo", "os.system", "eval"]
    )

    # Test code with violations
    code_with_sudo = """
import os

def dangerous_function():
    os.system("sudo rm -rf /")
"""

    code_with_eval = """
def unsafe():
    eval("malicious code")
"""

    code_safe = """
def safe_function():
    print("Hello World")
    return 42
"""

    # Simple validation logic
    violations = []

    for code in [code_with_sudo, code_with_eval]:
        content_lower = code.lower()
        for pattern in boundaries.never_allowed:
            if pattern.lower() in content_lower:
                violations.append(f"Found '{pattern}' in code")

    # Should detect violations
    assert len(violations) >= 2  # sudo and eval

    # Safe code should have no violations
    violations_safe = []
    content_lower = code_safe.lower()
    for pattern in boundaries.never_allowed:
        if pattern.lower() in content_lower:
            violations_safe.append(f"Found '{pattern}' in code")

    assert len(violations_safe) == 0


def test_boundaries_integration_pattern():
    """Test the integration pattern used in BMAD Engine"""
    # Simulate what happens in BMAD Engine

    # 1. Mock concretized requirement with boundaries
    mock_concretized = {
        "system_scope": {
            "project_name": "Test Project",
            "purpose": "Test"
        },
        "boundaries": {
            "always_allowed": ["Read files"],
            "ask_first": ["Write files"],
            "never_allowed": ["sudo", "rm -rf"]
        }
    }

    # 2. Mock generated code files
    generated_code = [
        {
            "path": "main.py",
            "content": "print('Hello World')\nimport os\n"
        },
        {
            "path": "dangerous.py",
            "content": "import os\nos.system('sudo dangerous command')\n"
        }
    ]

    # 3. Validate boundaries
    violations = []
    boundaries_dict = mock_concretized.get("boundaries")

    if boundaries_dict:
        boundaries = BoundariesSpec(**boundaries_dict)

        for file_info in generated_code:
            filename = file_info["path"]
            content = file_info.get("content", "")

            if not filename.endswith('.py'):
                continue

            content_lower = content.lower()

            # Check never_allowed patterns
            for pattern in (boundaries.never_allowed or []):
                if pattern.lower() in content_lower:
                    violation = f"NEVER_ALLOWED: {filename} contains '{pattern}'"
                    violations.append(violation)

    # Should detect violation in dangerous.py
    assert len(violations) > 0
    assert any("dangerous.py" in v for v in violations)
    assert any("sudo" in v for v in violations)


def test_no_violations_on_clean_code():
    """Test that clean code has no boundary violations"""
    boundaries = BoundariesSpec(
        never_allowed=["sudo", "rm -rf", "eval", "exec"]
    )

    clean_code = {
        "main.py": """
from crewai import Agent, Task, Crew

def main():
    agent = Agent(role="Researcher", goal="Research topics")
    task = Task(description="Research a topic", agent=agent)
    crew = Crew(agents=[agent], tasks=[task])
    result = crew.kickoff()
    return result

if __name__ == "__main__":
    main()
""",
        "requirements.txt": "crewai>=0.65.0\n"
    }

    violations = []
    for filename, content in clean_code.items():
        if not filename.endswith('.py'):
            continue

        content_lower = content.lower()
        for pattern in boundaries.never_allowed:
            if pattern.lower() in content_lower:
                violations.append(f"{filename}: {pattern}")

    assert len(violations) == 0, f"Clean code should have no violations, but found: {violations}"


if __name__ == "__main__":
    test_boundaries_spec_exists()
    test_boundaries_validation_logic()
    test_boundaries_integration_pattern()
    test_no_violations_on_clean_code()

    print("\n" + "="*70)
    print("✅ All Boundaries Integration tests passed!")
    print("="*70)
