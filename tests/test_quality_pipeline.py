"""
Test Code Quality Pipeline (Phase 1 - P1)

Verifies that:
1. Syntax check detects syntax errors
2. Import check validates imports
3. Code style check detects style issues
4. Overall pipeline runs successfully
"""

from caas_framework.quality.pipeline import (
    CheckStatus,
    CodeQualityPipeline,
    CodeStyleCheck,
    ImportCheck,
    SyntaxCheck,
)


def test_syntax_check_valid_code():
    """Test syntax check with valid Python code."""
    check = SyntaxCheck()

    files = {
        "main.py": """
from crewai import Crew, Agent, Task

def main():
    agent = Agent(role="Helper", goal="Help users")
    print("Running...")
"""
    }

    result = check.check(files)

    assert result.status == CheckStatus.PASSED
    assert len(result.errors) == 0


def test_syntax_check_invalid_code():
    """Test syntax check with invalid Python code."""
    check = SyntaxCheck()

    files = {
        "main.py": """
def broken_function(
    # Missing closing parenthesis
    print("This won't parse")
"""
    }

    result = check.check(files)

    assert result.status == CheckStatus.FAILED
    assert len(result.errors) > 0
    assert "main.py" in result.errors[0]


def test_import_check_standard_library():
    """Test import check with standard library imports."""
    check = ImportCheck()

    files = {
        "main.py": """
import os
import sys
import json
from typing import Dict, List
from datetime import datetime
"""
    }

    result = check.check(files)

    # Should pass (standard library imports)
    assert result.status == CheckStatus.PASSED
    assert len(result.errors) == 0


def test_import_check_third_party():
    """Test import check with third-party imports."""
    check = ImportCheck()

    files = {
        "main.py": """
from crewai import Crew, Agent
import langchain
"""
    }

    result = check.check(files)

    # Should pass with warnings (third-party but expected)
    assert result.status == CheckStatus.PASSED
    # Warnings are expected for third-party modules
    # (but we skip crewai and langchain)


def test_code_style_check_line_length():
    """Test code style check for line length."""
    check = CodeStyleCheck()

    # Create a very long line
    long_line = "x = " + "1" * 150

    files = {
        "main.py": f"""
def function():
    {long_line}
"""
    }

    result = check.check(files)

    # Should have warnings about line length
    assert len(result.warnings) > 0
    assert "Line too long" in result.warnings[0]


def test_code_style_check_wildcard_import():
    """Test code style check for wildcard imports."""
    check = CodeStyleCheck()

    files = {
        "main.py": """
from module import *
"""
    }

    result = check.check(files)

    # Should warn about wildcard import
    assert len(result.warnings) > 0
    assert "Wildcard import" in result.warnings[0]


def test_quality_pipeline_all_checks():
    """Test full quality pipeline with all checks."""
    pipeline = CodeQualityPipeline(
        enable_syntax=True, enable_imports=True, enable_style=True
    )

    # Good quality code
    files = {
        "main.py": """
from crewai import Crew, Agent, Task

def main():
    agent = Agent(role="Helper", goal="Help users")
    crew = Crew(agents=[agent], tasks=[])
    result = crew.kickoff()
    return result
""",
        "requirements.txt": "crewai>=0.65.0\n",
    }

    report = pipeline.verify(files)

    assert report.overall_passed is True
    assert report.files_checked == 2
    assert report.total_errors == 0
    assert len(report.checks) == 3  # syntax, imports, style


def test_quality_pipeline_with_errors():
    """Test quality pipeline with code that has errors."""
    pipeline = CodeQualityPipeline()

    # Code with syntax error
    files = {
        "main.py": """
def broken(
    print("Missing closing paren")
"""
    }

    report = pipeline.verify(files)

    assert report.overall_passed is False
    assert report.total_errors > 0


def test_quality_pipeline_report_format():
    """Test quality report formatting."""
    pipeline = CodeQualityPipeline()

    files = {"main.py": "print('Hello')\n"}

    report = pipeline.verify(files)

    # Test report to dict conversion
    report_dict = report.to_dict()

    assert "overall_passed" in report_dict
    assert "timestamp" in report_dict
    assert "checks" in report_dict
    assert isinstance(report_dict["checks"], list)


def test_quality_pipeline_selective_checks():
    """Test pipeline with selective checks enabled."""

    # Only syntax check
    pipeline = CodeQualityPipeline(
        enable_syntax=True, enable_imports=False, enable_style=False
    )

    files = {"main.py": "print('test')\n"}
    report = pipeline.verify(files)

    assert len(report.checks) == 1
    assert report.checks[0].name == "Syntax Check"


if __name__ == "__main__":
    test_syntax_check_valid_code()
    test_syntax_check_invalid_code()
    test_import_check_standard_library()
    test_import_check_third_party()
    test_code_style_check_line_length()
    test_code_style_check_wildcard_import()
    test_quality_pipeline_all_checks()
    test_quality_pipeline_with_errors()
    test_quality_pipeline_report_format()
    test_quality_pipeline_selective_checks()

    print("\n" + "=" * 70)
    print("✅ All Quality Pipeline tests passed!")
    print("=" * 70)
    print("\nSummary:")
    print("- Syntax Check: ✅ Detects syntax errors correctly")
    print("- Import Check: ✅ Validates imports (stdlib + third-party)")
    print("- Code Style Check: ✅ Detects line length and wildcard imports")
    print("- Full Pipeline: ✅ Runs all checks successfully")
    print("- Error Detection: ✅ Correctly identifies code quality issues")
    print("- Report Format: ✅ Generates structured quality reports")
    print("\n🎉 Phase 1 - Task #5 (P1) COMPLETE: Quality pipeline added!")
