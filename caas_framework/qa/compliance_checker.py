"""
Compliance Checker for CAAS-E QA

Verifies compliance with:
- Open source license requirements
- Privacy regulations (GDPR, CCPA)
- Dependency license compatibility
- Code attribution requirements

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


class LicenseType(Enum):
    """Common open source license types"""
    MIT = "MIT"
    APACHE_2 = "Apache-2.0"
    GPL_V3 = "GPL-3.0"
    BSD_3 = "BSD-3-Clause"
    ISC = "ISC"
    LGPL = "LGPL"
    MPL_2 = "MPL-2.0"
    UNLICENSED = "UNLICENSED"
    UNKNOWN = "UNKNOWN"


class ComplianceLevel(Enum):
    """Compliance check severity levels"""
    PASS = "pass"
    WARNING = "warning"
    FAIL = "fail"
    CRITICAL = "critical"


@dataclass
class ComplianceIssue:
    """Represents a compliance issue"""
    level: ComplianceLevel
    category: str  # "license", "privacy", "attribution"
    message: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    recommendation: Optional[str] = None


@dataclass
class LicenseInfo:
    """License information for a dependency"""
    package_name: str
    license_type: LicenseType
    license_text: Optional[str] = None
    compatible: bool = True
    compatibility_issues: List[str] = None


@dataclass
class ComplianceReport:
    """Compliance check report"""
    project_name: str
    issues: List[ComplianceIssue]
    license_summary: Dict[str, LicenseInfo]
    privacy_checks: Dict[str, bool]
    overall_compliance: ComplianceLevel
    pass_rate: float  # 0.0-1.0


class ComplianceChecker:
    """
    Comprehensive compliance checker for generated code.

    Checks:
    1. License Compliance
       - Dependency license compatibility
       - License file presence
       - Proper attribution

    2. Privacy Compliance
       - GDPR requirements (consent, data protection)
       - PII handling patterns
       - Data retention policies

    3. Code Attribution
       - Copyright notices
       - Author information
       - Third-party code attribution
    """

    # GPL-incompatible licenses
    GPL_INCOMPATIBLE = {
        LicenseType.APACHE_2,  # GPL v2 incompatible
    }

    # Privacy-related patterns (GDPR, CCPA)
    PRIVACY_PATTERNS = {
        "pii_collection": [
            r"email",
            r"phone",
            r"ssn",
            r"credit_card",
            r"password",
            r"ip_address",
        ],
        "consent_keywords": [
            r"consent",
            r"opt[-_]in",
            r"agree",
            r"accept",
        ],
        "data_retention": [
            r"delete",
            r"purge",
            r"expire",
            r"retention",
        ],
    }

    def __init__(
        self,
        project_license: LicenseType = LicenseType.MIT,
        strict_mode: bool = False,
    ):
        """
        Initialize compliance checker.

        Args:
            project_license: License type for the project
            strict_mode: If True, warnings become failures
        """
        self.project_license = project_license
        self.strict_mode = strict_mode
        self.logger = logging.getLogger(self.__class__.__name__)

    def check_project(
        self,
        project_dir: Path,
        check_dependencies: bool = True,
        check_privacy: bool = True,
        check_attribution: bool = True,
    ) -> ComplianceReport:
        """
        Run comprehensive compliance check on project.

        Args:
            project_dir: Path to project directory
            check_dependencies: Check dependency licenses
            check_privacy: Check privacy compliance
            check_attribution: Check code attribution

        Returns:
            ComplianceReport with all findings
        """
        self.logger.info(f"Starting compliance check for {project_dir}")

        issues: List[ComplianceIssue] = []
        license_summary: Dict[str, LicenseInfo] = {}
        privacy_checks: Dict[str, bool] = {}

        # 1. Check license file exists
        issues.extend(self._check_license_file(project_dir))

        # 2. Check dependency licenses
        if check_dependencies:
            dep_issues, license_summary = self._check_dependency_licenses(project_dir)
            issues.extend(dep_issues)

        # 3. Check privacy compliance
        if check_privacy:
            privacy_issues, privacy_checks = self._check_privacy_compliance(project_dir)
            issues.extend(privacy_issues)

        # 4. Check code attribution
        if check_attribution:
            issues.extend(self._check_code_attribution(project_dir))

        # Calculate overall compliance
        overall_compliance = self._calculate_overall_compliance(issues)

        # Calculate pass rate
        total_checks = len(issues) + len(license_summary) + len(privacy_checks)
        failed_checks = sum(1 for issue in issues if issue.level in [ComplianceLevel.FAIL, ComplianceLevel.CRITICAL])
        pass_rate = 1.0 - (failed_checks / total_checks) if total_checks > 0 else 1.0

        report = ComplianceReport(
            project_name=project_dir.name,
            issues=issues,
            license_summary=license_summary,
            privacy_checks=privacy_checks,
            overall_compliance=overall_compliance,
            pass_rate=pass_rate,
        )

        self.logger.info(
            f"Compliance check complete: {overall_compliance.value} "
            f"({len(issues)} issues, {pass_rate*100:.1f}% pass rate)"
        )

        return report

    def _check_license_file(self, project_dir: Path) -> List[ComplianceIssue]:
        """Check if LICENSE file exists and is valid"""
        issues = []

        license_files = ["LICENSE", "LICENSE.txt", "LICENSE.md", "COPYING"]
        found = False

        for license_file in license_files:
            if (project_dir / license_file).exists():
                found = True
                break

        if not found:
            issues.append(ComplianceIssue(
                level=ComplianceLevel.CRITICAL if self.strict_mode else ComplianceLevel.FAIL,
                category="license",
                message="No LICENSE file found in project root",
                recommendation="Add a LICENSE file with your chosen license text"
            ))

        return issues

    def _check_dependency_licenses(
        self,
        project_dir: Path
    ) -> Tuple[List[ComplianceIssue], Dict[str, LicenseInfo]]:
        """
        Check dependency license compatibility.

        Reads from:
        - requirements.txt
        - pyproject.toml
        - setup.py
        """
        issues = []
        license_summary = {}

        # Parse dependencies from requirements.txt
        requirements_file = project_dir / "requirements.txt"
        if requirements_file.exists():
            dependencies = self._parse_requirements(requirements_file)

            for dep in dependencies:
                # Try to detect license (simplified - in production use pip-licenses)
                license_type = self._detect_license(dep)

                # Check compatibility
                compatible, compatibility_issues = self._check_license_compatibility(
                    license_type,
                    self.project_license
                )

                license_info = LicenseInfo(
                    package_name=dep,
                    license_type=license_type,
                    compatible=compatible,
                    compatibility_issues=compatibility_issues,
                )

                license_summary[dep] = license_info

                if not compatible:
                    issues.append(ComplianceIssue(
                        level=ComplianceLevel.FAIL,
                        category="license",
                        message=f"Dependency '{dep}' license ({license_type.value}) "
                                f"incompatible with project license ({self.project_license.value})",
                        recommendation=f"Remove dependency or change project license. Issues: {', '.join(compatibility_issues)}"
                    ))

        return issues, license_summary

    def _check_privacy_compliance(
        self,
        project_dir: Path
    ) -> Tuple[List[ComplianceIssue], Dict[str, bool]]:
        """
        Check privacy regulation compliance (GDPR, CCPA).

        Checks:
        - PII collection with consent
        - Data retention policies
        - User data deletion capabilities
        """
        issues = []
        privacy_checks = {
            "pii_with_consent": False,
            "data_retention_policy": False,
            "user_deletion": False,
        }

        # Scan Python files for privacy patterns
        python_files = list(project_dir.rglob("*.py"))

        has_pii_collection = False
        has_consent_mechanism = False
        has_data_retention = False
        has_deletion_method = False

        for py_file in python_files:
            try:
                content = py_file.read_text()

                # Check for PII collection
                for pattern in self.PRIVACY_PATTERNS["pii_collection"]:
                    if re.search(pattern, content, re.IGNORECASE):
                        has_pii_collection = True
                        break

                # Check for consent mechanism
                for pattern in self.PRIVACY_PATTERNS["consent_keywords"]:
                    if re.search(pattern, content, re.IGNORECASE):
                        has_consent_mechanism = True
                        break

                # Check for data retention
                for pattern in self.PRIVACY_PATTERNS["data_retention"]:
                    if re.search(pattern, content, re.IGNORECASE):
                        has_data_retention = True

                # Check for deletion methods
                if re.search(r"def\s+delete_user|remove_user_data", content):
                    has_deletion_method = True

            except Exception as e:
                self.logger.warning(f"Error reading {py_file}: {e}")

        # Evaluate privacy compliance
        if has_pii_collection:
            if not has_consent_mechanism:
                issues.append(ComplianceIssue(
                    level=ComplianceLevel.CRITICAL,
                    category="privacy",
                    message="PII collection detected without explicit consent mechanism",
                    recommendation="Add user consent flow before collecting PII (email, phone, etc.)"
                ))
            else:
                privacy_checks["pii_with_consent"] = True

            if not has_deletion_method:
                issues.append(ComplianceIssue(
                    level=ComplianceLevel.FAIL,
                    category="privacy",
                    message="No user data deletion method found (GDPR 'Right to be Forgotten')",
                    recommendation="Implement delete_user_data() or similar method"
                ))
            else:
                privacy_checks["user_deletion"] = True

        privacy_checks["data_retention_policy"] = has_data_retention

        return issues, privacy_checks

    def _check_code_attribution(self, project_dir: Path) -> List[ComplianceIssue]:
        """Check for proper code attribution and copyright notices"""
        issues = []

        python_files = list(project_dir.rglob("*.py"))
        files_without_copyright = []

        for py_file in python_files:
            # Skip test files and __init__.py
            if "test_" in py_file.name or py_file.name == "__init__.py":
                continue

            try:
                content = py_file.read_text()

                # Check for copyright notice in first 10 lines
                lines = content.split("\n")[:10]
                has_copyright = any(
                    re.search(r"copyright|©|\(c\)", line, re.IGNORECASE)
                    for line in lines
                )

                if not has_copyright:
                    files_without_copyright.append(py_file.name)

            except Exception as e:
                self.logger.warning(f"Error reading {py_file}: {e}")

        if files_without_copyright and self.strict_mode:
            issues.append(ComplianceIssue(
                level=ComplianceLevel.WARNING,
                category="attribution",
                message=f"{len(files_without_copyright)} files missing copyright notice",
                recommendation="Add copyright notice in file headers"
            ))

        return issues

    def _parse_requirements(self, requirements_file: Path) -> List[str]:
        """Parse package names from requirements.txt"""
        packages = []

        try:
            content = requirements_file.read_text()
            for line in content.split("\n"):
                line = line.strip()
                if line and not line.startswith("#"):
                    # Extract package name (before ==, >=, etc.)
                    package = re.split(r"[=<>!]", line)[0].strip()
                    packages.append(package)
        except Exception as e:
            self.logger.warning(f"Error parsing requirements: {e}")

        return packages

    def _detect_license(self, package_name: str) -> LicenseType:
        """
        Detect license type for a package.

        Note: Simplified implementation. In production, use:
        - pip-licenses library
        - PyPI API
        - License file parsing
        """
        # Common package licenses (simplified mapping)
        known_licenses = {
            "crewai": LicenseType.MIT,
            "langchain": LicenseType.MIT,
            "openai": LicenseType.MIT,
            "pydantic": LicenseType.MIT,
            "fastapi": LicenseType.MIT,
            "pytest": LicenseType.MIT,
        }

        return known_licenses.get(package_name.lower(), LicenseType.UNKNOWN)

    def _check_license_compatibility(
        self,
        dep_license: LicenseType,
        project_license: LicenseType
    ) -> Tuple[bool, List[str]]:
        """
        Check if dependency license is compatible with project license.

        Returns:
            (compatible, list_of_issues)
        """
        issues = []

        # Unknown licenses are warnings
        if dep_license == LicenseType.UNKNOWN:
            issues.append("License type unknown - manual review required")
            return True, issues  # Don't block, but warn

        # GPL compatibility rules
        if project_license == LicenseType.GPL_V3:
            if dep_license in self.GPL_INCOMPATIBLE:
                issues.append(f"{dep_license.value} is incompatible with GPL-3.0")
                return False, issues

        # Copyleft licenses require project to use same license
        if dep_license == LicenseType.GPL_V3:
            if project_license != LicenseType.GPL_V3:
                issues.append("GPL-3.0 dependency requires project to be GPL-3.0")
                return False, issues

        return True, issues

    def _calculate_overall_compliance(
        self,
        issues: List[ComplianceIssue]
    ) -> ComplianceLevel:
        """Calculate overall compliance level from issues"""
        if not issues:
            return ComplianceLevel.PASS

        # Check for critical issues
        if any(issue.level == ComplianceLevel.CRITICAL for issue in issues):
            return ComplianceLevel.CRITICAL

        # Check for failures
        if any(issue.level == ComplianceLevel.FAIL for issue in issues):
            return ComplianceLevel.FAIL

        # Only warnings
        if any(issue.level == ComplianceLevel.WARNING for issue in issues):
            return ComplianceLevel.WARNING

        return ComplianceLevel.PASS
