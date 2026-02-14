"""
CLI commands for QA operations

Provides commands for:
- caas qa compliance - Check license and privacy compliance
- caas qa performance - Profile performance metrics
- caas qa security - Scan for security vulnerabilities
- caas qa report - Generate comprehensive QA report

Part of CAAS-E Week 6 implementation (Task 6.1).
"""

import click
import asyncio
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
import logging

from caas_framework.qa import (
    ComplianceChecker,
    PerformanceTester,
    EnhancedSecurityScanner,
    ComplianceLevel,
    PerformanceLevel,
    SecuritySeverity,
    LicenseType,
)

console = Console()
logger = logging.getLogger(__name__)


@click.group("qa")
def qa_group():
    """Quality Assurance commands for generated code"""
    pass


@qa_group.command("compliance")
@click.argument("project_dir", type=click.Path(exists=True, file_okay=False))
@click.option(
    "--license",
    type=click.Choice(["MIT", "Apache-2.0", "GPL-3.0", "BSD-3-Clause"]),
    default="MIT",
    help="Project license type",
)
@click.option(
    "--strict",
    is_flag=True,
    help="Strict mode (warnings become failures)",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output report file (JSON)",
)
def compliance_cmd(project_dir: str, license: str, strict: bool, output: str):
    """
    Check compliance (licenses, privacy, attribution).

    Examples:

    \b
    # Check compliance
    caas qa compliance ./generated

    \b
    # Strict mode
    caas qa compliance ./generated --strict

    \b
    # Save report
    caas qa compliance ./generated -o compliance_report.json
    """
    console.print("\n[bold cyan]🔍 Running Compliance Check...[/bold cyan]\n")

    # Initialize checker
    project_path = Path(project_dir)
    license_type = LicenseType[license.replace("-", "_").replace(".", "_")]

    checker = ComplianceChecker(
        project_license=license_type,
        strict_mode=strict,
    )

    # Run check
    report = checker.check_project(
        project_dir=project_path,
        check_dependencies=True,
        check_privacy=True,
        check_attribution=True,
    )

    # Display results
    _display_compliance_report(report)

    # Save to file
    if output:
        import json
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(_compliance_report_to_dict(report), f, indent=2)

        console.print(f"\n✅ Report saved to: {output_path}")

    # Exit code
    if report.overall_compliance in [ComplianceLevel.FAIL, ComplianceLevel.CRITICAL]:
        exit(1)


@qa_group.command("performance")
@click.argument("project_dir", type=click.Path(exists=True, file_okay=False))
@click.option(
    "--memory-threshold",
    type=int,
    default=500,
    help="Memory threshold in MB",
)
@click.option(
    "--cpu-threshold",
    type=int,
    default=80,
    help="CPU threshold in percent",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output report file (JSON)",
)
def performance_cmd(project_dir: str, memory_threshold: int, cpu_threshold: int, output: str):
    """
    Profile performance (memory, CPU, load).

    Examples:

    \b
    # Profile performance
    caas qa performance ./generated

    \b
    # Custom thresholds
    caas qa performance ./generated --memory-threshold 1000 --cpu-threshold 90

    \b
    # Save report
    caas qa performance ./generated -o performance_report.json
    """
    console.print("\n[bold cyan]⚡ Running Performance Tests...[/bold cyan]\n")

    # Initialize tester
    project_path = Path(project_dir)

    tester = PerformanceTester(
        memory_threshold_mb=memory_threshold,
        cpu_threshold_percent=cpu_threshold,
    )

    # Profile project
    # Note: In production, would load and test actual functions
    report = tester.profile_project(
        project_dir=project_path,
        test_functions=[],  # No test functions for now
    )

    # Display results
    _display_performance_report(report)

    # Save to file
    if output:
        import json
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(_performance_report_to_dict(report), f, indent=2)

        console.print(f"\n✅ Report saved to: {output_path}")

    # Exit code
    if report.overall_performance == PerformanceLevel.POOR:
        exit(1)


