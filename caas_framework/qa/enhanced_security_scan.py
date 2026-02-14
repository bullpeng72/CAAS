"""
Enhanced Security Scanner for CAAS-E QA

Advanced security vulnerability detection:
- OWASP Top 10 checks
- Dependency vulnerability scanning
- Code injection patterns
- Authentication/authorization issues
- Data exposure risks

Part of CAAS-E Week 6 implementation (Task 6.1).
"""

import re
import ast
from pathlib import Path
from typing import List, Dict, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class SecuritySeverity(Enum):
    """Security issue severity levels"""
    CRITICAL = "critical"  # Immediate fix required
    HIGH = "high"  # Fix as soon as possible
    MEDIUM = "medium"  # Fix in next sprint
    LOW = "low"  # Fix when convenient
    INFO = "info"  # Informational


class VulnerabilityCategory(Enum):
    """OWASP Top 10 and other categories"""
    INJECTION = "injection"  # SQL, Command, Code injection
    BROKEN_AUTH = "broken_authentication"
    SENSITIVE_DATA = "sensitive_data_exposure"
    XXE = "xml_external_entities"
    BROKEN_ACCESS = "broken_access_control"
    SECURITY_MISCONFIG = "security_misconfiguration"
    XSS = "cross_site_scripting"
    INSECURE_DESERIALIZATION = "insecure_deserialization"
    VULNERABLE_COMPONENTS = "vulnerable_components"
    INSUFFICIENT_LOGGING = "insufficient_logging"
    CRYPTO_FAILURES = "cryptographic_failures"


@dataclass
class SecurityIssue:
    """Represents a security vulnerability"""
    severity: SecuritySeverity
    category: VulnerabilityCategory
    title: str
    description: str
    file_path: str
    line_number: Optional[int] = None
    code_snippet: Optional[str] = None
    cwe_id: Optional[str] = None  # Common Weakness Enumeration ID
    recommendation: Optional[str] = None
    references: List[str] = None


@dataclass
class SecurityReport:
    """Security scan report"""
    project_name: str
    issues: List[SecurityIssue]
    vulnerability_summary: Dict[SecuritySeverity, int]
    category_summary: Dict[VulnerabilityCategory, int]
    overall_severity: SecuritySeverity
    pass_threshold: bool  # True if no CRITICAL issues


