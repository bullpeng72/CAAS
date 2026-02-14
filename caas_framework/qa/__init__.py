"""
Quality Assurance (QA) Module for CAAS-E

Comprehensive QA capabilities:
- Compliance checking (licenses, privacy)
- Performance testing (memory, CPU, load)
- Security scanning (OWASP Top 10, vulnerabilities)

Part of CAAS-E Week 6 implementation (Task 6.1).
"""

from caas_framework.qa.compliance_checker import (
    ComplianceChecker,
    ComplianceReport,
    ComplianceIssue,
    ComplianceLevel,
    LicenseType,
    LicenseInfo,
)

from caas_framework.qa.performance_tester import (
    PerformanceTester,
    PerformanceReport,
    PerformanceMetrics,
    PerformanceLevel,
    MemoryProfile,
    CPUProfile,
    LoadTestResult,
)

from caas_framework.qa.enhanced_security_scan import (
    EnhancedSecurityScanner,
    SecurityReport,
    SecurityIssue,
    SecuritySeverity,
    VulnerabilityCategory,
)

__all__ = [
    # Compliance
    "ComplianceChecker",
    "ComplianceReport",
    "ComplianceIssue",
    "ComplianceLevel",
    "LicenseType",
    "LicenseInfo",
    # Performance
    "PerformanceTester",
    "PerformanceReport",
    "PerformanceMetrics",
    "PerformanceLevel",
    "MemoryProfile",
    "CPUProfile",
    "LoadTestResult",
    # Security
    "EnhancedSecurityScanner",
    "SecurityReport",
    "SecurityIssue",
    "SecuritySeverity",
    "VulnerabilityCategory",
]