@qa_group.command("security")
@click.argument("project_dir", type=click.Path(exists=True, file_okay=False))
@click.option(
    "--fail-on-high",
    is_flag=True,
    help="Fail build on HIGH severity issues",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output report file (JSON)",
)
def security_cmd(project_dir: str, fail_on_high: bool, output: str):
    """
    Scan for security vulnerabilities (OWASP Top 10).

    Examples:

    \b
    # Security scan
    caas qa security ./generated

    \b
    # Fail on HIGH severity
    caas qa security ./generated --fail-on-high

    \b
    # Save report
    caas qa security ./generated -o security_report.json
    """
    console.print("\n[bold cyan]🔒 Running Security Scan...[/bold cyan]\n")

    # Initialize scanner
    project_path = Path(project_dir)

    scanner = EnhancedSecurityScanner(
        fail_on_critical=True,
        fail_on_high=fail_on_high,
    )

    # Run scan
    report = scanner.scan_project(
        project_dir=project_path,
        scan_dependencies=True,
    )

    # Display results
    _display_security_report(report)

    # Save to file
    if output:
        import json
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(_security_report_to_dict(report), f, indent=2)

        console.print(f"\n✅ Report saved to: {output_path}")

    # Exit code
    if not report.pass_threshold:
        exit(1)


@qa_group.command("report")
@click.argument("project_dir", type=click.Path(exists=True, file_okay=False))
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default="qa_report.json",
    help="Output report file",
)
def report_cmd(project_dir: str, output: str):
    """
    Generate comprehensive QA report (all checks).

    Examples:

    \b
    # Full QA report
    caas qa report ./generated

    \b
    # Custom output
    caas qa report ./generated -o my_qa_report.json
    """
    console.print("\n[bold cyan]📊 Generating Comprehensive QA Report...[/bold cyan]\n")

    project_path = Path(project_dir)

    # Run all checks
    console.print("[dim]1/3 Compliance check...[/dim]")
    compliance_checker = ComplianceChecker()
    compliance_report = compliance_checker.check_project(project_path)

    console.print("[dim]2/3 Performance test...[/dim]")
    performance_tester = PerformanceTester()
    performance_report = performance_tester.profile_project(project_path)

    console.print("[dim]3/3 Security scan...[/dim]")
    security_scanner = EnhancedSecurityScanner()
    security_report = security_scanner.scan_project(project_path)

    # Combine reports
    combined_report = {
        "project_name": project_path.name,
        "compliance": _compliance_report_to_dict(compliance_report),
        "performance": _performance_report_to_dict(performance_report),
        "security": _security_report_to_dict(security_report),
        "summary": {
            "compliance_level": compliance_report.overall_compliance.value,
            "performance_level": performance_report.overall_performance.value,
            "security_severity": security_report.overall_severity.value,
            "pass_all_checks": (
                compliance_report.pass_rate >= 0.9
                and performance_report.overall_performance in [PerformanceLevel.EXCELLENT, PerformanceLevel.GOOD]
                and security_report.pass_threshold
            ),
        },
    }

    # Save report
    import json
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(combined_report, f, indent=2)

    # Display summary
    _display_combined_summary(combined_report)

    console.print(f"\n✅ Comprehensive report saved to: {output_path}")


# Helper functions for display

def _display_compliance_report(report):
    """Display compliance report in console"""
    # Summary panel
    summary_text = f"""
Project: {report.project_name}
Overall: {report.overall_compliance.value.upper()}
Pass Rate: {report.pass_rate * 100:.1f}%
Issues: {len(report.issues)}
"""
    console.print(Panel(summary_text.strip(), title="Compliance Summary", border_style="cyan"))

    # Issues table
    if report.issues:
        table = Table(title="Compliance Issues", box=box.ROUNDED)
        table.add_column("Level", style="bold")
        table.add_column("Category")
        table.add_column("Message")

        for issue in report.issues[:10]:  # Show first 10
            table.add_row(
                issue.level.value.upper(),
                issue.category,
                issue.message[:60] + "..." if len(issue.message) > 60 else issue.message,
            )

        console.print(table)

        if len(report.issues) > 10:
            console.print(f"\n[dim]... and {len(report.issues) - 10} more issues[/dim]")