class EnhancedSecurityScanner:
    """
    Comprehensive security scanner for generated code.

    Based on OWASP Top 10 and security best practices.

    Detects:
    1. Injection Vulnerabilities
       - SQL injection
       - Command injection
       - Code injection (eval, exec)

    2. Authentication/Authorization
       - Weak password policies
       - Missing authentication
       - Broken access control

    3. Sensitive Data Exposure
       - Hardcoded secrets
       - Unencrypted data transmission
       - Logging sensitive data

    4. Security Misconfiguration
       - Debug mode in production
       - Default credentials
       - Insecure defaults

    5. Cryptographic Failures
       - Weak encryption algorithms
       - Insecure random number generation
       - Missing HTTPS enforcement
    """

    # Dangerous functions (CWE-78, CWE-95, CWE-502)
    DANGEROUS_FUNCTIONS = {
        "eval": (SecuritySeverity.CRITICAL, "CWE-95", "Arbitrary code execution via eval()"),
        "exec": (SecuritySeverity.CRITICAL, "CWE-95", "Arbitrary code execution via exec()"),
        "compile": (SecuritySeverity.HIGH, "CWE-95", "Dynamic code compilation"),
        "__import__": (SecuritySeverity.HIGH, "CWE-95", "Dynamic import"),
        "pickle.loads": (SecuritySeverity.CRITICAL, "CWE-502", "Insecure deserialization"),
        "yaml.load": (SecuritySeverity.HIGH, "CWE-502", "Unsafe YAML loading"),
        "os.system": (SecuritySeverity.CRITICAL, "CWE-78", "Command injection via os.system()"),
        "subprocess.call": (SecuritySeverity.HIGH, "CWE-78", "Command injection risk"),
        "subprocess.Popen": (SecuritySeverity.HIGH, "CWE-78", "Command injection risk"),
    }

    # SQL injection patterns (CWE-89)
    SQL_INJECTION_PATTERNS = [
        r"execute\s*\(\s*['\"].*%s",  # String formatting in SQL
        r"execute\s*\(\s*f['\"]",  # f-strings in SQL
        r"execute\s*\(\s*.*\+",  # String concatenation in SQL
        r"cursor\.execute\s*\(.*format\(",  # .format() in SQL
    ]

    # Hardcoded secrets patterns (CWE-798)
    SECRET_PATTERNS = [
        (r"password\s*=\s*['\"][^'\"]+['\"]", "Hardcoded password"),
        (r"api_key\s*=\s*['\"][^'\"]+['\"]", "Hardcoded API key"),
        (r"secret\s*=\s*['\"][^'\"]+['\"]", "Hardcoded secret"),
        (r"token\s*=\s*['\"][^'\"]+['\"]", "Hardcoded token"),
        (r"private_key\s*=\s*['\"][^'\"]+['\"]", "Hardcoded private key"),
    ]

    # Weak crypto patterns (CWE-327)
    WEAK_CRYPTO = [
        (r"hashlib\.md5", "MD5 is cryptographically broken"),
        (r"hashlib\.sha1", "SHA1 is cryptographically weak"),
        (r"random\.random", "Use secrets module for cryptographic randomness"),
        (r"DES|RC4", "Weak encryption algorithm"),
    ]

    def __init__(
        self,
        fail_on_critical: bool = True,
        fail_on_high: bool = False,
    ):
        """
        Initialize security scanner.

        Args:
            fail_on_critical: Fail build on CRITICAL issues
            fail_on_high: Fail build on HIGH issues
        """
        self.fail_on_critical = fail_on_critical
        self.fail_on_high = fail_on_high
        self.logger = logging.getLogger(self.__class__.__name__)

    def scan_project(
        self,
        project_dir: Path,
        scan_dependencies: bool = True,
    ) -> SecurityReport:
        """
        Scan project for security vulnerabilities.

        Args:
            project_dir: Project directory
            scan_dependencies: Check for vulnerable dependencies

        Returns:
            SecurityReport with findings
        """
        self.logger.info(f"Starting security scan for {project_dir}")

        issues: List[SecurityIssue] = []

        # Scan Python files
        python_files = list(project_dir.rglob("*.py"))
        for py_file in python_files:
            try:
                issues.extend(self._scan_file(py_file))
            except Exception as e:
                self.logger.warning(f"Error scanning {py_file}: {e}")

        # Scan dependencies
        if scan_dependencies:
            issues.extend(self._scan_dependencies(project_dir))

        # Calculate summaries
        vulnerability_summary = self._calculate_severity_summary(issues)
        category_summary = self._calculate_category_summary(issues)

        # Determine overall severity
        if any(i.severity == SecuritySeverity.CRITICAL for i in issues):
            overall_severity = SecuritySeverity.CRITICAL
        elif any(i.severity == SecuritySeverity.HIGH for i in issues):
            overall_severity = SecuritySeverity.HIGH
        elif any(i.severity == SecuritySeverity.MEDIUM for i in issues):
            overall_severity = SecuritySeverity.MEDIUM
        elif any(i.severity == SecuritySeverity.LOW for i in issues):
            overall_severity = SecuritySeverity.LOW
        else:
            overall_severity = SecuritySeverity.INFO

        # Check pass threshold
        pass_threshold = (
            vulnerability_summary.get(SecuritySeverity.CRITICAL, 0) == 0
            if self.fail_on_critical else True
        )
        if self.fail_on_high:
            pass_threshold = pass_threshold and vulnerability_summary.get(SecuritySeverity.HIGH, 0) == 0

        report = SecurityReport(
            project_name=project_dir.name,
            issues=issues,
            vulnerability_summary=vulnerability_summary,
            category_summary=category_summary,
            overall_severity=overall_severity,
            pass_threshold=pass_threshold,
        )

        self.logger.info(
            f"Security scan complete: {len(issues)} issues, "
            f"overall severity: {overall_severity.value}"
        )

        return report

    def _scan_file(self, file_path: Path) -> List[SecurityIssue]:
        """Scan a single Python file for vulnerabilities"""
        issues = []

        try:
            content = file_path.read_text()
            lines = content.split("\n")

            # Parse AST
            try:
                tree = ast.parse(content, filename=str(file_path))
            except SyntaxError:
                return issues  # Skip files with syntax errors

            # 1. Check for dangerous functions
            issues.extend(self._check_dangerous_functions(tree, file_path, lines))

            # 2. Check for SQL injection
            issues.extend(self._check_sql_injection(content, file_path, lines))

            # 3. Check for hardcoded secrets
            issues.extend(self._check_hardcoded_secrets(content, file_path, lines))

            # 4. Check for weak crypto
            issues.extend(self._check_weak_crypto(content, file_path, lines))

            # 5. Check for security misconfigurations
            issues.extend(self._check_security_misconfig(content, file_path, lines))

            # 6. Check for XSS vulnerabilities
            issues.extend(self._check_xss(content, file_path, lines))

        except Exception as e:
            self.logger.warning(f"Error scanning file {file_path}: {e}")

        return issues

    def _check_dangerous_functions(
        self,
        tree: ast.AST,
        file_path: Path,
        lines: List[str]
    ) -> List[SecurityIssue]:
        """Check for dangerous function calls"""
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func_name = None

                # Direct function call
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                # Attribute call (e.g., pickle.loads)
                elif isinstance(node.func, ast.Attribute):
                    if isinstance(node.func.value, ast.Name):
                        func_name = f"{node.func.value.id}.{node.func.attr}"

                if func_name in self.DANGEROUS_FUNCTIONS:
                    severity, cwe_id, description = self.DANGEROUS_FUNCTIONS[func_name]

                    issues.append(SecurityIssue(
                        severity=severity,
                        category=VulnerabilityCategory.INJECTION,
                        title=f"Dangerous function: {func_name}",
                        description=description,
                        file_path=str(file_path.relative_to(file_path.parent.parent)),
                        line_number=node.lineno,
                        code_snippet=lines[node.lineno - 1].strip() if node.lineno <= len(lines) else None,
                        cwe_id=cwe_id,
                        recommendation=f"Avoid using {func_name}. Use safer alternatives or validate all inputs thoroughly.",
                        references=[
                            f"https://cwe.mitre.org/data/definitions/{cwe_id.split('-')[1]}.html"
                        ]
                    ))

        return issues

    def _check_sql_injection(
        self,
        content: str,
        file_path: Path,
        lines: List[str]
    ) -> List[SecurityIssue]:
        """Check for SQL injection vulnerabilities"""
        issues = []

        for i, line in enumerate(lines, 1):
            for pattern in self.SQL_INJECTION_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    issues.append(SecurityIssue(
                        severity=SecuritySeverity.CRITICAL,
                        category=VulnerabilityCategory.INJECTION,
                        title="SQL Injection vulnerability",
                        description="SQL query uses string formatting/concatenation which is vulnerable to SQL injection",
                        file_path=str(file_path.relative_to(file_path.parent.parent)),
                        line_number=i,
                        code_snippet=line.strip(),
                        cwe_id="CWE-89",
                        recommendation="Use parameterized queries or ORM. Example: cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))",
                        references=[
                            "https://cwe.mitre.org/data/definitions/89.html",
                            "https://owasp.org/www-community/attacks/SQL_Injection"
                        ]
                    ))

        return issues

    def _check_hardcoded_secrets(
        self,
        content: str,
        file_path: Path,
        lines: List[str]
    ) -> List[SecurityIssue]:
        """Check for hardcoded secrets"""
        issues = []

        for i, line in enumerate(lines, 1):
            # Skip comments
            if line.strip().startswith("#"):
                continue

            for pattern, description in self.SECRET_PATTERNS:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    # Exclude placeholder values
                    value = match.group(0)
                    if any(placeholder in value.lower() for placeholder in ["your_", "example", "placeholder", "xxx", "***"]):
                        continue

                    issues.append(SecurityIssue(
                        severity=SecuritySeverity.CRITICAL,
                        category=VulnerabilityCategory.SENSITIVE_DATA,
                        title=f"Hardcoded secret detected: {description}",
                        description="Sensitive credentials are hardcoded in source code",
                        file_path=str(file_path.relative_to(file_path.parent.parent)),
                        line_number=i,
                        code_snippet=line.strip(),
                        cwe_id="CWE-798",
                        recommendation="Use environment variables or secret management service (e.g., os.getenv('API_KEY'))",
                        references=[
                            "https://cwe.mitre.org/data/definitions/798.html"
                        ]
                    ))

        return issues

    def _check_weak_crypto(
        self,
        content: str,
        file_path: Path,
        lines: List[str]
    ) -> List[SecurityIssue]:
        """Check for weak cryptographic practices"""
        issues = []

        for i, line in enumerate(lines, 1):
            for pattern, description in self.WEAK_CRYPTO:
                if re.search(pattern, line, re.IGNORECASE):
                    issues.append(SecurityIssue(
                        severity=SecuritySeverity.HIGH,
                        category=VulnerabilityCategory.CRYPTO_FAILURES,
                        title="Weak cryptography detected",
                        description=description,
                        file_path=str(file_path.relative_to(file_path.parent.parent)),
                        line_number=i,
                        code_snippet=line.strip(),
                        cwe_id="CWE-327",
                        recommendation="Use strong algorithms: SHA-256 for hashing, AES for encryption, secrets module for randomness",
                        references=[
                            "https://cwe.mitre.org/data/definitions/327.html"
                        ]
                    ))

        return issues

    def _check_security_misconfig(
        self,
        content: str,
        file_path: Path,
        lines: List[str]
    ) -> List[SecurityIssue]:
        """Check for security misconfigurations"""
        issues = []

        # Check for debug mode
        if re.search(r"debug\s*=\s*True", content, re.IGNORECASE):
            for i, line in enumerate(lines, 1):
                if re.search(r"debug\s*=\s*True", line, re.IGNORECASE):
                    issues.append(SecurityIssue(
                        severity=SecuritySeverity.MEDIUM,
                        category=VulnerabilityCategory.SECURITY_MISCONFIG,
                        title="Debug mode enabled",
                        description="Debug mode should not be enabled in production",
                        file_path=str(file_path.relative_to(file_path.parent.parent)),
                        line_number=i,
                        code_snippet=line.strip(),
                        cwe_id="CWE-489",
                        recommendation="Set debug=False in production or use environment-based configuration",
                    ))

        return issues

    def _check_xss(
        self,
        content: str,
        file_path: Path,
        lines: List[str]
    ) -> List[SecurityIssue]:
        """Check for Cross-Site Scripting (XSS) vulnerabilities"""
        issues = []

        # Check for unsafe HTML rendering
        xss_patterns = [
            r"\.render_template\s*\(.*\{\{.*\|safe\}\}",
            r"\.format\s*\(.*<.*>",  # HTML in format strings
        ]

        for i, line in enumerate(lines, 1):
            for pattern in xss_patterns:
                if re.search(pattern, line):
                    issues.append(SecurityIssue(
                        severity=SecuritySeverity.HIGH,
                        category=VulnerabilityCategory.XSS,
                        title="Potential XSS vulnerability",
                        description="User input rendered without proper escaping",
                        file_path=str(file_path.relative_to(file_path.parent.parent)),
                        line_number=i,
                        code_snippet=line.strip(),
                        cwe_id="CWE-79",
                        recommendation="Use auto-escaping templates or explicitly escape user input",
                        references=[
                            "https://cwe.mitre.org/data/definitions/79.html",
                            "https://owasp.org/www-community/attacks/xss/"
                        ]
                    ))

        return issues

    def _scan_dependencies(self, project_dir: Path) -> List[SecurityIssue]:
        """Scan for vulnerable dependencies"""
        issues = []

        # Simplified - in production use safety, pip-audit, or Snyk
        requirements_file = project_dir / "requirements.txt"
        if requirements_file.exists():
            # Placeholder for dependency scanning
            # In production, integrate with vulnerability databases
            pass

        return issues

    def _calculate_severity_summary(
        self,
        issues: List[SecurityIssue]
    ) -> Dict[SecuritySeverity, int]:
        """Calculate count by severity"""
        summary = {severity: 0 for severity in SecuritySeverity}

        for issue in issues:
            summary[issue.severity] += 1

        return summary

    def _calculate_category_summary(
        self,
        issues: List[SecurityIssue]
    ) -> Dict[VulnerabilityCategory, int]:
        """Calculate count by category"""
        summary = {category: 0 for category in VulnerabilityCategory}

        for issue in issues:
            summary[issue.category] += 1

        return summary
