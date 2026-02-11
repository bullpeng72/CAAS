"""
Test suite for Integration Agent (v0.5.0)

Tests the IntegrationAgent implementation.
Target coverage: 90%+
"""

import pytest

from caas_framework.agents.integration_agent import (
    IntegrationAgent,
    BackendGenerationResult,
    FrontendGenerationResult,
    TestGenerationResult,
    IntegratedResult,
    CrossValidationIssue,
    CrossValidationResult,
)
from caas_framework.models.validation import ValidationSeverity


class TestIntegrationAgent:
    """Test IntegrationAgent initialization."""

    def test_initialization(self):
        """Test agent initialization."""
        agent = IntegrationAgent()
        assert agent is not None
        assert agent.logger is not None


class TestIntegrate:
    """Test integrate() method."""

    def test_integrates_backend_and_frontend(self):
        """Test basic integration of backend and frontend."""
        agent = IntegrationAgent()

        backend = BackendGenerationResult(
            files={"main.py": "def main(): pass", "agents.py": "# agents"},
            agents_count=2,
            tasks_count=3,
        )

        frontend = FrontendGenerationResult(
            app_code="import streamlit as st\nst.title('App')",
            ui_requirements_input_names=["keyword"],
        )

        result = agent.integrate(backend=backend, frontend=frontend, tests=None)

        assert isinstance(result, IntegratedResult)
        assert len(result.all_files) == 3  # main.py, agents.py, app.py
        assert "main.py" in result.all_files
        assert "app.py" in result.all_files
        assert result.backend_files == backend.files
        assert result.frontend_files == {"app.py": frontend.app_code}

    def test_integrates_with_tests(self):
        """Test integration including test files."""
        agent = IntegrationAgent()

        backend = BackendGenerationResult(files={"main.py": "code"})
        frontend = FrontendGenerationResult(app_code="ui code")
        tests = TestGenerationResult(test_files={"test_main.py": "test code"})

        result = agent.integrate(backend=backend, frontend=frontend, tests=tests)

        assert len(result.all_files) == 3
        assert "test_main.py" in result.all_files
        assert result.test_files == tests.test_files

    def test_integrates_without_tests(self):
        """Test integration when tests are None."""
        agent = IntegrationAgent()

        backend = BackendGenerationResult(files={"main.py": "code"})
        frontend = FrontendGenerationResult(app_code="ui")

        result = agent.integrate(backend=backend, frontend=frontend, tests=None)

        assert len(result.test_files) == 0
        assert len(result.all_files) == 2


