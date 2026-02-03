"""
Code Security Scanner - Static Analysis for Generated Code

Scans generated code for security vulnerabilities using:
1. Bandit - Python static security analyzer
2. Safety - Dependency vulnerability scanner
3. Secret Detection - Find hardcoded secrets
"""

import json
import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional


class Severity(str, Enum):
    """Security issue severity levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IssueType(str, Enum):
    """Types of security issues"""

    VULNERABILITY = "vulnerability"  # Code vulnerability
    SECRET = "secret"  # Hardcoded secret
    DEPENDENCY = "dependency"  # Vulnerable dependency
    BEST_PRACTICE = "best_practice"  # Security best practice violation


@dataclass
class SecurityIssue:
    """A single security issue"""

    type: IssueType
    severity: Severity
    file_path: str
    line_number: Optional[int]
    issue_text: str
    confidence: str = "HIGH"  # LOW, MEDIUM, HIGH
    cwe_id: Optional[str] = None  # Common Weakness Enumeration ID

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "type": self.type.value,
            "severity": self.severity.value,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "issue_text": self.issue_text,
            "confidence": self.confidence,
            "cwe_id": self.cwe_id,
        }


@dataclass
class SecurityReport:
    """Security scan report"""

    is_safe: bool
    total_issues: int
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    issues: List[SecurityIssue] = field(default_factory=list)
    scan_timestamp: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "is_safe": self.is_safe,
            "total_issues": self.total_issues,
            "critical_count": self.critical_count,
            "high_count": self.high_count,
            "medium_count": self.medium_count,
            "low_count": self.low_count,
            "issues": [issue.to_dict() for issue in self.issues],
            "scan_timestamp": self.scan_timestamp,
        }


class CodeSecurityScanner:
    """
    Security scanner for generated code

    Features:
    - Bandit integration for Python static analysis
    - Secret detection (API keys, passwords, tokens)
    - Dependency vulnerability scanning
    - CWE (Common Weakness Enumeration) mapping
    """

    # Common secret patterns
    SECRET_PATTERNS = {
        "api_key": (
            r'(?i)(api[_-]?key|apikey|api[_-]?secret)\s*[=:]\s*["\']([a-zA-Z0-9_\-]{20,})["\']',
            "Hardcoded API key detected",
        ),
        "password": (
            r'(?i)(password|passwd|pwd)\s*[=:]\s*["\']([^"\']{4,})["\']',
            "Hardcoded password detected",
        ),
        "aws_key": (r"AKIA[0-9A-Z]{16}", "AWS Access Key ID detected"),
        "private_key": (r"-----BEGIN (RSA |EC )?PRIVATE KEY-----", "Private key detected"),
        "github_token": (r"gh[pousr]_[A-Za-z0-9_]{36,255}", "GitHub token detected"),
        "generic_secret": (
            r'(?i)(secret|token|bearer)\s*[=:]\s*["\']([a-zA-Z0-9_\-]{20,})["\']',
            "Hardcoded secret detected",
        ),
        "database_url": (
            r'(?i)(database_url|db_url|connection_string)\s*=\s*["\'].*:\/\/.*:.*@',
            "Database credentials in connection string",
        ),
    }

    # Dangerous function patterns
    DANGEROUS_PATTERNS = {
        "eval": (
            r"\beval\s*\(",
            "Use of eval() is dangerous",
            Severity.HIGH,
            "CWE-95",  # Improper Neutralization of Directives in Dynamically Evaluated Code
        ),
        "exec": (r"\bexec\s*\(", "Use of exec() is dangerous", Severity.HIGH, "CWE-95"),
        "pickle": (
            r"import\s+pickle|from\s+pickle\s+import",
            "Pickle usage can lead to arbitrary code execution",
            Severity.MEDIUM,
            "CWE-502",  # Deserialization of Untrusted Data
        ),
        "yaml_unsafe": (
            r"yaml\.load\s*\([^,)]+\)",
            "Use yaml.safe_load() instead of yaml.load()",
            Severity.MEDIUM,
            "CWE-502",
        ),
        "shell_injection": (
            r"os\.(system|popen)\s*\(",
            "Shell injection risk - use subprocess with shell=False",
            Severity.HIGH,
            "CWE-78",  # OS Command Injection
        ),
        "sql_injection": (
            r'(execute|cursor\.execute)\s*\([\'"].*%s.*[\'"].*%',
            "SQL injection risk - use parameterized queries",
            Severity.CRITICAL,
            "CWE-89",  # SQL Injection
        ),
    }

    def __init__(self, use_bandit: bool = True, use_secret_detection: bool = True):
        """
        Initialize security scanner

        Args:
            use_bandit: Whether to use Bandit for static analysis
            use_secret_detection: Whether to scan for hardcoded secrets
        """
        self.use_bandit = use_bandit
        self.use_secret_detection = use_secret_detection
        self._check_dependencies()

    def _check_dependencies(self):
        """Check if required tools are available"""
        if self.use_bandit:
            try:
                subprocess.run(["bandit", "--version"], capture_output=True, check=True, timeout=5)
            except (subprocess.CalledProcessError, FileNotFoundError):
                self.use_bandit = False
                # Bandit not available, will use pattern matching instead

    def scan(
        self, generated_files: Dict[str, str], fail_on_critical: bool = False
    ) -> SecurityReport:
        """
        Scan generated code for security issues

        Args:
            generated_files: Dictionary of {filename: content}
            fail_on_critical: Whether to mark report as unsafe on critical issues

        Returns:
            SecurityReport with all findings
        """
        from datetime import datetime

        all_issues: List[SecurityIssue] = []

        # 1. Pattern-based scanning (always runs)
        pattern_issues = self._scan_with_patterns(generated_files)
        all_issues.extend(pattern_issues)

        # 2. Secret detection
        if self.use_secret_detection:
            secret_issues = self._detect_secrets(generated_files)
            all_issues.extend(secret_issues)

        # 3. Bandit scanning (if available)
        if self.use_bandit:
            bandit_issues = self._scan_with_bandit(generated_files)
            all_issues.extend(bandit_issues)

        # Count by severity
        critical_count = sum(1 for i in all_issues if i.severity == Severity.CRITICAL)
        high_count = sum(1 for i in all_issues if i.severity == Severity.HIGH)
        medium_count = sum(1 for i in all_issues if i.severity == Severity.MEDIUM)
        low_count = sum(1 for i in all_issues if i.severity == Severity.LOW)

        # Determine if safe
        is_safe = True
        if fail_on_critical and critical_count > 0:
            is_safe = False
        elif critical_count + high_count > 10:  # Too many issues
            is_safe = False

        return SecurityReport(
            is_safe=is_safe,
            total_issues=len(all_issues),
            critical_count=critical_count,
            high_count=high_count,
            medium_count=medium_count,
            low_count=low_count,
            issues=all_issues,
            scan_timestamp=datetime.now().isoformat(),
        )

    def _scan_with_patterns(self, files: Dict[str, str]) -> List[SecurityIssue]:
        """Scan code using pattern matching"""
        issues = []

        for filename, content in files.items():
            # Skip non-Python files
            if not filename.endswith(".py"):
                continue

            # Skip metadata fields
            if filename.startswith("_"):
                continue

            lines = content.split("\n")

            for line_num, line in enumerate(lines, 1):
                # Check dangerous patterns
                for pattern_name, (
                    regex,
                    description,
                    severity,
                    cwe,
                ) in self.DANGEROUS_PATTERNS.items():
                    if re.search(regex, line):
                        issues.append(
                            SecurityIssue(
                                type=IssueType.VULNERABILITY,
                                severity=severity,
                                file_path=filename,
                                line_number=line_num,
                                issue_text=f"{description} (Line: {line.strip()[:60]}...)",
                                confidence="MEDIUM",
                                cwe_id=cwe,
                            )
                        )

        return issues

    def _detect_secrets(self, files: Dict[str, str]) -> List[SecurityIssue]:
        """Detect hardcoded secrets in code"""
        issues = []

        for filename, content in files.items():
            # Skip non-code files
            if filename.startswith("_") or not self._is_code_file(filename):
                continue

            lines = content.split("\n")

            for line_num, line in enumerate(lines, 1):
                # Skip comments
                if line.strip().startswith("#"):
                    continue

                # Check secret patterns
                for secret_type, (regex, description) in self.SECRET_PATTERNS.items():
                    matches = re.finditer(regex, line)
                    for match in matches:
                        # Skip if it's a placeholder
                        matched_value = match.group(0)
                        if self._is_placeholder(matched_value):
                            continue

                        issues.append(
                            SecurityIssue(
                                type=IssueType.SECRET,
                                severity=Severity.CRITICAL,
                                file_path=filename,
                                line_number=line_num,
                                issue_text=f"{description} ({secret_type})",
                                confidence="HIGH",
                                cwe_id="CWE-798",  # Use of Hard-coded Credentials
                            )
                        )

        return issues

    def _scan_with_bandit(self, files: Dict[str, str]) -> List[SecurityIssue]:
        """Scan code using Bandit static analyzer"""
        issues = []

        # Create temporary directory with files
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Write files to temp directory
            for filename, content in files.items():
                # Skip metadata and non-Python files
                if filename.startswith("_") or not filename.endswith(".py"):
                    continue

                file_path = tmppath / filename
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(content)

            # Run Bandit
            try:
                result = subprocess.run(
                    [
                        "bandit",
                        "-r",
                        str(tmppath),
                        "-f",
                        "json",
                        "-ll",  # Only report medium and high severity
                    ],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                # Parse Bandit output
                if result.stdout:
                    bandit_data = json.loads(result.stdout)

                    for result_item in bandit_data.get("results", []):
                        # Map Bandit severity to our severity levels
                        bandit_severity = result_item.get("issue_severity", "LOW")
                        severity_map = {
                            "LOW": Severity.LOW,
                            "MEDIUM": Severity.MEDIUM,
                            "HIGH": Severity.HIGH,
                        }
                        severity = severity_map.get(bandit_severity, Severity.MEDIUM)

                        # Extract relative filename
                        full_path = result_item.get("filename", "")
                        relative_path = full_path.replace(str(tmppath) + "/", "")

                        issues.append(
                            SecurityIssue(
                                type=IssueType.VULNERABILITY,
                                severity=severity,
                                file_path=relative_path,
                                line_number=result_item.get("line_number"),
                                issue_text=result_item.get("issue_text", "Unknown issue"),
                                confidence=result_item.get("issue_confidence", "MEDIUM"),
                                cwe_id=result_item.get("cwe", {}).get("id"),
                            )
                        )

            except (
                subprocess.TimeoutExpired,
                subprocess.CalledProcessError,
                json.JSONDecodeError,
            ):
                # Bandit failed, skip
                pass

        return issues

    def _is_code_file(self, filename: str) -> bool:
        """Check if file is a code file"""
        code_extensions = {".py", ".js", ".ts", ".java", ".go", ".rb", ".php", ".cs"}
        return any(filename.endswith(ext) for ext in code_extensions)

    def _is_placeholder(self, value: str) -> bool:
        """Check if a value is a placeholder rather than a real secret"""
        placeholders = [
            "your_api_key",
            "your_password",
            "your_secret",
            "api_key_here",
            "password_here",
            "secret_here",
            "xxxxxxxxx",
            "placeholder",
            "example",
            "test",
            "changeme",
            "change_me",
            "todo",
            "fixme",
            "12345",
            "admin",
            "root",
            "demo",
        ]

        value_lower = value.lower()
        return any(placeholder in value_lower for placeholder in placeholders)


def scan_generated_code(
    generated_files: Dict[str, str], use_bandit: bool = True, fail_on_critical: bool = False
) -> SecurityReport:
    """
    Convenience function to scan generated code

    Args:
        generated_files: Dictionary of {filename: content}
        use_bandit: Whether to use Bandit (requires bandit to be installed)
        fail_on_critical: Mark report as unsafe if critical issues found

    Returns:
        SecurityReport with findings

    Example:
        ```python
        files = {
            "main.py": "import os\\nos.system('ls')",
            "config.py": "API_KEY = 'sk_live_12345...'"
        }

        report = scan_generated_code(files)
        print(f"Safe: {report.is_safe}")
        print(f"Issues: {report.total_issues}")
        for issue in report.issues:
            print(f"  - {issue.severity}: {issue.issue_text}")
        ```
    """
    scanner = CodeSecurityScanner(use_bandit=use_bandit, use_secret_detection=True)

    return scanner.scan(generated_files=generated_files, fail_on_critical=fail_on_critical)
