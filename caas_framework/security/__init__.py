"""
Security Module - Code Security Analysis

Provides security scanning capabilities for generated code.
"""

from caas_framework.security.code_scanner import (
    CodeSecurityScanner,
    IssueType,
    SecurityIssue,
    SecurityReport,
    Severity,
    scan_generated_code,
)

__all__ = [
    "CodeSecurityScanner",
    "SecurityReport",
    "SecurityIssue",
    "Severity",
    "IssueType",
    "scan_generated_code",
]