class TestCrossValidate:
    """Test cross_validate() method."""

    def test_validates_clean_integration(self):
        """Test validation with clean backend-frontend integration."""
        agent = IntegrationAgent()

        backend = BackendGenerationResult(
            files={
                "main.py": "def main(inputs=None):\n    pass",
                "tasks.py": "description = 'Use {keyword}'",
            }
        )

        frontend = FrontendGenerationResult(
            app_code="from main import main\nkeyword = st.text_input('Keyword')\nresult = main(inputs=user_inputs)",
            ui_requirements_input_names=["keyword"],
        )

        result = agent.cross_validate(backend=backend, frontend=frontend)

        assert isinstance(result, CrossValidationResult)
        assert result.passed is True
        # May have warnings (e.g., missing_path_setup) but no errors
        error_issues = [i for i in result.issues if i.severity == ValidationSeverity.ERROR]
        assert len(error_issues) == 0

    def test_detects_signature_mismatch(self):
        """Test detection of main() signature mismatch."""
        agent = IntegrationAgent()

        backend = BackendGenerationResult(
            files={"main.py": "def main():\n    pass"}  # No inputs parameter
        )

        frontend = FrontendGenerationResult(
            app_code="result = main(inputs=user_inputs)",  # Calls with inputs
            ui_requirements_input_names=[],
        )

        result = agent.cross_validate(backend=backend, frontend=frontend)

        assert result.passed is False
        assert any(
            issue.type == "signature_mismatch" for issue in result.issues
        )
        assert any(
            issue.severity == ValidationSeverity.ERROR for issue in result.issues
        )

    def test_detects_missing_input_widgets(self):
        """Test detection of missing input widgets."""
        agent = IntegrationAgent()

        backend = BackendGenerationResult(
            files={
                "main.py": "def main(inputs=None): pass",
                "tasks.py": "description = 'Search {keyword} and {url}'",
            }
        )

        frontend = FrontendGenerationResult(
            app_code="keyword = st.text_input('Keyword')",  # Missing url widget
            ui_requirements_input_names=["keyword"],  # Only keyword, no url
        )

        result = agent.cross_validate(backend=backend, frontend=frontend)

        assert result.passed is False
        assert any(
            issue.type == "missing_input_widgets" for issue in result.issues
        )
        assert "url" in str(result.issues)

    def test_detects_unused_input_widgets(self):
        """Test detection of unused input widgets."""
        agent = IntegrationAgent()

        backend = BackendGenerationResult(
            files={
                "main.py": "def main(inputs=None): pass",
                "tasks.py": "description = 'Search {keyword}'",
            }
        )

        frontend = FrontendGenerationResult(
            app_code="keyword, url = widgets",
            ui_requirements_input_names=["keyword", "url"],  # url not used by backend
        )

        result = agent.cross_validate(backend=backend, frontend=frontend)

        assert any(
            issue.type == "unused_input_widgets" for issue in result.issues
        )
        assert any(
            issue.severity == ValidationSeverity.WARNING for issue in result.issues
        )

    def test_detects_missing_import(self):
        """Test detection of missing import statement."""
        agent = IntegrationAgent()

        backend = BackendGenerationResult(
            files={"main.py": "def main(inputs=None): pass"}
        )

        frontend = FrontendGenerationResult(
            app_code="import streamlit as st\nresult = main()",  # No import of main
            ui_requirements_input_names=[],
        )

        result = agent.cross_validate(backend=backend, frontend=frontend)

        assert any(issue.type == "missing_import" for issue in result.issues)

    def test_detects_missing_path_setup(self):
        """Test detection of missing sys.path setup."""
        agent = IntegrationAgent()

        backend = BackendGenerationResult(files={"main.py": "def main(): pass"})

        frontend = FrontendGenerationResult(
            app_code="from main import main\nresult = main()",  # No sys.path setup
            ui_requirements_input_names=[],
        )

        result = agent.cross_validate(backend=backend, frontend=frontend)

        assert any(
            issue.type == "missing_path_setup" for issue in result.issues
        )


class TestAutoFixIntegrationIssues:
    """Test auto_fix_integration_issues() method."""

    def test_fixes_signature_mismatch(self):
        """Test auto-fix for main() signature mismatch."""
        agent = IntegrationAgent()

        backend = BackendGenerationResult(
            files={"main.py": "def main():\n    return 'result'"}
        )

        frontend = FrontendGenerationResult(
            app_code="result = main(inputs=user_inputs)", ui_requirements_input_names=[]
        )

        issues = [
            CrossValidationIssue(
                severity=ValidationSeverity.ERROR,
                type="signature_mismatch",
                message="Signature mismatch",
                auto_fix="Add inputs parameter",
            )
        ]

        result = agent.auto_fix_integration_issues(
            backend=backend, frontend=frontend, issues=issues
        )

        assert "def main(inputs=None):" in result.backend_files["main.py"]

    def test_fixes_missing_input_widgets(self):
        """Test auto-fix for missing input widgets."""
        agent = IntegrationAgent()

        backend = BackendGenerationResult(files={"main.py": "code"})

        frontend = FrontendGenerationResult(
            app_code="# Input widgets\nresult = main()",
            ui_requirements_input_names=["keyword"],
        )

        issues = [
            CrossValidationIssue(
                severity=ValidationSeverity.ERROR,
                type="missing_input_widgets",
                message="Backend requires inputs {keyword} but frontend doesn't provide them",
                auto_fix="Add widget",
            )
        ]

        result = agent.auto_fix_integration_issues(
            backend=backend, frontend=frontend, issues=issues
        )

        assert "keyword = st.text_input" in result.frontend_files["app.py"]

    def test_fixes_missing_import(self):
        """Test auto-fix for missing import statement."""
        agent = IntegrationAgent()

        backend = BackendGenerationResult(files={"main.py": "code"})

        frontend = FrontendGenerationResult(
            app_code="from pathlib import Path\n\nresult = main()",
            ui_requirements_input_names=[],
        )

        issues = [
            CrossValidationIssue(
                severity=ValidationSeverity.ERROR,
                type="missing_import",
                message="Missing import",
                auto_fix="Add import",
            )
        ]

        result = agent.auto_fix_integration_issues(
            backend=backend, frontend=frontend, issues=issues
        )

        assert "from main import main" in result.frontend_files["app.py"]

    def test_fixes_unused_parameter(self):
        """Test auto-fix for unused inputs parameter."""
        agent = IntegrationAgent()

        backend = BackendGenerationResult(
            files={"main.py": "def main(inputs=None): pass"}
        )

        frontend = FrontendGenerationResult(
            app_code="result = main()", ui_requirements_input_names=[]
        )

        issues = [
            CrossValidationIssue(
                severity=ValidationSeverity.WARNING,
                type="unused_parameter",
                message="Unused parameter",
                auto_fix="Pass inputs",
            )
        ]

        result = agent.auto_fix_integration_issues(
            backend=backend, frontend=frontend, issues=issues
        )

        assert "main(inputs=user_inputs)" in result.frontend_files["app.py"]

    def test_handles_multiple_fixes(self):
        """Test handling multiple auto-fixes."""
        agent = IntegrationAgent()

        backend = BackendGenerationResult(
            files={"main.py": "def main():\n    pass"}
        )

        frontend = FrontendGenerationResult(
            app_code="from pathlib import Path\n# Input widgets\nresult = main()",
            ui_requirements_input_names=[],
        )

        issues = [
            CrossValidationIssue(
                severity=ValidationSeverity.ERROR,
                type="signature_mismatch",
                message="Fix signature",
                auto_fix="Add inputs",
            ),
            CrossValidationIssue(
                severity=ValidationSeverity.ERROR,
                type="missing_import",
                message="Fix import",
                auto_fix="Add import",
            ),
        ]

        result = agent.auto_fix_integration_issues(
            backend=backend, frontend=frontend, issues=issues
        )

        assert "def main(inputs=None):" in result.backend_files["main.py"]
        assert "from main import main" in result.frontend_files["app.py"]


