"""
Integration tests for analyze-completeness CLI command.

Tests the complete workflow of analyzing implementation completeness
against Golden Data.
"""

import json
import pytest
from pathlib import Path
from click.testing import CliRunner
from unittest.mock import patch, AsyncMock, Mock

from caas_cli.commands.analyze_completeness import analyze_completeness


class TestAnalyzeCompletenessCommand:
    """Integration tests for analyze-completeness command."""

    @pytest.fixture
    def runner(self):
        """CLI runner."""
        return CliRunner()

    @pytest.fixture
    def mock_golden_data(self, tmp_path):
        """Create mock Golden Data file."""
        golden_data = {
            "project_name": "TestProject",
            "domain": "CONVERSATIONAL_AI",
            "system_scope": {
                "project_name": "TestProject",
                "purpose": "Test chatbot",
                "target_users": ["developers"],
            },
            "features": [
                {
                    "id": "feature_1",
                    "name": "User Authentication",
                    "description": "Allow users to log in",
                    "priority": "high",
                    "acceptance_criteria": [
                        "User can log in with username/password",
                        "Invalid credentials show error message",
                    ],
                    "functional_requirements": [],
                    "user_stories": [],
                },
                {
                    "id": "feature_2",
                    "name": "Chat Interface",
                    "description": "Display chat messages",
                    "priority": "medium",
                    "acceptance_criteria": [
                        "Messages display in chronological order",
                    ],
                    "functional_requirements": [],
                    "user_stories": [],
                },
            ],
        }

        golden_file = tmp_path / "golden_data.json"
        golden_file.write_text(json.dumps(golden_data, indent=2))
        return golden_file

    @pytest.fixture
    def mock_project(self, tmp_path):
        """Create mock project directory."""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()

        # Create sample files
        (project_dir / "auth.py").write_text("""
def login(username, password):
    '''User authentication function'''
    if authenticate(username, password):
        return redirect_to_dashboard()
    else:
        return show_error_message()
""")

        (project_dir / "chat.py").write_text("""
def display_messages(messages):
    '''Display chat messages in order'''
    sorted_messages = sorted(messages, key=lambda x: x.timestamp)
    for msg in sorted_messages:
        render_message(msg)
""")

        (project_dir / "README.md").write_text("# Test Project")

        return project_dir

    def test_command_help(self, runner):
        """Test command help text."""
        result = runner.invoke(analyze_completeness, ["--help"])
        assert result.exit_code == 0
        assert "Analyze implementation completeness" in result.output
        assert "--project" in result.output
        assert "--golden-data" in result.output

    def test_missing_required_options(self, runner):
        """Test command fails with missing required options."""
        result = runner.invoke(analyze_completeness, [])
        assert result.exit_code != 0

    @patch('caas_framework.agents.code_analysis_agent.CodeAnalysisAgent')
    @patch('caas_framework.plugins.llm.factory.create_llm_plugin')
    @patch('caas_framework.config.loader.load_config')
    def test_basic_analysis(
        self, mock_load_config, mock_create_llm, mock_agent_class,
        runner, mock_project, mock_golden_data
    ):
        """Test basic completeness analysis."""
        # Mock config
        mock_config = Mock()
        mock_load_config.return_value = mock_config

        # Mock LLM plugin
        mock_llm = Mock()
        mock_create_llm.return_value = mock_llm

        # Mock agent and its analyze_implementation method
        mock_agent = Mock()
        mock_agent_class.return_value = mock_agent

        # Mock analysis result
        from caas_framework.models.code_analysis import (
            ImplementationAnalysisResult,
            TraceabilityResult,
        )

        mock_result = ImplementationAnalysisResult(
            project_name="TestProject",
            total_features=2,
            implemented_features=2,
            partial_features=0,
            missing_features=0,
            overall_coverage=95.0,
            traceability_results=[
                TraceabilityResult(
                    feature_id="feature_1",
                    feature_name="User Authentication",
                    is_implemented=True,
                    coverage_percentage=100.0,
                    implementation_files=["auth.py"],
                    missing_requirements=[],
                    gaps=[],
                ),
            ],
            business_rule_violations=[],
            implementation_gaps=[],
            recommendations=["Excellent coverage!"],
        )

        # Create async mock for analyze_implementation
        async def mock_analyze(*args, **kwargs):
            return mock_result

        mock_agent.analyze_implementation = mock_analyze

        # Run command
        result = runner.invoke(analyze_completeness, [
            "--project", str(mock_project),
            "--golden-data", str(mock_golden_data),
        ])

        # Assertions
        assert result.exit_code == 0
        assert "IMPLEMENTATION COMPLETENESS ANALYSIS" in result.output
        assert "TestProject" in result.output
        assert "95.0%" in result.output or "95%" in result.output
        assert "Excellent coverage" in result.output

    @patch('caas_framework.agents.code_analysis_agent.CodeAnalysisAgent')
    @patch('caas_framework.plugins.llm.factory.create_llm_plugin')
    @patch('caas_framework.config.loader.load_config')
    def test_analysis_with_output_file(
        self, mock_load_config, mock_create_llm, mock_agent_class,
        runner, mock_project, mock_golden_data, tmp_path
    ):
        """Test analysis with JSON output file."""
        # Setup mocks
        mock_config = Mock()
        mock_load_config.return_value = mock_config
        mock_llm = Mock()
        mock_create_llm.return_value = mock_llm
        mock_agent = Mock()
        mock_agent_class.return_value = mock_agent

        from caas_framework.models.code_analysis import ImplementationAnalysisResult

        mock_result = ImplementationAnalysisResult(
            project_name="TestProject",
            total_features=2,
            implemented_features=1,
            partial_features=1,
            missing_features=0,
            overall_coverage=75.0,
            traceability_results=[],
            business_rule_violations=[],
            implementation_gaps=[],
            recommendations=[],
        )

        async def mock_analyze(*args, **kwargs):
            return mock_result

        mock_agent.analyze_implementation = mock_analyze

        output_file = tmp_path / "report.json"

        # Run command
        result = runner.invoke(analyze_completeness, [
            "--project", str(mock_project),
            "--golden-data", str(mock_golden_data),
            "--output", str(output_file),
        ])

        # Assertions
        assert result.exit_code == 0
        assert output_file.exists()

        # Check JSON content
        report = json.loads(output_file.read_text())
        assert report["analysis_type"] == "completeness"
        assert report["summary"]["project_name"] == "TestProject"
        assert report["summary"]["overall_coverage"] == 75.0

    @patch('caas_framework.agents.code_analysis_agent.CodeAnalysisAgent')
    @patch('caas_framework.plugins.llm.factory.create_llm_plugin')
    @patch('caas_framework.config.loader.load_config')
    def test_analysis_with_detailed_flag(
        self, mock_load_config, mock_create_llm, mock_agent_class,
        runner, mock_project, mock_golden_data
    ):
        """Test analysis with detailed output."""
        # Setup mocks
        mock_config = Mock()
        mock_load_config.return_value = mock_config
        mock_llm = Mock()
        mock_create_llm.return_value = mock_llm
        mock_agent = Mock()
        mock_agent_class.return_value = mock_agent

        from caas_framework.models.code_analysis import (
            ImplementationAnalysisResult,
            TraceabilityResult,
        )

        mock_result = ImplementationAnalysisResult(
            project_name="TestProject",
            total_features=2,
            implemented_features=1,
            partial_features=1,
            missing_features=0,
            overall_coverage=60.0,
            traceability_results=[
                TraceabilityResult(
                    feature_id="feature_1",
                    feature_name="User Authentication",
                    is_implemented=True,
                    coverage_percentage=100.0,
                    implementation_files=["auth.py"],
                    missing_requirements=[],
                    gaps=[],
                ),
                TraceabilityResult(
                    feature_id="feature_2",
                    feature_name="Chat Interface",
                    is_implemented=False,
                    coverage_percentage=20.0,
                    implementation_files=[],
                    missing_requirements=["Real-time updates"],
                    gaps=[],
                ),
            ],
            business_rule_violations=[],
            implementation_gaps=[],
            recommendations=[],
        )

        async def mock_analyze(*args, **kwargs):
            return mock_result

        mock_agent.analyze_implementation = mock_analyze

        # Run command with detailed flag
        result = runner.invoke(analyze_completeness, [
            "--project", str(mock_project),
            "--golden-data", str(mock_golden_data),
            "--detailed",
        ])

        # Assertions
        assert result.exit_code == 0
        assert "DETAILED TRACEABILITY ANALYSIS" in result.output
        assert "User Authentication" in result.output
        assert "Chat Interface" in result.output

    @patch('caas_framework.agents.code_analysis_agent.CodeAnalysisAgent')
    @patch('caas_framework.plugins.llm.factory.create_llm_plugin')
    @patch('caas_framework.config.loader.load_config')
    def test_analysis_with_violations(
        self, mock_load_config, mock_create_llm, mock_agent_class,
        runner, mock_project, mock_golden_data
    ):
        """Test analysis with business rule violations."""
        # Setup mocks
        mock_config = Mock()
        mock_load_config.return_value = mock_config
        mock_llm = Mock()
        mock_create_llm.return_value = mock_llm
        mock_agent = Mock()
        mock_agent_class.return_value = mock_agent

        from caas_framework.models.code_analysis import (
            ImplementationAnalysisResult,
            BusinessRuleViolation,
            ErrorSeverity,
        )

        mock_result = ImplementationAnalysisResult(
            project_name="TestProject",
            total_features=2,
            implemented_features=1,
            partial_features=1,
            missing_features=0,
            overall_coverage=70.0,
            traceability_results=[],
            business_rule_violations=[
                BusinessRuleViolation(
                    rule_id="rule_1",
                    feature_id="feature_1",
                    feature_name="User Authentication",
                    violation_type="missing",
                    description="Missing password validation",
                    severity=ErrorSeverity.CRITICAL,
                ),
            ],
            implementation_gaps=[],
            recommendations=[],
        )

        async def mock_analyze(*args, **kwargs):
            return mock_result

        mock_agent.analyze_implementation = mock_analyze

        # Run command
        result = runner.invoke(analyze_completeness, [
            "--project", str(mock_project),
            "--golden-data", str(mock_golden_data),
        ])

        # Assertions
        assert result.exit_code == 0
        assert "BUSINESS RULE VIOLATIONS" in result.output
        assert "Critical" in result.output or "critical" in result.output

    def test_missing_golden_data_file(self, runner, mock_project, tmp_path):
        """Test error handling for missing golden data file."""
        result = runner.invoke(analyze_completeness, [
            "--project", str(mock_project),
            "--golden-data", str(tmp_path / "nonexistent.json"),
        ])

        assert result.exit_code != 0

    def test_missing_project_directory(self, runner, mock_golden_data, tmp_path):
        """Test error handling for missing project directory."""
        result = runner.invoke(analyze_completeness, [
            "--project", str(tmp_path / "nonexistent_project"),
            "--golden-data", str(mock_golden_data),
        ])

        assert result.exit_code != 0

    @patch('caas_framework.agents.code_analysis_agent.CodeAnalysisAgent')
    @patch('caas_framework.plugins.llm.factory.create_llm_plugin')
    @patch('caas_framework.config.loader.load_config')
    def test_low_coverage_exit_code(
        self, mock_load_config, mock_create_llm, mock_agent_class,
        runner, mock_project, mock_golden_data
    ):
        """Test that low coverage (<50%) causes non-zero exit code."""
        # Setup mocks
        mock_config = Mock()
        mock_load_config.return_value = mock_config
        mock_llm = Mock()
        mock_create_llm.return_value = mock_llm
        mock_agent = Mock()
        mock_agent_class.return_value = mock_agent

        from caas_framework.models.code_analysis import ImplementationAnalysisResult

        mock_result = ImplementationAnalysisResult(
            project_name="TestProject",
            total_features=2,
            implemented_features=0,
            partial_features=1,
            missing_features=1,
            overall_coverage=40.0,
            traceability_results=[],
            business_rule_violations=[],
            implementation_gaps=[],
            recommendations=[],
        )

        async def mock_analyze(*args, **kwargs):
            return mock_result

        mock_agent.analyze_implementation = mock_analyze

        # Run command
        result = runner.invoke(analyze_completeness, [
            "--project", str(mock_project),
            "--golden-data", str(mock_golden_data),
        ])

        # Should fail due to low coverage
        assert result.exit_code != 0
        assert "40.0%" in result.output or "40%" in result.output
