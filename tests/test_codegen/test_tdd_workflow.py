"""
Integration Tests for TDD Workflow

Tests for test-driven code generation workflow (Task 4.2).
"""

import pytest
from pathlib import Path
from caas_framework.codegen.test_parser import TestParser, ParsedTestFile
from caas_framework.codegen.test_driven_generator import TestDrivenCodeGenerator
from caas_framework.codegen.tdd_orchestrator import TDDOrchestrator, TDDWorkflowConfig


class TestTestParser:
    """Test Test Parser functionality."""

    def test_parse_simple_test_file(self, tmp_path):
        """Test parsing a simple test file."""
        # Create a simple test file
        test_file = tmp_path / "test_example.py"
        test_file.write_text("""
def test_addition():
    \"\"\"Test basic addition.\"\"\"
    assert 1 + 1 == 2

def test_subtraction():
    \"\"\"Test basic subtraction.\"\"\"
    assert 5 - 3 == 2
""")

        parser = TestParser()
        parsed = parser.parse_test_file(test_file)

        assert isinstance(parsed, ParsedTestFile)
        assert len(parsed.test_functions) == 2
        assert parsed.test_functions[0].name == "test_addition"
        assert len(parsed.test_functions[0].assertions) == 1

    def test_extract_fixtures(self, tmp_path):
        """Test extracting pytest fixtures."""
        test_file = tmp_path / "test_fixtures.py"
        test_file.write_text("""
import pytest

@pytest.fixture
def sample_data():
    return {"key": "value"}

def test_with_fixture(sample_data):
    assert sample_data["key"] == "value"
""")

        parser = TestParser()
        parsed = parser.parse_test_file(test_file)

        assert len(parsed.fixtures) == 1
        assert parsed.fixtures[0].name == "sample_data"
        assert len(parsed.test_functions) == 1
        assert "sample_data" in parsed.test_functions[0].fixtures

    def test_extract_assertions(self, tmp_path):
        """Test extracting different types of assertions."""
        test_file = tmp_path / "test_assertions.py"
        test_file.write_text("""
def test_various_assertions():
    assert True
    assert 1 == 1
    assert "a" in "abc"
""")

        parser = TestParser()
        parsed = parser.parse_test_file(test_file)

        test_func = parsed.test_functions[0]
        assert len(test_func.assertions) == 3
        assert test_func.assertions[0].type == "truthy"
        assert test_func.assertions[1].type == "equal"
        assert test_func.assertions[2].type == "in"


class TestTDDWorkflowConfig:
    """Test TDD Workflow Configuration."""

    def test_default_config(self):
        """Test default configuration."""
        config = TDDWorkflowConfig()

        assert config.max_iterations == 3
        assert config.timeout_per_test == 30
        assert config.require_all_tests_pass is True

    def test_custom_config(self):
        """Test custom configuration."""
        config = TDDWorkflowConfig(
            max_iterations=5,
            timeout_per_test=60,
            require_all_tests_pass=False,
        )

        assert config.max_iterations == 5
        assert config.timeout_per_test == 60
        assert config.require_all_tests_pass is False


# Note: Full integration tests with LLM would require actual API calls
# These are basic unit tests. For E2E testing, use manual testing or mocked LLM.
