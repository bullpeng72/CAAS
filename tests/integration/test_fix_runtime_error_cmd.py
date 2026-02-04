"""
Integration tests for fix-runtime-error CLI command.

Tests the complete workflow of analyzing and fixing runtime errors.
"""

import json
import pytest
from pathlib import Path
from click.testing import CliRunner
from unittest.mock import patch, AsyncMock, Mock

from caas_cli.commands.fix_runtime_error import fix_runtime_error


class TestFixRuntimeErrorCommand:
    """Integration tests for fix-runtime-error command."""

    @pytest.fixture
    def runner(self):
        """CLI runner."""
        return CliRunner()

    @pytest.fixture
    def mock_project(self, tmp_path):
        """Create mock project with buggy code."""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()

        # Create file with import error
        (project_dir / "main.py").write_text("""
import missing_module

def main():
    print('Hello World')

if __name__ == '__main__':
    main()
""")

        return project_dir

    @pytest.fixture
    def error_log_file(self, tmp_path):
        """Create error log file."""
        error_log = """
Traceback (most recent call last):
  File "main.py", line 2, in <module>
    import missing_module
ModuleNotFoundError: No module named 'missing_module'
"""
        log_file = tmp_path / "error.log"
        log_file.write_text(error_log)
        return log_file

    def test_command_help(self, runner):
        """Test command help text."""
        result = runner.invoke(fix_runtime_error, ["--help"])
        assert result.exit_code == 0
        assert "Automatically analyze and fix runtime errors" in result.output
        assert "--project" in result.output
        assert "--error-log" in result.output
        assert "--apply" in result.output

    def test_missing_required_options(self, runner):
        """Test command fails with missing required options."""
        result = runner.invoke(fix_runtime_error, [])
        assert result.exit_code != 0

    @patch('caas_framework.agents.code_analysis_agent.CodeAnalysisAgent')
    @patch('caas_framework.plugins.llm.factory.create_llm_plugin')
    @patch('caas_framework.config.loader.load_config')
    def test_analyze_error_preview_mode(
        self, mock_load_config, mock_create_llm, mock_agent_class,
        runner, mock_project, error_log_file
    ):
        """Test error analysis in preview mode (no --apply)."""
        # Setup mocks
        mock_config = Mock()
        mock_load_config.return_value = mock_config
        mock_llm = Mock()
        mock_create_llm.return_value = mock_llm
        mock_agent = Mock()
        mock_agent_class.return_value = mock_agent

        from caas_framework.models.code_analysis import (
            RuntimeErrorFix,
            RuntimeErrorInfo,
            CodeFix,
            ErrorCategory,
            ErrorSeverity,
        )

        # Mock fix result
        mock_fix = RuntimeErrorFix(
            error_info=RuntimeErrorInfo(
                error_type="ModuleNotFoundError",
                error_message="No module named 'missing_module'",
                file_path="main.py",
                line_number=2,
                category=ErrorCategory.IMPORT,
                severity=ErrorSeverity.CRITICAL,
            ),
            fixes=[
                CodeFix(
                    file_path="main.py",
                    original_code="import missing_module",
                    fixed_code="# import missing_module  # Module not found",
                    explanation="Commented out missing import",
                    confidence=0.9,
                ),
            ],
            root_cause="The module 'missing_module' is not installed or does not exist",
            fix_strategy="Install missing dependency or fix import path",
            test_command="python main.py",
        )

        async def mock_analyze(*args, **kwargs):
            return mock_fix

        mock_agent.analyze_runtime_error = mock_analyze

        # Run command without --apply
        result = runner.invoke(fix_runtime_error, [
            "--project", str(mock_project),
            "--error-log", str(error_log_file),
        ])

        # Assertions
        assert result.exit_code == 0
        assert "RUNTIME ERROR ANALYSIS" in result.output
        assert "ModuleNotFoundError" in result.output
        assert "ROOT CAUSE ANALYSIS" in result.output
        assert "PROPOSED FIX" in result.output
        assert "Preview mode" in result.output

    @patch('caas_framework.agents.code_analysis_agent.CodeAnalysisAgent')
    @patch('caas_framework.plugins.llm.factory.create_llm_plugin')
    @patch('caas_framework.config.loader.load_config')
    def test_apply_fix_with_backup(
        self, mock_load_config, mock_create_llm, mock_agent_class,
        runner, mock_project, error_log_file
    ):
        """Test applying fix with backup."""
        # Setup mocks
        mock_config = Mock()
        mock_load_config.return_value = mock_config
        mock_llm = Mock()
        mock_create_llm.return_value = mock_llm
        mock_agent = Mock()
        mock_agent_class.return_value = mock_agent

        from caas_framework.models.code_analysis import (
            RuntimeErrorFix,
            RuntimeErrorInfo,
            CodeFix,
            ErrorCategory,
            ErrorSeverity,
        )

        original_content = (mock_project / "main.py").read_text()

        mock_fix = RuntimeErrorFix(
            error_info=RuntimeErrorInfo(
                error_type="ModuleNotFoundError",
                error_message="No module named 'missing_module'",
                file_path="main.py",
                line_number=2,
                category=ErrorCategory.IMPORT,
                severity=ErrorSeverity.CRITICAL,
            ),
            fixes=[
                CodeFix(
                    file_path="main.py",
                    original_code="import missing_module",
                    fixed_code="# import missing_module  # Fixed",
                    explanation="Commented out missing import",
                    confidence=0.9,
                ),
            ],
            root_cause="Missing module",
            fix_strategy="Remove import",
            test_command="python main.py",
        )

        async def mock_analyze(*args, **kwargs):
            return mock_fix

        mock_agent.analyze_runtime_error = mock_analyze

        # Run command with --apply and --backup
        result = runner.invoke(fix_runtime_error, [
            "--project", str(mock_project),
            "--error-log", str(error_log_file),
            "--apply",
            "--backup",
        ])

        # Assertions
        assert result.exit_code == 0
        assert "Applying fixes" in result.output
        assert "Backup created" in result.output
        assert "Fixed: main.py" in result.output or "✅ Fixed" in result.output

        # Check backup was created
        backup_file = mock_project / "main.py.backup"
        assert backup_file.exists()
        assert backup_file.read_text() == original_content

    @patch('caas_framework.agents.code_analysis_agent.CodeAnalysisAgent')
    @patch('caas_framework.plugins.llm.factory.create_llm_plugin')
    @patch('caas_framework.config.loader.load_config')
    def test_fix_with_output_report(
        self, mock_load_config, mock_create_llm, mock_agent_class,
        runner, mock_project, error_log_file, tmp_path
    ):
        """Test fix with JSON output report."""
        # Setup mocks
        mock_config = Mock()
        mock_load_config.return_value = mock_config
        mock_llm = Mock()
        mock_create_llm.return_value = mock_llm
        mock_agent = Mock()
        mock_agent_class.return_value = mock_agent

        from caas_framework.models.code_analysis import (
            RuntimeErrorFix,
            RuntimeErrorInfo,
            CodeFix,
            ErrorCategory,
            ErrorSeverity,
        )

        mock_fix = RuntimeErrorFix(
            error_info=RuntimeErrorInfo(
                error_type="NameError",
                error_message="name 'undefined_var' is not defined",
                file_path="main.py",
                line_number=5,
                category=ErrorCategory.NAME,
                severity=ErrorSeverity.HIGH,
            ),
            fixes=[
                CodeFix(
                    file_path="main.py",
                    original_code="result = undefined_var + 1",
                    fixed_code="result = 0 + 1  # Fixed: undefined_var",
                    explanation="Initialized undefined variable",
                    confidence=0.7,
                ),
            ],
            root_cause="Variable used before definition",
            fix_strategy="Initialize variable before use",
            test_command="python main.py",
        )

        async def mock_analyze(*args, **kwargs):
            return mock_fix

        mock_agent.analyze_runtime_error = mock_analyze

        output_file = tmp_path / "fix_report.json"

        # Run command
        result = runner.invoke(fix_runtime_error, [
            "--project", str(mock_project),
            "--error-log", str(error_log_file),
            "--output", str(output_file),
        ])

        # Assertions
        assert result.exit_code == 0
        assert output_file.exists()

        # Check JSON content
        report = json.loads(output_file.read_text())
        assert report["analysis_type"] == "runtime_error"
        assert report["error_info"]["error_type"] == "NameError"
        assert report["root_cause"] == "Variable used before definition"

    @patch('caas_framework.agents.code_analysis_agent.CodeAnalysisAgent')
    @patch('caas_framework.plugins.llm.factory.create_llm_plugin')
    @patch('caas_framework.config.loader.load_config')
    def test_interactive_error_paste(
        self, mock_load_config, mock_create_llm, mock_agent_class,
        runner, mock_project
    ):
        """Test interactive error paste mode (no --error-log)."""
        # Setup mocks
        mock_config = Mock()
        mock_load_config.return_value = mock_config
        mock_llm = Mock()
        mock_create_llm.return_value = mock_llm
        mock_agent = Mock()
        mock_agent_class.return_value = mock_agent

        from caas_framework.models.code_analysis import (
            RuntimeErrorFix,
            RuntimeErrorInfo,
            CodeFix,
            ErrorCategory,
            ErrorSeverity,
        )

        mock_fix = RuntimeErrorFix(
            error_info=RuntimeErrorInfo(
                error_type="TypeError",
                error_message="unsupported operand type(s)",
                file_path="main.py",
                line_number=10,
                category=ErrorCategory.TYPE,
                severity=ErrorSeverity.HIGH,
            ),
            fixes=[],
            root_cause="Type mismatch",
            fix_strategy="Fix type conversion",
            test_command="python main.py",
        )

        async def mock_analyze(*args, **kwargs):
            return mock_fix

        mock_agent.analyze_runtime_error = mock_analyze

        # Simulate user input
        error_text = "TypeError: unsupported operand type(s) for +: 'int' and 'str'"

        result = runner.invoke(fix_runtime_error, [
            "--project", str(mock_project),
        ], input=error_text)

        # Should handle interactive mode
        assert "Paste your error traceback" in result.output or result.exit_code == 0

    @patch('caas_framework.agents.code_analysis_agent.CodeAnalysisAgent')
    @patch('caas_framework.plugins.llm.factory.create_llm_plugin')
    @patch('caas_framework.config.loader.load_config')
    def test_low_confidence_fix_warning(
        self, mock_load_config, mock_create_llm, mock_agent_class,
        runner, mock_project, error_log_file
    ):
        """Test warning for low-confidence fixes."""
        # Setup mocks
        mock_config = Mock()
        mock_load_config.return_value = mock_config
        mock_llm = Mock()
        mock_create_llm.return_value = mock_llm
        mock_agent = Mock()
        mock_agent_class.return_value = mock_agent

        from caas_framework.models.code_analysis import (
            RuntimeErrorFix,
            RuntimeErrorInfo,
            CodeFix,
            ErrorCategory,
            ErrorSeverity,
        )

        mock_fix = RuntimeErrorFix(
            error_info=RuntimeErrorInfo(
                error_type="RuntimeError",
                error_message="Complex error",
                file_path="main.py",
                line_number=20,
                category=ErrorCategory.RUNTIME,
                severity=ErrorSeverity.HIGH,
            ),
            fixes=[
                CodeFix(
                    file_path="main.py",
                    original_code="complex_code()",
                    fixed_code="# complex_code()  # Needs review",
                    explanation="Uncertain fix",
                    confidence=0.5,  # Low confidence
                ),
            ],
            root_cause="Complex logic error",
            fix_strategy="Manual review needed",
            test_command="python main.py",
        )

        async def mock_analyze(*args, **kwargs):
            return mock_fix

        mock_agent.analyze_runtime_error = mock_analyze

        # Run command
        result = runner.invoke(fix_runtime_error, [
            "--project", str(mock_project),
            "--error-log", str(error_log_file),
        ])

        # Should show low confidence warning
        assert result.exit_code == 0
        assert "Low confidence" in result.output or "manual review" in result.output.lower()

    def test_missing_error_log_and_no_input(self, runner, mock_project):
        """Test error when no error log provided and no stdin input."""
        result = runner.invoke(fix_runtime_error, [
            "--project", str(mock_project),
        ], input="")  # Empty input

        # Should fail
        assert result.exit_code != 0

    @patch('caas_framework.agents.code_analysis_agent.CodeAnalysisAgent')
    @patch('caas_framework.plugins.llm.factory.create_llm_plugin')
    @patch('caas_framework.config.loader.load_config')
    def test_multiple_fixes(
        self, mock_load_config, mock_create_llm, mock_agent_class,
        runner, mock_project, error_log_file
    ):
        """Test handling multiple fixes for one error."""
        # Setup mocks
        mock_config = Mock()
        mock_load_config.return_value = mock_config
        mock_llm = Mock()
        mock_create_llm.return_value = mock_llm
        mock_agent = Mock()
        mock_agent_class.return_value = mock_agent

        from caas_framework.models.code_analysis import (
            RuntimeErrorFix,
            RuntimeErrorInfo,
            CodeFix,
            ErrorCategory,
            ErrorSeverity,
        )

        mock_fix = RuntimeErrorFix(
            error_info=RuntimeErrorInfo(
                error_type="ImportError",
                error_message="Cannot import module",
                file_path="main.py",
                line_number=1,
                category=ErrorCategory.IMPORT,
                severity=ErrorSeverity.CRITICAL,
            ),
            fixes=[
                CodeFix(
                    file_path="main.py",
                    original_code="import module1",
                    fixed_code="# import module1",
                    explanation="Fix 1",
                    confidence=0.8,
                ),
                CodeFix(
                    file_path="utils.py",
                    original_code="from module1 import func",
                    fixed_code="# from module1 import func",
                    explanation="Fix 2",
                    confidence=0.8,
                ),
            ],
            root_cause="Missing dependency",
            fix_strategy="Remove imports",
            test_command="python main.py",
        )

        async def mock_analyze(*args, **kwargs):
            return mock_fix

        mock_agent.analyze_runtime_error = mock_analyze

        # Run command
        result = runner.invoke(fix_runtime_error, [
            "--project", str(mock_project),
            "--error-log", str(error_log_file),
        ])

        # Should show multiple fixes
        assert result.exit_code == 0
        assert "2 change(s)" in result.output or "Fix #1" in result.output

    @patch('caas_framework.agents.code_analysis_agent.CodeAnalysisAgent')
    @patch('caas_framework.plugins.llm.factory.create_llm_plugin')
    @patch('caas_framework.config.loader.load_config')
    def test_no_fixes_generated(
        self, mock_load_config, mock_create_llm, mock_agent_class,
        runner, mock_project, error_log_file
    ):
        """Test when no fixes can be generated."""
        # Setup mocks
        mock_config = Mock()
        mock_load_config.return_value = mock_config
        mock_llm = Mock()
        mock_create_llm.return_value = mock_llm
        mock_agent = Mock()
        mock_agent_class.return_value = mock_agent

        from caas_framework.models.code_analysis import (
            RuntimeErrorFix,
            RuntimeErrorInfo,
            ErrorCategory,
            ErrorSeverity,
        )

        mock_fix = RuntimeErrorFix(
            error_info=RuntimeErrorInfo(
                error_type="UnknownError",
                error_message="Cannot analyze",
                file_path="main.py",
                line_number=1,
                category=ErrorCategory.RUNTIME,
                severity=ErrorSeverity.HIGH,
            ),
            fixes=[],  # No fixes
            root_cause="Unknown",
            fix_strategy="Manual intervention required",
            test_command="python main.py",
        )

        async def mock_analyze(*args, **kwargs):
            return mock_fix

        mock_agent.analyze_runtime_error = mock_analyze

        # Run command
        result = runner.invoke(fix_runtime_error, [
            "--project", str(mock_project),
            "--error-log", str(error_log_file),
        ])

        # Should handle no fixes gracefully
        assert result.exit_code == 0
        assert "Could not generate fix" in result.output or "Manual intervention" in result.output
