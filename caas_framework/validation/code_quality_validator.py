"""
Code Quality Validator (v0.4.2)

Validates generated code quality and provides auto-fix suggestions.

Features:
- Frontend code quality checks (4 critical checks)
- Backend code quality checks
- Auto-fix suggestions
- Fallback trigger on quality failure
"""

import re
from dataclasses import dataclass
from typing import List, Optional

from caas_framework.utils.logger import get_logger

logger = get_logger()


@dataclass
class ValidationIssue:
    """Represents a code quality issue."""

    check_name: str
    severity: str  # "critical", "warning", "info"
    message: str
    location: Optional[str] = None  # File name or line number
    auto_fix: Optional[str] = None  # Suggested fix


@dataclass
class ValidationResult:
    """Result of code quality validation."""

    passed: bool
    issues: List[ValidationIssue]
    score: float  # 0.0 - 10.0
    use_fallback: bool = False  # Trigger fallback if True


class CodeQualityValidator:
    """
    Validates generated code quality.

    Focuses on critical issues that cause runtime failures:
    - Missing input widgets (frontend)
    - Missing inputs parameter in main() calls
    - Missing input validation
    - Missing error handling
    """

    def __init__(self):
        self.logger = logger

    def validate_frontend(
        self, app_code: str, main_code: str, framework: str = "streamlit"
    ) -> ValidationResult:
        """
        Validate frontend code quality.

        Args:
            app_code: Contents of app.py
            main_code: Contents of main.py
            framework: Frontend framework (default: "streamlit")

        Returns:
            ValidationResult with issues and score
        """
        issues = []

        if framework == "streamlit":
            # Check 1: Input widgets exist
            widget_issue = self._check_input_widgets(app_code)
            if widget_issue:
                issues.append(widget_issue)

            # Check 2: main() called with inputs
            main_call_issue = self._check_main_call(app_code)
            if main_call_issue:
                issues.append(main_call_issue)

            # Check 3: Input validation exists
            validation_issue = self._check_input_validation(app_code)
            if validation_issue:
                issues.append(validation_issue)

            # Check 4: Error handling exists
            error_handling_issue = self._check_error_handling(app_code)
            if error_handling_issue:
                issues.append(error_handling_issue)

            # Check 5: main.py accepts inputs parameter
            main_signature_issue = self._check_main_signature(main_code)
            if main_signature_issue:
                issues.append(main_signature_issue)

        # Calculate score
        critical_issues = [i for i in issues if i.severity == "critical"]
        warning_issues = [i for i in issues if i.severity == "warning"]

        score = 10.0
        score -= len(critical_issues) * 3.0  # -3 per critical
        score -= len(warning_issues) * 1.0  # -1 per warning
        score = max(0.0, score)

        # Determine if fallback should be used
        use_fallback = len(critical_issues) > 0 or score < 5.0

        passed = len(critical_issues) == 0

        if not passed:
            self.logger.warning(
                f"Frontend validation failed: {len(critical_issues)} critical issues, "
                f"score={score:.1f}/10.0"
            )
        else:
            self.logger.info(f"Frontend validation passed: score={score:.1f}/10.0")

        return ValidationResult(
            passed=passed, issues=issues, score=score, use_fallback=use_fallback
        )

    def _check_input_widgets(self, app_code: str) -> Optional[ValidationIssue]:
        """Check if input widgets are present in app.py."""

        # Common Streamlit input widgets
        widget_patterns = [
            r"st\.text_input\(",
            r"st\.number_input\(",
            r"st\.text_area\(",
            r"st\.selectbox\(",
            r"st\.multiselect\(",
            r"st\.slider\(",
            r"st\.date_input\(",
        ]

        has_widgets = any(re.search(pattern, app_code) for pattern in widget_patterns)

        if not has_widgets:
            # Check if there's an empty input section (common mistake)
            empty_input_section = re.search(
                r"# Input section\s*\n\s*\n\s*st\.markdown", app_code
            )

            if empty_input_section:
                return ValidationIssue(
                    check_name="input_widgets",
                    severity="critical",
                    message="Input section is EMPTY - no input widgets found (st.text_input, etc.)",
                    location="app.py",
                    auto_fix="Add input widgets like: keyword = st.text_input('Keyword:', key='keyword')",
                )
            else:
                return ValidationIssue(
                    check_name="input_widgets",
                    severity="critical",
                    message="No input widgets found in app.py - users cannot provide inputs",
                    location="app.py",
                    auto_fix="Add input widgets based on task requirements",
                )

        return None

    def _check_main_call(self, app_code: str) -> Optional[ValidationIssue]:
        """Check if main() is called with inputs parameter."""

        # Pattern: main(inputs=...) or main(inputs = ...)
        correct_call = re.search(r"main\s*\(\s*inputs\s*=", app_code)

        if not correct_call:
            # Check if main() is called without inputs
            wrong_call = re.search(r"result\s*=\s*main\s*\(\s*\)", app_code)

            if wrong_call:
                return ValidationIssue(
                    check_name="main_call",
                    severity="critical",
                    message="main() called WITHOUT inputs parameter - will not pass user inputs to backend",
                    location="app.py",
                    auto_fix="Change 'result = main()' to 'result = main(inputs=user_inputs)'",
                )
            else:
                return ValidationIssue(
                    check_name="main_call",
                    severity="warning",
                    message="Could not verify main() call pattern",
                    location="app.py",
                )

        return None

    def _check_input_validation(self, app_code: str) -> Optional[ValidationIssue]:
        """Check if input validation exists."""

        # Pattern: if not variable: or if any(not val for val in ...)
        validation_patterns = [
            r"if\s+not\s+\w+:",  # if not keyword:
            r"if\s+any\(",  # if any(...)
            r"st\.error\(",  # st.error() usually indicates validation
        ]

        has_validation = any(
            re.search(pattern, app_code) for pattern in validation_patterns
        )

        if not has_validation:
            return ValidationIssue(
                check_name="input_validation",
                severity="warning",
                message="No input validation found - users can submit empty inputs",
                location="app.py",
                auto_fix="Add: if not keyword: st.error('Please enter keyword')",
            )

        # Check for empty list validation (common mistake)
        empty_list_validation = re.search(r"if\s+any\([^)]*\[\s*\]\)", app_code)
        if empty_list_validation:
            return ValidationIssue(
                check_name="input_validation",
                severity="critical",
                message="WRONG validation pattern: if any(not val for val in []) - empty list always passes",
                location="app.py",
                auto_fix="Replace with specific variable checks: if not keyword:",
            )

        return None

    def _check_error_handling(self, app_code: str) -> Optional[ValidationIssue]:
        """Check if error handling exists."""

        # Pattern: try-except with st.error()
        has_try_except = re.search(r"try\s*:", app_code) and re.search(
            r"except\s+\w*Exception", app_code
        )

        has_error_display = re.search(r"st\.error\(", app_code)

        if not has_try_except:
            return ValidationIssue(
                check_name="error_handling",
                severity="warning",
                message="No try-except block found - errors will crash the app",
                location="app.py",
                auto_fix="Wrap crew execution in try-except block",
            )

        if has_try_except and not has_error_display:
            return ValidationIssue(
                check_name="error_handling",
                severity="info",
                message="Error handling exists but errors not displayed to user",
                location="app.py",
                auto_fix="Add st.error(f'Error: {e}') in except block",
            )

        return None

    def _check_main_signature(self, main_code: str) -> Optional[ValidationIssue]:
        """Check if main() function accepts inputs parameter."""

        # Pattern: def main(inputs=None): or def main(inputs: Optional[Dict] = None):
        correct_signature = re.search(
            r"def\s+main\s*\(\s*inputs\s*[=:]", main_code, re.MULTILINE
        )

        if not correct_signature:
            # Check if main() has no parameters
            no_params = re.search(r"def\s+main\s*\(\s*\)\s*:", main_code, re.MULTILINE)

            if no_params:
                return ValidationIssue(
                    check_name="main_signature",
                    severity="critical",
                    message="main() function does NOT accept inputs parameter - frontend cannot pass user inputs",
                    location="main.py",
                    auto_fix="Change 'def main():' to 'def main(inputs=None):'",
                )

        return None

    def validate_backend(self, main_code: str) -> ValidationResult:
        """
        Validate backend code quality.

        Args:
            main_code: Contents of main.py

        Returns:
            ValidationResult
        """
        issues = []

        # Check 1: crew.kickoff() called with inputs
        kickoff_issue = self._check_kickoff_inputs(main_code)
        if kickoff_issue:
            issues.append(kickoff_issue)

        # Check 2: inputs parameter is used
        inputs_usage_issue = self._check_inputs_usage(main_code)
        if inputs_usage_issue:
            issues.append(inputs_usage_issue)

        # Calculate score
        critical_issues = [i for i in issues if i.severity == "critical"]
        score = 10.0 - len(critical_issues) * 3.0
        score = max(0.0, score)

        passed = len(critical_issues) == 0
        use_fallback = not passed

        return ValidationResult(
            passed=passed, issues=issues, score=score, use_fallback=use_fallback
        )

    def _check_kickoff_inputs(self, main_code: str) -> Optional[ValidationIssue]:
        """Check if crew.kickoff() is called with inputs parameter."""

        # Pattern: crew.kickoff(inputs=user_inputs)
        correct_kickoff = re.search(r"crew\.kickoff\s*\(\s*inputs\s*=", main_code)

        if not correct_kickoff:
            # Check if kickoff() called without inputs
            wrong_kickoff = re.search(r"crew\.kickoff\s*\(\s*\)", main_code)

            if wrong_kickoff:
                return ValidationIssue(
                    check_name="kickoff_inputs",
                    severity="critical",
                    message="crew.kickoff() called WITHOUT inputs - user inputs will not be passed to agents",
                    location="main.py",
                    auto_fix="Change 'crew.kickoff()' to 'crew.kickoff(inputs=user_inputs)'",
                )

        return None

    def _check_inputs_usage(self, main_code: str) -> Optional[ValidationIssue]:
        """Check if inputs parameter is actually used in main()."""

        # Check if main(inputs=None) exists
        has_inputs_param = re.search(r"def\s+main\s*\(\s*inputs\s*=", main_code)

        if has_inputs_param:
            # Check if inputs is used in the function body
            has_if_inputs_none = re.search(r"if\s+inputs\s+is\s+None", main_code)
            has_user_inputs_assignment = re.search(
                r"user_inputs\s*=\s*inputs", main_code
            )

            if not (has_if_inputs_none or has_user_inputs_assignment):
                return ValidationIssue(
                    check_name="inputs_usage",
                    severity="critical",
                    message="main() accepts inputs parameter but does NOT use it",
                    location="main.py",
                    auto_fix="Add: if inputs is None: collect_cli_inputs() else: user_inputs = inputs",
                )

        return None

    def format_validation_report(self, result: ValidationResult) -> str:
        """
        Format validation result as human-readable report.

        Args:
            result: ValidationResult

        Returns:
            Formatted report string
        """
        lines = []
        lines.append("\n" + "=" * 70)
        lines.append("📋 CODE QUALITY VALIDATION REPORT")
        lines.append("=" * 70)

        # Overall status
        status = "✅ PASSED" if result.passed else "❌ FAILED"
        lines.append(f"\nStatus: {status}")
        lines.append(f"Score: {result.score:.1f}/10.0")
        lines.append(f"Use Fallback: {'Yes' if result.use_fallback else 'No'}")

        # Issues breakdown
        if result.issues:
            lines.append(f"\nIssues Found: {len(result.issues)}")

            critical = [i for i in result.issues if i.severity == "critical"]
            warning = [i for i in result.issues if i.severity == "warning"]
            info = [i for i in result.issues if i.severity == "info"]

            if critical:
                lines.append(f"\n🔴 CRITICAL ({len(critical)}):")
                for issue in critical:
                    lines.append(f"  - [{issue.location}] {issue.message}")
                    if issue.auto_fix:
                        lines.append(f"    💡 Fix: {issue.auto_fix}")

            if warning:
                lines.append(f"\n🟡 WARNING ({len(warning)}):")
                for issue in warning:
                    lines.append(f"  - [{issue.location}] {issue.message}")
                    if issue.auto_fix:
                        lines.append(f"    💡 Fix: {issue.auto_fix}")

            if info:
                lines.append(f"\n🔵 INFO ({len(info)}):")
                for issue in info:
                    lines.append(f"  - [{issue.location}] {issue.message}")
        else:
            lines.append("\n✨ No issues found!")

        lines.append("\n" + "=" * 70)

        return "\n".join(lines)

    def apply_fixes(
        self,
        app_code: str,
        main_code: str,
        issues: List[ValidationIssue],
    ) -> tuple[str, str, int]:
        """
        ✅ v0.5.0: Apply auto-fixes to code based on validation issues.

        Args:
            app_code: Contents of app.py
            main_code: Contents of main.py
            issues: List of validation issues with auto_fix suggestions

        Returns:
            (fixed_app_code, fixed_main_code, fixes_applied_count)
        """
        fixed_app = app_code
        fixed_main = main_code
        fixes_applied = 0

        for issue in issues:
            # Only apply critical and error severity fixes
            if issue.severity not in ("critical", "error"):
                continue

            try:
                if issue.check_name == "input_widgets":
                    fixed_app = self._fix_missing_input_widgets(fixed_app, issue)
                    fixes_applied += 1
                    self.logger.info(f"✅ Applied fix for {issue.check_name}")

                elif issue.check_name == "main_call":
                    fixed_app = self._fix_main_call(fixed_app, issue)
                    fixes_applied += 1
                    self.logger.info(f"✅ Applied fix for {issue.check_name}")

                elif issue.check_name == "input_validation":
                    fixed_app = self._fix_validation_pattern(fixed_app, issue)
                    fixes_applied += 1
                    self.logger.info(f"✅ Applied fix for {issue.check_name}")

                elif issue.check_name == "main_signature":
                    fixed_main = self._fix_main_signature(fixed_main, issue)
                    fixes_applied += 1
                    self.logger.info(f"✅ Applied fix for {issue.check_name}")

                elif issue.check_name == "kickoff_inputs":
                    fixed_main = self._fix_kickoff_inputs(fixed_main, issue)
                    fixes_applied += 1
                    self.logger.info(f"✅ Applied fix for {issue.check_name}")

            except Exception as e:
                self.logger.warning(f"⚠️  Failed to apply fix for {issue.check_name}: {e}")

        return fixed_app, fixed_main, fixes_applied

    def _fix_missing_input_widgets(self, app_code: str, issue: ValidationIssue) -> str:
        """
        Fix missing input widgets by injecting widget code.

        Inserts widget code after "# Input section" comment.
        """
        # Extract widget code from auto_fix message
        # Format: "Add input widgets like: keyword = st.text_input('Keyword:', key='keyword')"

        # For now, use a generic fix - in production, parse issue.details for specifics
        widget_code = "keyword = st.text_input(\"검색 키워드:\", key=\"keyword\", placeholder=\"예: AI 기술 동향\")"

        # Find insertion point: after "# Input section"
        pattern = r"(# Input section\s*\n)"
        replacement = rf"\1{widget_code}\n\n"

        fixed_code = re.sub(pattern, replacement, app_code, count=1)

        # Verify fix was applied
        if widget_code not in fixed_code:
            self.logger.warning("⚠️  Widget code was not inserted - pattern not found")
            return app_code

        return fixed_code

    def _fix_main_call(self, app_code: str, issue: ValidationIssue) -> str:
        """
        Fix main() call to include inputs parameter.

        Changes:
          result = main()
        To:
          result = main(inputs=user_inputs)
        """
        # Pattern: result = main()
        pattern = r"result\s*=\s*main\s*\(\s*\)"
        replacement = "result = main(inputs=user_inputs)"

        fixed_code = re.sub(pattern, replacement, app_code)

        # Verify fix was applied
        if "main(inputs=user_inputs)" not in fixed_code and "main(inputs=" not in fixed_code:
            self.logger.warning("⚠️  main() call fix not applied - pattern not found")
            return app_code

        return fixed_code

    def _fix_validation_pattern(self, app_code: str, issue: ValidationIssue) -> str:
        """
        Fix wrong validation pattern.

        Changes:
          if any(not val for val in []):  # Empty list
        To:
          if not keyword:  # Specific variable check
        """
        # Pattern: if any(not val for val in [...]):
        # Replace with: if not keyword:

        pattern = r"if\s+any\s*\(\s*not\s+val\s+for\s+val\s+in\s+\[[^\]]*\]\s*\)\s*:"
        replacement = "if not keyword:"

        fixed_code = re.sub(pattern, replacement, app_code)

        return fixed_code

    def _fix_main_signature(self, main_code: str, issue: ValidationIssue) -> str:
        """
        Fix main() function signature to accept inputs parameter.

        Changes:
          def main():
        To:
          def main(inputs=None):
        """
        # Pattern: def main():
        pattern = r"def\s+main\s*\(\s*\)\s*:"
        replacement = "def main(inputs=None):"

        fixed_code = re.sub(pattern, replacement, main_code, count=1)

        # Verify fix was applied
        if "def main(inputs=" not in fixed_code:
            self.logger.warning("⚠️  main signature fix not applied - pattern not found")
            return main_code

        return fixed_code

    def _fix_kickoff_inputs(self, main_code: str, issue: ValidationIssue) -> str:
        """
        Fix crew.kickoff() call to include inputs parameter.

        Changes:
          result = crew.kickoff()
          result = crew . kickoff()  # ✅ v0.5.2: Also handles whitespace around dot
        To:
          result = crew.kickoff(inputs=user_inputs)
        """
        # ✅ v0.5.2: Enhanced pattern to handle whitespace around dot
        # Matches: crew.kickoff(), crew . kickoff(), crew  .  kickoff()
        pattern = r"crew\s*\.\s*kickoff\s*\(\s*\)"
        replacement = "crew.kickoff(inputs=user_inputs)"

        fixed_code = re.sub(pattern, replacement, main_code)

        return fixed_code