class TestIntegrationScenarios:
    """Integration test scenarios."""

    def test_complete_integration_workflow(self):
        """Test complete integration workflow."""
        agent = IntegrationAgent()

        # 1. Create backend and frontend
        backend = BackendGenerationResult(
            files={
                "main.py": "def main(inputs=None):\n    return inputs['keyword']",
                "tasks.py": "description = 'Search {keyword}'",
            },
            agents_count=1,
            tasks_count=1,
        )

        frontend = FrontendGenerationResult(
            app_code="""
from main import main
import sys
keyword = st.text_input('Keyword')
result = main(inputs={'keyword': keyword})
""",
            ui_requirements_input_names=["keyword"],
        )

        # 2. Integrate
        integrated = agent.integrate(backend=backend, frontend=frontend)
        assert len(integrated.all_files) == 3

        # 3. Cross-validate
        validation = agent.cross_validate(backend=backend, frontend=frontend)
        assert validation.passed is True

    def test_workflow_with_issues_and_auto_fix(self):
        """Test workflow with issues that require auto-fix."""
        agent = IntegrationAgent()

        backend = BackendGenerationResult(
            files={
                "main.py": "def main():\n    pass",  # Missing inputs param
                "tasks.py": "description = '{keyword}'",
            }
        )

        frontend = FrontendGenerationResult(
            app_code="result = main(inputs=data)",  # Calls with inputs
            ui_requirements_input_names=["keyword"],
        )

        # Validate - should find issues
        validation = agent.cross_validate(backend=backend, frontend=frontend)
        assert validation.passed is False
        assert len(validation.issues) > 0

        # Auto-fix
        fixed = agent.auto_fix_integration_issues(
            backend=backend, frontend=frontend, issues=validation.issues
        )

        # Verify fixes
        assert "def main(inputs=None):" in fixed.backend_files["main.py"]

    def test_no_issues_workflow(self):
        """Test workflow when everything is correct."""
        agent = IntegrationAgent()

        backend = BackendGenerationResult(
            files={
                "main.py": "def main(inputs=None): pass",
                "tasks.py": "description = '{x}'",
            }
        )

        frontend = FrontendGenerationResult(
            app_code="from main import main\nimport sys\nx = st.text_input('X')\nmain(inputs={'x': x})",
            ui_requirements_input_names=["x"],
        )

        validation = agent.cross_validate(backend=backend, frontend=frontend)

        assert validation.passed is True
        # May have warnings but no errors
        error_issues = [i for i in validation.issues if i.severity == ValidationSeverity.ERROR]
        assert len(error_issues) == 0