def _display_performance_report(report):
    """Display performance report in console"""
    summary_text = f"""
Project: {report.project_name}
Overall: {report.overall_performance.value.upper()}
Duration: {report.total_duration_seconds:.2f}s
Tests: {report.summary.get('total_tests', 0)}
Avg Memory: {report.summary.get('average_memory_mb', 0):.1f} MB
Avg CPU: {report.summary.get('average_cpu_percent', 0):.1f}%
"""
    console.print(Panel(summary_text.strip(), title="Performance Summary", border_style="yellow"))


def _display_security_report(report):
    """Display security report in console"""
    # Summary panel
    summary_text = f"""
Project: {report.project_name}
Overall Severity: {report.overall_severity.value.upper()}
Pass Threshold: {'✅ PASS' if report.pass_threshold else '❌ FAIL'}
Total Issues: {len(report.issues)}
"""

    # Add severity counts
    for severity in SecuritySeverity:
        count = report.vulnerability_summary.get(severity, 0)
        if count > 0:
            summary_text += f"\n{severity.value.upper()}: {count}"

    console.print(Panel(summary_text.strip(), title="Security Summary", border_style="red"))

    # Issues table
    if report.issues:
        table = Table(title="Security Issues", box=box.ROUNDED)
        table.add_column("Severity", style="bold")
        table.add_column("Category")
        table.add_column("Title")
        table.add_column("File:Line")

        for issue in report.issues[:15]:  # Show first 15
            table.add_row(
                issue.severity.value.upper(),
                issue.category.value,
                issue.title[:40] + "..." if len(issue.title) > 40 else issue.title,
                f"{issue.file_path}:{issue.line_number}" if issue.line_number else issue.file_path,
            )

        console.print(table)

        if len(report.issues) > 15:
            console.print(f"\n[dim]... and {len(report.issues) - 15} more issues[/dim]")


def _display_combined_summary(report):
    """Display combined QA summary"""
    summary = report["summary"]

    summary_text = f"""
Project: {report['project_name']}

Compliance: {summary['compliance_level'].upper()}
Performance: {summary['performance_level'].upper()}
Security: {summary['security_severity'].upper()}

Overall: {'✅ PASS' if summary['pass_all_checks'] else '❌ FAIL'}
"""

    console.print(Panel(summary_text.strip(), title="QA Report Summary", border_style="green"))


# Helper functions for serialization

def _compliance_report_to_dict(report):
    """Convert ComplianceReport to dict"""
    return {
        "project_name": report.project_name,
        "overall_compliance": report.overall_compliance.value,
        "pass_rate": report.pass_rate,
        "issues": [
            {
                "level": issue.level.value,
                "category": issue.category,
                "message": issue.message,
                "file_path": issue.file_path,
                "recommendation": issue.recommendation,
            }
            for issue in report.issues
        ],
        "privacy_checks": report.privacy_checks,
    }


def _performance_report_to_dict(report):
    """Convert PerformanceReport to dict"""
    return {
        "project_name": report.project_name,
        "overall_performance": report.overall_performance.value,
        "total_duration_seconds": report.total_duration_seconds,
        "summary": report.summary,
    }


def _security_report_to_dict(report):
    """Convert SecurityReport to dict"""
    return {
        "project_name": report.project_name,
        "overall_severity": report.overall_severity.value,
        "pass_threshold": report.pass_threshold,
        "issues": [
            {
                "severity": issue.severity.value,
                "category": issue.category.value,
                "title": issue.title,
                "description": issue.description,
                "file_path": issue.file_path,
                "line_number": issue.line_number,
                "cwe_id": issue.cwe_id,
                "recommendation": issue.recommendation,
            }
            for issue in report.issues
        ],
        "vulnerability_summary": {k.value: v for k, v in report.vulnerability_summary.items()},
    }
