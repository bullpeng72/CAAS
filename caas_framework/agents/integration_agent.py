"""
Integration Agent (v0.5.0)

Agent for merging and cross-validating outputs from specialized agents.

Responsibilities:
- Merge backend + frontend + test outputs
- Cross-validate integration points
- Ensure main.py signature matches app.py calls
- Ensure inputs in app.py match tasks in backend
- Auto-fix integration issues

Phase: POST-DELIVERY
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from caas_framework.models.validation import ValidationSeverity
from caas_framework.utils.logger import get_logger

logger = get_logger("agents.integration_agent")


@dataclass
class BackendGenerationResult:
    """Result from backend code generation."""

    files: Dict[str, str]  # filename -> code
    agents_count: int = 0
    tasks_count: int = 0


@dataclass
class FrontendGenerationResult:
    """Result from frontend code generation."""

    app_code: str
    ui_requirements_input_names: List[str] = field(default_factory=list)
    framework: str = "streamlit"


@dataclass
class TestGenerationResult:
    """Result from test generation."""

    test_files: Dict[str, str] = field(default_factory=dict)


@dataclass
class IntegratedResult:
    """Integrated result from all agents."""

    backend_files: Dict[str, str]
    frontend_files: Dict[str, str]
    test_files: Dict[str, str]
    all_files: Dict[str, str]


@dataclass
class CrossValidationIssue:
    """Issue found during cross-validation."""

    severity: ValidationSeverity
    type: str
    message: str
    backend_location: Optional[str] = None
    frontend_location: Optional[str] = None
    auto_fix: Optional[str] = None


@dataclass
class CrossValidationResult:
    """Result of cross-validation."""

    passed: bool
    issues: List[CrossValidationIssue]
    backend_inputs: Set[str] = field(default_factory=set)
    frontend_inputs: Set[str] = field(default_factory=set)


class IntegrationAgent:
    """
    Integration Agent

    Merges and cross-validates outputs from specialized agents (Backend, Frontend, Tests).
    Ensures integration points are correct and auto-fixes common issues.
    """

    def __init__(self):
        """Initialize Integration Agent."""
        self.logger = logger

    def integrate(
        self,
        backend: BackendGenerationResult,
        frontend: FrontendGenerationResult,
        tests: Optional[TestGenerationResult] = None,
    ) -> IntegratedResult:
        """
        Merge outputs from specialized agents.

        Args:
            backend: Backend generation result
            frontend: Frontend generation result
            tests: Optional test generation result

        Returns:
            IntegratedResult with all files merged
        """
        logger.info("🔗 Integrating outputs from specialized agents...")

        all_files = {}

        # Add backend files
        all_files.update(backend.files)
        logger.info(f"✅ Added {len(backend.files)} backend files")

        # Add frontend file
        frontend_files = {"app.py": frontend.app_code}
        all_files.update(frontend_files)
        logger.info("✅ Added frontend file (app.py)")

        # Add test files if available
        test_files = {}
        if tests:
            test_files.update(tests.test_files)
            all_files.update(tests.test_files)
            logger.info(f"✅ Added {len(test_files)} test files")

        logger.info(f"✅ Integration complete: {len(all_files)} total files")

        return IntegratedResult(
            backend_files=backend.files,
            frontend_files=frontend_files,
            test_files=test_files,
            all_files=all_files,
        )

    def cross_validate(
        self,
        backend: BackendGenerationResult,
        frontend: FrontendGenerationResult,
    ) -> CrossValidationResult:
        """
        Cross-validate integration between backend and frontend.

        Checks:
        1. main.py signature matches app.py calls
        2. Input requirements in app.py match task templates in backend
        3. Import statements are compatible

        Args:
            backend: Backend generation result
            frontend: Frontend generation result

        Returns:
            CrossValidationResult
        """
        logger.info("🔍 Cross-validating backend-frontend integration...")

        issues = []

        main_code = backend.files.get("main.py", "")
        app_code = frontend.app_code

        # Check 1: main() signature compatibility
        logger.info("Checking main() signature compatibility...")
        signature_issues = self._check_main_signature(main_code, app_code)
        issues.extend(signature_issues)

        # Check 2: Input requirements consistency
        logger.info("Checking input requirements consistency...")
        input_issues, backend_inputs, frontend_inputs = self._check_input_consistency(
            backend.files, frontend
        )
        issues.extend(input_issues)

        # Check 3: Import compatibility
        logger.info("Checking import compatibility...")
        import_issues = self._check_import_compatibility(app_code)
        issues.extend(import_issues)

        # Determine if validation passed
        error_count = len([i for i in issues if i.severity == ValidationSeverity.ERROR])
        passed = error_count == 0

        if passed:
            logger.info("✅ Cross-validation passed")
        else:
            logger.warning(f"⚠️ Cross-validation found {error_count} errors")

        return CrossValidationResult(
            passed=passed,
            issues=issues,
            backend_inputs=backend_inputs,
            frontend_inputs=frontend_inputs,
        )

    def _check_main_signature(
        self, main_code: str, app_code: str
    ) -> List[CrossValidationIssue]:
        """
        Check if main() signature matches app.py calls.

        Args:
            main_code: main.py code
            app_code: app.py code

        Returns:
            List of issues
        """
        issues = []

        # Check if main() accepts inputs parameter
        main_signature_pattern = r"def\s+main\s*\(\s*inputs\s*[=:]"
        has_inputs_param = bool(re.search(main_signature_pattern, main_code))

        # Check if app.py calls main(inputs=...)
        app_calls_with_inputs = "main(inputs=" in app_code or "main(inputs =" in app_code

        if app_calls_with_inputs and not has_inputs_param:
            issues.append(
                CrossValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    type="signature_mismatch",
                    message="app.py calls main(inputs=...) but main() doesn't accept inputs parameter",
                    backend_location="main.py:def main()",
                    frontend_location="app.py:main(inputs=...)",
                    auto_fix="Add 'inputs=None' parameter to main() function in main.py",
                )
            )
        elif not app_calls_with_inputs and has_inputs_param:
            issues.append(
                CrossValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    type="unused_parameter",
                    message="main() accepts inputs parameter but app.py doesn't pass it",
                    backend_location="main.py:def main(inputs=...)",
                    frontend_location="app.py:main()",
                    auto_fix="Update app.py to call main(inputs=user_inputs)",
                )
            )

        return issues

    def _check_input_consistency(
        self, backend_files: Dict[str, str], frontend: FrontendGenerationResult
    ) -> tuple[List[CrossValidationIssue], Set[str], Set[str]]:
        """
        Check input requirements consistency between backend and frontend.

        Args:
            backend_files: Backend code files
            frontend: Frontend generation result

        Returns:
            Tuple of (issues, backend_inputs, frontend_inputs)
        """
        issues = []

        # Extract template variables from backend tasks
        tasks_code = backend_files.get("tasks.py", "")
        backend_inputs = set(re.findall(r"\{(\w+)\}", tasks_code))

        # Get frontend inputs
        if hasattr(frontend, "ui_requirements_input_names"):
            # Legacy attribute
            frontend_inputs = set(frontend.ui_requirements_input_names)
        elif hasattr(frontend, "ui_requirements"):
            # v0.5.0: Extract from UIRequirement objects
            frontend_inputs = set(req.input_name for req in frontend.ui_requirements)
        else:
            frontend_inputs = set()

        # Check for missing inputs in frontend
        missing_in_frontend = backend_inputs - frontend_inputs
        if missing_in_frontend:
            issues.append(
                CrossValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    type="missing_input_widgets",
                    message=f"Backend requires inputs {missing_in_frontend} but frontend doesn't provide them",
                    backend_location="tasks.py:task descriptions",
                    frontend_location="app.py:input widgets",
                    auto_fix=f"Add UI widgets for: {', '.join(missing_in_frontend)}",
                )
            )

        # Check for extra inputs in frontend (not used by backend)
        extra_in_frontend = frontend_inputs - backend_inputs
        if extra_in_frontend:
            issues.append(
                CrossValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    type="unused_input_widgets",
                    message=f"Frontend has inputs {extra_in_frontend} but backend doesn't use them",
                    backend_location="tasks.py",
                    frontend_location="app.py:input widgets",
                    auto_fix=f"Remove unused widgets or add to tasks: {', '.join(extra_in_frontend)}",
                )
            )

        return issues, backend_inputs, frontend_inputs

    def _check_import_compatibility(self, app_code: str) -> List[CrossValidationIssue]:
        """
        Check if app.py imports are compatible.

        Args:
            app_code: app.py code

        Returns:
            List of issues
        """
        issues = []

        # Check if app.py imports main from main.py
        if "from main import main" not in app_code and "from main import *" not in app_code:
            issues.append(
                CrossValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    type="missing_import",
                    message="app.py doesn't import main from main.py",
                    frontend_location="app.py:imports",
                    auto_fix="Add: from main import main",
                )
            )

        # Check if sys.path manipulation exists (needed for imports)
        if "sys.path" not in app_code:
            issues.append(
                CrossValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    type="missing_path_setup",
                    message="app.py may not have proper sys.path setup for imports",
                    frontend_location="app.py",
                    auto_fix="Add: sys.path.insert(0, str(Path(__file__).parent))",
                )
            )

        return issues

    def auto_fix_integration_issues(
        self,
        backend: BackendGenerationResult,
        frontend: FrontendGenerationResult,
        issues: List[CrossValidationIssue],
    ) -> IntegratedResult:
        """
        Auto-fix integration issues by patching code.

        Args:
            backend: Backend generation result
            frontend: Frontend generation result
            issues: Cross-validation issues

        Returns:
            IntegratedResult with fixed code
        """
        logger.info(f"🔧 Auto-fixing {len(issues)} integration issues...")

        fixed_backend_files = backend.files.copy()
        fixed_frontend_code = frontend.app_code

        for issue in issues:
            if issue.type == "signature_mismatch":
                # Fix main() signature to accept inputs
                main_code = fixed_backend_files.get("main.py", "")

                # Replace: def main():
                # With:    def main(inputs=None):
                pattern = r"(def\s+main\s*\(\s*)\):"
                replacement = r"\1inputs=None):"
                fixed_main = re.sub(pattern, replacement, main_code, count=1)

                if fixed_main != main_code:
                    fixed_backend_files["main.py"] = fixed_main
                    logger.info("✅ Fixed main() signature in main.py")

            elif issue.type == "missing_input_widgets":
                # Add missing widgets to frontend
                missing_inputs_match = re.search(r"\{([^}]+)\}", issue.message)
                if missing_inputs_match:
                    missing_inputs_str = missing_inputs_match.group(1)
                    missing_inputs = [inp.strip() for inp in missing_inputs_str.split(",")]

                    for input_name in missing_inputs:
                        widget_code = f'{input_name} = st.text_input("{input_name}:", key="{input_name}")\n'

                        # Insert after "# Input widgets" comment
                        pattern = r"(# Input widgets\s*\n)"
                        replacement = rf"\1{widget_code}"
                        fixed_frontend_code = re.sub(
                            pattern, replacement, fixed_frontend_code, count=1
                        )

                    logger.info(f"✅ Added {len(missing_inputs)} missing widgets to app.py")

            elif issue.type == "missing_import":
                # Add import statement
                if "from main import main" not in fixed_frontend_code:
                    # Insert after other imports
                    pattern = r"(from pathlib import Path\s*\n)"
                    replacement = r"\1\nfrom main import main\n"
                    fixed_frontend_code = re.sub(
                        pattern, replacement, fixed_frontend_code, count=1
                    )
                    logger.info("✅ Added 'from main import main' to app.py")

            elif issue.type == "unused_parameter":
                # Update app.py to pass inputs
                if "main(inputs=user_inputs)" not in fixed_frontend_code:
                    pattern = r"result\s*=\s*main\s*\(\s*\)"
                    replacement = "result = main(inputs=user_inputs)"
                    fixed_frontend_code = re.sub(pattern, replacement, fixed_frontend_code)
                    logger.info("✅ Updated app.py to pass inputs to main()")

        logger.info("✅ Auto-fix complete")

        return IntegratedResult(
            backend_files=fixed_backend_files,
            frontend_files={"app.py": fixed_frontend_code},
            test_files={},
            all_files={**fixed_backend_files, "app.py": fixed_frontend_code},
        )
