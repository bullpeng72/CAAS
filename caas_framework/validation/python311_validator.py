"""
Python 3.11 Compatibility Validator

Validates generated code for Python 3.11 compatibility.
"""

import ast
import re
import sys
from typing import Dict, List

from caas_framework.models.validation import ValidationIssue, ValidationResult


class Python311Validator:
    """
    Python 3.11 Environment Validator

    Validates that generated code is compatible with Python 3.11:
    - Checks for deprecated features removed in 3.11
    - Validates new feature usage
    - Ensures type hint compatibility
    - Verifies syntax compatibility
    """

    # Features removed or deprecated in Python 3.11
    DEPRECATED_FEATURES = {
        r"collections\.Callable": {
            "replacement": "collections.abc.Callable",
            "message": "collections.Callable removed in Python 3.10+, use collections.abc.Callable",
            "severity": "error",
        },
        r"typing\.io": {
            "replacement": "typing.IO",
            "message": "typing.io deprecated, use typing.IO",
            "severity": "warning",
        },
        r"inspect\.getargspec": {
            "replacement": "inspect.signature",
            "message": "inspect.getargspec removed in Python 3.11, use inspect.signature",
            "severity": "error",
        },
        r"asyncio\.coroutine": {
            "replacement": "async def",
            "message": "@asyncio.coroutine decorator removed, use async def",
            "severity": "error",
        },
        r"loop\.create_task\(coro\(\)\)": {
            "replacement": "asyncio.create_task(coro())",
            "message": "Deprecated pattern, use asyncio.create_task()",
            "severity": "warning",
        },
    }

    # Python 3.11 specific features to validate correct usage
    NEW_FEATURES_PATTERNS = {
        r"except\*": {
            "name": "Exception Groups (PEP 654)",
            "check": "verify_exception_group_usage",
        },
        r"from __future__ import annotations": {
            "name": "PEP 563 - Postponed annotation evaluation",
            "check": "verify_future_annotations",
        },
    }

    def __init__(self):
        """Initialize validator"""
        self.current_python_version = f"{sys.version_info.major}.{sys.version_info.minor}"

    def validate(self, files: Dict[str, str]) -> ValidationResult:
        """
        Validate Python 3.11 compatibility

        Args:
            files: Dict of file paths to file contents

        Returns:
            ValidationResult with issues found
        """
        issues = []

        # 1. Check Python version
        version_issues = self._check_python_version()
        issues.extend(version_issues)

        # 2. Check deprecated features
        for filepath, content in files.items():
            if filepath.endswith(".py"):
                issues.extend(self._check_deprecated_features(filepath, content))
                issues.extend(self._check_type_hints(filepath, content))
                issues.extend(self._check_syntax_compatibility(filepath, content))
                issues.extend(self._check_encoding(filepath, content))

        return ValidationResult(
            is_valid=len([i for i in issues if i.severity == "error"]) == 0, issues=issues
        )

    def _check_python_version(self) -> List[ValidationIssue]:
        """Check if running Python 3.11"""
        issues = []

        if sys.version_info.major != 3 or sys.version_info.minor != 11:
            issues.append(
                ValidationIssue(
                    severity="warning",
                    issue_type="python_version",
                    message=f"Framework targets Python 3.11, but running {self.current_python_version}. "
                    f"Generated code may not be fully compatible.",
                    suggested_fix="Use Python 3.11 environment",
                )
            )

        return issues

    def _check_deprecated_features(self, filepath: str, content: str) -> List[ValidationIssue]:
        """Check for deprecated features removed in Python 3.11"""
        issues = []

        for pattern, info in self.DEPRECATED_FEATURES.items():
            matches = list(re.finditer(pattern, content))

            for match in matches:
                # Calculate line number
                line_num = content[: match.start()].count("\n") + 1

                issues.append(
                    ValidationIssue(
                        severity=info["severity"],
                        issue_type="deprecated_feature",
                        message=info["message"],
                        file=filepath,
                        line=line_num,
                        suggested_fix=info["replacement"],
                    )
                )

        return issues

    def _check_type_hints(self, filepath: str, content: str) -> List[ValidationIssue]:
        """Validate type hint compatibility with Python 3.11"""
        issues = []

        try:
            tree = ast.parse(content)

            # Check for Union type syntax (X | Y)
            # This is valid in 3.10+, but requires from __future__ import annotations in 3.9
            for node in ast.walk(tree):
                # Check for BinOp with BitOr in annotation context
                if isinstance(node, ast.FunctionDef):
                    # Check return annotation
                    if node.returns and self._contains_union_syntax(node.returns):
                        # Verify __future__ import exists if needed
                        if not self._has_future_annotations(tree):
                            issues.append(
                                ValidationIssue(
                                    severity="info",
                                    issue_type="type_hint_syntax",
                                    message=f"Using | for Union types in {node.name}. "
                                    f"Consider adding 'from __future__ import annotations' for better compatibility",
                                    file=filepath,
                                    line=node.lineno,
                                    suggested_fix="Add: from __future__ import annotations",
                                )
                            )

        except SyntaxError:
            # Syntax errors are handled by syntax validator
            pass

        return issues

    def _contains_union_syntax(self, node: ast.AST) -> bool:
        """Check if annotation contains | (Union) syntax"""
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            return True

        for child in ast.walk(node):
            if isinstance(child, ast.BinOp) and isinstance(child.op, ast.BitOr):
                return True

        return False

    def _has_future_annotations(self, tree: ast.AST) -> bool:
        """Check if module has 'from __future__ import annotations'"""
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module == "__future__":
                    for alias in node.names:
                        if alias.name == "annotations":
                            return True
        return False

    def _check_syntax_compatibility(self, filepath: str, content: str) -> List[ValidationIssue]:
        """Check for syntax that may not work in Python 3.11"""
        issues = []

        # Check for f-string expressions with backslashes (not allowed)
        # Python 3.12 allows this, but 3.11 doesn't
        fstring_pattern = r'f["\'][^"\']*\\[^"\']*["\']'
        matches = re.finditer(fstring_pattern, content)

        for match in matches:
            line_num = content[: match.start()].count("\n") + 1
            issues.append(
                ValidationIssue(
                    severity="warning",
                    issue_type="fstring_backslash",
                    message="f-string contains backslash which may cause issues",
                    file=filepath,
                    line=line_num,
                    suggested_fix="Extract backslash to variable or use raw string",
                )
            )

        return issues

    def _check_encoding(self, filepath: str, content: str) -> List[ValidationIssue]:
        """Check file encoding (Python 3.11 defaults to UTF-8)"""
        issues = []

        # Check for non-UTF-8 encoding declaration
        encoding_pattern = r"#.*?coding[:=]\s*([-\w.]+)"
        match = re.search(encoding_pattern, content[:200])  # Check first 2 lines

        if match:
            encoding = match.group(1).lower()
            if encoding not in ("utf-8", "utf8"):
                issues.append(
                    ValidationIssue(
                        severity="warning",
                        issue_type="encoding",
                        message=f"File uses {encoding} encoding. Python 3.11 defaults to UTF-8",
                        file=filepath,
                        line=1,
                        suggested_fix="Use UTF-8 encoding or remove encoding declaration",
                    )
                )

        return issues

    def get_validation_summary(self, result: ValidationResult) -> str:
        """Generate human-readable validation summary"""
        lines = []
        lines.append("=" * 70)
        lines.append("Python 3.11 Compatibility Validation")
        lines.append("=" * 70)

        if result.is_valid:
            lines.append("✅ All checks passed - Code is Python 3.11 compatible")
        else:
            lines.append(f"❌ Found {result.error_count} errors, {result.warning_count} warnings")

        if result.issues:
            lines.append("\nIssues:")
            for issue in result.issues:
                icon = (
                    "❌"
                    if issue.severity == "error"
                    else "⚠️" if issue.severity == "warning" else "ℹ️"
                )
                location = f"{issue.file}:{issue.line}" if issue.file and issue.line else "general"
                lines.append(f"  {icon} [{issue.severity.upper()}] {location}")
                lines.append(f"     {issue.message}")
                if issue.suggested_fix:
                    lines.append(f"     💡 Fix: {issue.suggested_fix}")

        lines.append("=" * 70)
        return "\n".join(lines)
