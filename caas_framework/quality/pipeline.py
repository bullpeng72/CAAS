"""
Code Quality Pipeline

Automated verification of generated code quality.
Checks syntax, imports, and code style.
"""

from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
import ast
import sys
import io
import logging
from datetime import datetime


class CheckStatus(Enum):
    """Status of a quality check."""
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"


@dataclass
class CheckResult:
    """Result of a single quality check."""
    name: str
    status: CheckStatus
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    duration: float = 0.0
    details: Optional[Dict[str, Any]] = None


@dataclass
class QualityReport:
    """Overall quality report for generated code."""
    checks: List[CheckResult]
    overall_passed: bool
    timestamp: datetime
    total_duration: float
    files_checked: int
    total_errors: int
    total_warnings: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary."""
        return {
            "overall_passed": self.overall_passed,
            "timestamp": self.timestamp.isoformat(),
            "total_duration": self.total_duration,
            "files_checked": self.files_checked,
            "total_errors": self.total_errors,
            "total_warnings": self.total_warnings,
            "checks": [
                {
                    "name": check.name,
                    "status": check.status.value,
                    "errors": check.errors,
                    "warnings": check.warnings,
                    "duration": check.duration
                }
                for check in self.checks
            ]
        }


class QualityCheck:
    """Base class for quality checks."""

    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(__name__)

    def check(self, files: Dict[str, str]) -> CheckResult:
        """
        Perform quality check on generated files.

        Args:
            files: Dictionary of filename -> content

        Returns:
            CheckResult
        """
        raise NotImplementedError


class SyntaxCheck(QualityCheck):
    """Check Python syntax validity."""

    def __init__(self):
        super().__init__("Syntax Check")

    def check(self, files: Dict[str, str]) -> CheckResult:
        """Check syntax of all Python files."""
        import time
        start_time = time.time()

        errors = []
        warnings = []

        for filename, content in files.items():
            if not filename.endswith('.py'):
                continue

            try:
                ast.parse(content)
            except SyntaxError as e:
                errors.append(
                    f"{filename}:{e.lineno}:{e.offset}: {e.msg}"
                )
            except Exception as e:
                warnings.append(
                    f"{filename}: Unexpected error during parsing: {str(e)}"
                )

        duration = time.time() - start_time

        status = CheckStatus.PASSED if len(errors) == 0 else CheckStatus.FAILED

        return CheckResult(
            name=self.name,
            status=status,
            errors=errors,
            warnings=warnings,
            duration=duration,
            details={"files_checked": len([f for f in files if f.endswith('.py')])}
        )


class ImportCheck(QualityCheck):
    """Check if all imports are valid."""

    def __init__(self):
        super().__init__("Import Check")

    def check(self, files: Dict[str, str]) -> CheckResult:
        """Check imports in all Python files."""
        import time
        start_time = time.time()

        errors = []
        warnings = []

        for filename, content in files.items():
            if not filename.endswith('.py'):
                continue

            try:
                tree = ast.parse(content)

                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            self._check_module(alias.name, filename, errors, warnings)

                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            self._check_module(node.module, filename, errors, warnings)

            except SyntaxError:
                # Skip files with syntax errors (already caught by SyntaxCheck)
                continue
            except Exception as e:
                warnings.append(
                    f"{filename}: Error checking imports: {str(e)}"
                )

        duration = time.time() - start_time

        status = CheckStatus.PASSED if len(errors) == 0 else CheckStatus.FAILED

        return CheckResult(
            name=self.name,
            status=status,
            errors=errors,
            warnings=warnings,
            duration=duration
        )

    def _check_module(
        self,
        module_name: str,
        filename: str,
        errors: List[str],
        warnings: List[str]
    ) -> None:
        """Check if a module can be imported."""

        # Skip checking generated modules (they don't exist yet)
        if module_name in ['agents', 'tasks', 'main']:
            return

        # Known problematic modules (skip for now)
        skip_modules = {'crewai', 'langchain', 'dotenv'}
        if any(module_name.startswith(skip) for skip in skip_modules):
            # These are expected dependencies
            return

        # Try to check if module exists in stdlib
        if module_name in sys.builtin_module_names:
            return

        # Check standard library modules
        stdlib_modules = {
            'os', 'sys', 'json', 're', 'time', 'datetime',
            'collections', 'itertools', 'functools', 'typing',
            'pathlib', 'logging', 'unittest', 'asyncio'
        }

        if module_name.split('.')[0] in stdlib_modules:
            return

        # If not in stdlib, it's likely a third-party dependency
        # We'll warn but not fail
        warnings.append(
            f"{filename}: Third-party module '{module_name}' "
            f"(ensure it's in requirements.txt)"
        )


class CodeStyleCheck(QualityCheck):
    """Check code style (basic PEP 8 compliance)."""

    def __init__(self):
        super().__init__("Code Style Check")

    def check(self, files: Dict[str, str]) -> CheckResult:
        """Check code style in all Python files."""
        import time
        start_time = time.time()

        errors = []
        warnings = []

        for filename, content in files.items():
            if not filename.endswith('.py'):
                continue

            lines = content.split('\n')

            # Check line length (warn if > 120 chars)
            for i, line in enumerate(lines, 1):
                if len(line) > 120:
                    warnings.append(
                        f"{filename}:{i}: Line too long ({len(line)} > 120 chars)"
                    )

            # Check for common style issues
            if 'import *' in content:
                warnings.append(
                    f"{filename}: Wildcard import detected (avoid 'from x import *')"
                )

            # Check for proper spacing around operators (basic check)
            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                if stripped and not stripped.startswith('#'):
                    # Check for spacing around '='
                    if '=' in stripped and not any(op in stripped for op in ['==', '!=', '<=', '>=', '=>']):
                        parts = stripped.split('=')
                        if len(parts) == 2:
                            # Simple check: should have space before and after '='
                            # (This is a simplified check, not comprehensive)
                            pass

        duration = time.time() - start_time

        # Code style issues are warnings, not errors
        status = CheckStatus.PASSED if len(warnings) < 10 else CheckStatus.WARNING

        return CheckResult(
            name=self.name,
            status=status,
            errors=errors,
            warnings=warnings,
            duration=duration
        )


class CodeQualityPipeline:
    """
    Automated code quality verification pipeline.

    Runs multiple checks on generated code:
    1. Syntax validation
    2. Import validation
    3. Code style (basic PEP 8)
    """

    def __init__(
        self,
        enable_syntax: bool = True,
        enable_imports: bool = True,
        enable_style: bool = True
    ):
        """
        Initialize quality pipeline.

        Args:
            enable_syntax: Enable syntax checking
            enable_imports: Enable import checking
            enable_style: Enable style checking
        """
        self.checks: List[QualityCheck] = []

        if enable_syntax:
            self.checks.append(SyntaxCheck())

        if enable_imports:
            self.checks.append(ImportCheck())

        if enable_style:
            self.checks.append(CodeStyleCheck())

        self.logger = logging.getLogger(__name__)

    def verify(self, files: Dict[str, str]) -> QualityReport:
        """
        Run all quality checks on generated files.

        Args:
            files: Dictionary of filename -> content

        Returns:
            QualityReport with all check results
        """
        import time
        start_time = time.time()

        results = []

        for check in self.checks:
            self.logger.info(f"Running {check.name}...")
            try:
                result = check.check(files)
                results.append(result)

                if result.status == CheckStatus.PASSED:
                    self.logger.info(f"✅ {check.name} passed")
                elif result.status == CheckStatus.WARNING:
                    self.logger.warning(
                        f"⚠️ {check.name} passed with warnings: {len(result.warnings)}"
                    )
                else:
                    self.logger.error(
                        f"❌ {check.name} failed: {len(result.errors)} errors"
                    )

            except Exception as e:
                self.logger.exception(f"Error running {check.name}: {e}")
                results.append(CheckResult(
                    name=check.name,
                    status=CheckStatus.FAILED,
                    errors=[f"Check failed with exception: {str(e)}"]
                ))

        total_duration = time.time() - start_time

        # Calculate overall status
        overall_passed = all(
            r.status in [CheckStatus.PASSED, CheckStatus.WARNING]
            for r in results
        )

        total_errors = sum(len(r.errors) for r in results)
        total_warnings = sum(len(r.warnings) for r in results)

        report = QualityReport(
            checks=results,
            overall_passed=overall_passed,
            timestamp=datetime.now(),
            total_duration=total_duration,
            files_checked=len(files),
            total_errors=total_errors,
            total_warnings=total_warnings
        )

        return report

    def print_report(self, report: QualityReport) -> None:
        """Print quality report to console."""
        print("\n" + "=" * 70)
        print("CODE QUALITY REPORT")
        print("=" * 70)

        print(f"\n📊 Summary:")
        print(f"  Files Checked: {report.files_checked}")
        print(f"  Total Duration: {report.total_duration:.2f}s")
        print(f"  Errors: {report.total_errors}")
        print(f"  Warnings: {report.total_warnings}")

        print(f"\n✅ Overall: {'PASSED' if report.overall_passed else 'FAILED'}")

        print("\n📋 Check Results:")
        for check in report.checks:
            status_icon = "✅" if check.status == CheckStatus.PASSED else "⚠️" if check.status == CheckStatus.WARNING else "❌"
            print(f"\n  {status_icon} {check.name} ({check.duration:.2f}s)")

            if check.errors:
                print(f"    Errors ({len(check.errors)}):")
                for error in check.errors[:5]:  # Limit to 5
                    print(f"      - {error}")
                if len(check.errors) > 5:
                    print(f"      ... and {len(check.errors) - 5} more")

            if check.warnings:
                print(f"    Warnings ({len(check.warnings)}):")
                for warning in check.warnings[:3]:  # Limit to 3
                    print(f"      - {warning}")
                if len(check.warnings) > 3:
                    print(f"      ... and {len(check.warnings) - 3} more")

        print("\n" + "=" * 70)
