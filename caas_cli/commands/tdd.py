"""
CLI commands for TDD (Test-Driven Development) workflow

Implements CAAS-E Week 3 TDD Integration:
- Phase 4.5: TDD RED - Test generation from Golden Data
- Phase 5.5: TDD REFACTOR - Code analysis and refactoring suggestions
"""

import click
import json
import asyncio
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from typing import Optional, List

from caas_framework.methodology.tdd_test_generator import TDDRedEngine
from caas_framework.methodology.tdd_refactor_engine import (
    TDDRefactorEngine,
    RefactorReport
)
from caas_framework.models.specifications import ConcretizedRequirement

console = Console()


@click.group("tdd")
def tdd_group():
    """
    TDD (Test-Driven Development) workflow commands.

    Supports RED-GREEN-REFACTOR cycle:
    - generate-tests: Phase 4.5 (TDD RED) - Generate failing tests
    - analyze-code: Phase 5.5 (TDD REFACTOR) - Analyze code quality
    - workflow: Complete TDD workflow (RED → GREEN → REFACTOR)
    """


@tdd_group.command("generate-tests")
@click.argument("golden_data", type=click.Path(exists=True))
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(),
    default="./tests",
    help="Output directory for generated tests (default: ./tests)"
)
@click.option(
    "--test-types",
    type=str,
    default="unit,integration,edge_case",
    help="Comma-separated test types to generate (default: unit,integration,edge_case)"
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show detailed generation process"
)
def generate_tests_cmd(
    golden_data: str,
    output_dir: str,
    test_types: str,
    verbose: bool
):
    """
    Generate pytest tests from Golden Data (Phase 4.5: TDD RED).

    Reads Golden Data with test_scenarios and generates complete pytest test files
    with fixtures, mocks, and assertions.

    Example:
        caas tdd generate-tests ./golden_data.json --output-dir ./tests

    Generated files:
        - tests/test_<feature_name>_<feature_id>.py
        - Includes: unit, integration, edge_case, e2e tests
    """
    asyncio.run(_generate_tests(golden_data, output_dir, test_types, verbose))


async def _generate_tests(
    golden_data_path: str,
    output_dir: str,
    test_types: str,
    verbose: bool
):
    """Async implementation of test generation"""

    console.print("\n")
    console.print(Panel(
        "[bold cyan]Phase 4.5: TDD RED - Test Generation[/bold cyan]",
        border_style="cyan"
    ))

    # Load Golden Data
    console.print(f"\n📂 Loading Golden Data: [cyan]{golden_data_path}[/cyan]")
    try:
        with open(golden_data_path, 'r') as f:
            golden_data_dict = json.load(f)

        # Convert to ConcretizedRequirement
        golden_data = ConcretizedRequirement(**golden_data_dict)

        # Count features with test scenarios
        features_with_tests = [
            f for f in golden_data.features
            if f.test_scenarios and len(f.test_scenarios) > 0
        ]

        if not features_with_tests:
            console.print("[yellow]⚠️  No features with test_scenarios found![/yellow]")
            console.print("   Add test_scenarios to your features in Golden Data.")
            return

        console.print(f"✅ Loaded {len(golden_data.features)} features")
        console.print(f"   {len(features_with_tests)} features have test scenarios")

    except Exception as e:
        console.print(f"[red]❌ Error loading Golden Data: {e}[/red]")
        return

    # Generate tests
    console.print(f"\n🧪 Generating tests...")
    console.print(f"   Output directory: [cyan]{output_dir}[/cyan]")
    console.print(f"   Test types: [cyan]{test_types}[/cyan]\n")

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Generating test files...", total=None)

            # Generate tests
            engine = TDDRedEngine()
            generated_tests = await engine.generate_tests(golden_data, output_dir)

            progress.update(task, completed=True)

        # Display results
        if not generated_tests:
            console.print("[yellow]⚠️  No tests generated[/yellow]")
            return

        console.print(f"[green]✅ Generated {len(generated_tests)} test files:[/green]\n")

        # Create table
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("File", style="cyan")
        table.add_column("Tests", justify="right", style="yellow")
        table.add_column("Types", style="green")
        table.add_column("Feature ID", style="blue")

        total_tests = 0
        for test_file in generated_tests:
            table.add_row(
                test_file.file_path,
                str(test_file.test_count),
                ", ".join(test_file.test_types),
                test_file.feature_id
            )
            total_tests += test_file.test_count

            # Write file to disk
            Path(test_file.file_path).parent.mkdir(parents=True, exist_ok=True)
            with open(test_file.file_path, 'w') as f:
                f.write(test_file.content)

        console.print(table)
        console.print(f"\n[bold green]📊 Total: {total_tests} tests generated[/bold green]")

        # Show verbose details
        if verbose:
            console.print("\n[bold]Generated Test Details:[/bold]")
            for test_file in generated_tests:
                console.print(f"\n[cyan]{test_file.file_path}[/cyan]")
                console.print(f"  Lines: {len(test_file.content.splitlines())}")
                console.print(f"  Tests: {test_file.test_count}")
                console.print(f"  Types: {', '.join(test_file.test_types)}")

        console.print("\n[bold yellow]Next Steps:[/bold yellow]")
        console.print("  1. Review generated tests")
        console.print(f"  2. Run tests: [cyan]pytest {output_dir} -v[/cyan]")
        console.print("  3. All tests should FAIL (RED phase)")
        console.print("  4. Implement features to make tests PASS (GREEN phase)")
        console.print(f"  5. Analyze code: [cyan]caas tdd analyze-code <file>[/cyan]")

    except Exception as e:
        console.print(f"[red]❌ Error generating tests: {e}[/red]")
        if verbose:
            import traceback
            console.print(traceback.format_exc())


@tdd_group.command("analyze-code")
@click.argument("code_file", type=click.Path(exists=True))
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default=None,
    help="Output file for refactoring report (JSON format)"
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "json", "detailed"]),
    default="table",
    help="Output format (default: table)"
)
@click.option(
    "--min-severity",
    type=click.Choice(["low", "medium", "high", "critical"]),
    default="low",
    help="Minimum severity to report (default: low = show all)"
)
@click.option(
    "--show-suggestions/--no-suggestions",
    default=True,
    help="Show refactoring suggestions (default: true)"
)
def analyze_code_cmd(
    code_file: str,
    output: Optional[str],
    output_format: str,
    min_severity: str,
    show_suggestions: bool
):
    """
    Analyze code for smells and refactoring opportunities (Phase 5.5: TDD REFACTOR).

    Performs AST-based analysis to detect:
    - Code smells (long functions, too many parameters, deep nesting, magic numbers)
    - Performance issues (nested loops, string concatenation in loops)
    - Generates refactoring suggestions with before/after examples

    Example:
        caas tdd analyze-code ./src/auth/services.py --format table
        caas tdd analyze-code ./src/app.py --output report.json --format json
    """
    _analyze_code(code_file, output, output_format, min_severity, show_suggestions)


def _analyze_code(
    code_file_path: str,
    output_path: Optional[str],
    output_format: str,
    min_severity: str,
    show_suggestions: bool
):
    """Implementation of code analysis"""

    console.print("\n")
    console.print(Panel(
        "[bold cyan]Phase 5.5: TDD REFACTOR - Code Analysis[/bold cyan]",
        border_style="cyan"
    ))

    # Load code
    console.print(f"\n📂 Analyzing: [cyan]{code_file_path}[/cyan]")
    try:
        with open(code_file_path, 'r') as f:
            code = f.read()

        lines = len(code.splitlines())
        console.print(f"   {lines} lines of code\n")

    except Exception as e:
        console.print(f"[red]❌ Error loading file: {e}[/red]")
        return

    # Analyze code
    console.print("🔍 Running analysis...")
    try:
        engine = TDDRefactorEngine()
        report: RefactorReport = engine.analyze_code(code, code_file_path)

        console.print("[green]✅ Analysis complete[/green]\n")

    except Exception as e:
        console.print(f"[red]❌ Error analyzing code: {e}[/red]")
        return

    # Filter by severity
    severity_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
    min_level = severity_order[min_severity]
    filtered_smells = [
        s for s in report.code_smells
        if severity_order[s.severity.value] >= min_level
    ]

    # Display results based on format
    if output_format == "json":
        # JSON output
        report_dict = report.to_dict()
        if output_path:
            with open(output_path, 'w') as f:
                json.dump(report_dict, f, indent=2)
            console.print(f"[green]✅ Report saved to: {output_path}[/green]")
        else:
            console.print(json.dumps(report_dict, indent=2))

    elif output_format == "table":
        # Table output
        _display_analysis_table(report, filtered_smells, show_suggestions)

    elif output_format == "detailed":
        # Detailed output
        _display_analysis_detailed(report, filtered_smells, show_suggestions)

    # Save JSON output if path provided
    if output_path and output_format != "json":
        with open(output_path, 'w') as f:
            json.dump(report.to_dict(), f, indent=2)
        console.print(f"\n[green]✅ JSON report saved to: {output_path}[/green]")


def _display_analysis_table(
    report: RefactorReport,
    filtered_smells: List,
    show_suggestions: bool
):
    """Display analysis results in table format"""

    # Quality Scores
    console.print("[bold]📊 Code Quality Scores:[/bold]\n")
    scores_table = Table(show_header=True, header_style="bold cyan")
    scores_table.add_column("Metric", style="cyan")
    scores_table.add_column("Score", justify="right", style="yellow")
    scores_table.add_column("Status", style="green")

    def get_status(score):
        if score >= 9.0:
            return "[green]Excellent ✅[/green]"
        elif score >= 7.0:
            return "[yellow]Good[/yellow]"
        elif score >= 5.0:
            return "[orange1]Needs Improvement[/orange1]"
        else:
            return "[red]Poor ⚠️[/red]"

    scores_table.add_row(
        "Code Quality",
        f"{report.code_quality_score:.1f}/10.0",
        get_status(report.code_quality_score)
    )
    scores_table.add_row(
        "Best Practices",
        f"{report.best_practices_score:.1f}/10.0",
        get_status(report.best_practices_score)
    )

    console.print(scores_table)

    # Code Smells
    if filtered_smells:
        console.print(f"\n[bold]🔍 Code Smells Found: {len(filtered_smells)}[/bold]\n")

        smells_table = Table(show_header=True, header_style="bold cyan")
        smells_table.add_column("Severity", style="red")
        smells_table.add_column("Type", style="yellow")
        smells_table.add_column("Location", style="cyan")
        smells_table.add_column("Description", style="white")

        for smell in filtered_smells:
            severity_color = {
                "critical": "red bold",
                "high": "red",
                "medium": "yellow",
                "low": "blue"
            }.get(smell.severity.value, "white")

            smells_table.add_row(
                f"[{severity_color}]{smell.severity.value.upper()}[/{severity_color}]",
                smell.smell_type,
                smell.location,
                smell.description[:60] + "..." if len(smell.description) > 60 else smell.description
            )

        console.print(smells_table)
    else:
        console.print(f"\n[green]✅ No code smells found (above {filtered_smells} severity)[/green]")

    # Performance Issues
    if report.performance_issues:
        console.print(f"\n[bold]⚡ Performance Issues: {len(report.performance_issues)}[/bold]\n")

        perf_table = Table(show_header=True, header_style="bold cyan")
        perf_table.add_column("Type", style="yellow")
        perf_table.add_column("Location", style="cyan")
        perf_table.add_column("Complexity", style="red")
        perf_table.add_column("Optimization", style="green")

        for issue in report.performance_issues:
            perf_table.add_row(
                issue.issue_type,
                issue.location,
                issue.current_complexity,
                issue.optimization[:40] + "..." if len(issue.optimization) > 40 else issue.optimization
            )

        console.print(perf_table)

    # Refactoring Suggestions
    if show_suggestions and report.refactoring_suggestions:
        console.print(f"\n[bold]💡 Refactoring Suggestions: {len(report.refactoring_suggestions)}[/bold]\n")

        suggestions_table = Table(show_header=True, header_style="bold cyan")
        suggestions_table.add_column("Type", style="yellow")
        suggestions_table.add_column("Target", style="cyan")
        suggestions_table.add_column("Effort", style="blue")
        suggestions_table.add_column("Reason", style="white")

        for suggestion in report.refactoring_suggestions[:10]:  # Show top 10
            suggestions_table.add_row(
                suggestion.refactoring_type.value,
                suggestion.target,
                suggestion.effort,
                suggestion.reason[:50] + "..." if len(suggestion.reason) > 50 else suggestion.reason
            )

        console.print(suggestions_table)

        if len(report.refactoring_suggestions) > 10:
            console.print(f"\n[dim]... and {len(report.refactoring_suggestions) - 10} more suggestions[/dim]")


def _display_analysis_detailed(
    report: RefactorReport,
    filtered_smells: List,
    show_suggestions: bool
):
    """Display detailed analysis results"""

    console.print("[bold]📊 Code Quality Report[/bold]\n")
    console.print(f"File: [cyan]{report.file_path}[/cyan]")
    console.print(f"Code Quality Score: [yellow]{report.code_quality_score:.1f}/10.0[/yellow]")
    console.print(f"Best Practices Score: [yellow]{report.best_practices_score:.1f}/10.0[/yellow]")
    console.print(f"\nSummary: {report.summary}\n")

    # Detailed smells
    if filtered_smells:
        console.print(f"[bold red]🔍 Code Smells ({len(filtered_smells)}):[/bold red]\n")
        for i, smell in enumerate(filtered_smells, 1):
            console.print(f"{i}. [{smell.severity.value.upper()}] {smell.smell_type}")
            console.print(f"   Location: {smell.location}")
            console.print(f"   {smell.description}")
            if smell.suggested_fix:
                console.print(f"   Fix: {smell.suggested_fix}")
            console.print()

    # Detailed suggestions
    if show_suggestions and report.refactoring_suggestions:
        console.print(f"[bold green]💡 Refactoring Suggestions ({len(report.refactoring_suggestions)}):[/bold green]\n")
        for i, suggestion in enumerate(report.refactoring_suggestions, 1):
            console.print(f"{i}. {suggestion.refactoring_type.value} → {suggestion.target}")
            console.print(f"   Reason: {suggestion.reason}")
            console.print(f"   Impact: {suggestion.impact}")
            console.print(f"   Effort: {suggestion.effort}")
            console.print(f"\n   [dim]Before:[/dim]")
            console.print(f"   {suggestion.before_code[:100]}...")
            console.print(f"\n   [dim]After:[/dim]")
            console.print(f"   {suggestion.after_code[:100]}...")
            console.print()


@tdd_group.command("workflow")
@click.argument("golden_data", type=click.Path(exists=True))
@click.argument("code_dir", type=click.Path(exists=True))
@click.option(
    "--test-dir",
    type=click.Path(),
    default="./tests",
    help="Test directory (default: ./tests)"
)
@click.option(
    "--output-report",
    "-o",
    type=click.Path(),
    default="./tdd_report.json",
    help="Output report file (default: ./tdd_report.json)"
)
@click.option(
    "--run-tests/--skip-tests",
    default=True,
    help="Run pytest after test generation (default: true)"
)
def workflow_cmd(
    golden_data: str,
    code_dir: str,
    test_dir: str,
    output_report: str,
    run_tests: bool
):
    """
    Run complete TDD workflow: RED → GREEN → REFACTOR.

    Steps:
    1. Phase 4.5 (RED): Generate tests from Golden Data
    2. Phase 5 (GREEN): Run tests (expected to fail initially)
    3. Phase 5.5 (REFACTOR): Analyze code for quality and suggestions

    Example:
        caas tdd workflow ./golden_data.json ./src --output-report ./report.json
    """
    asyncio.run(_run_workflow(golden_data, code_dir, test_dir, output_report, run_tests))


async def _run_workflow(
    golden_data_path: str,
    code_dir_path: str,
    test_dir_path: str,
    output_report_path: str,
    run_tests: bool
):
    """Async implementation of TDD workflow"""

    console.print("\n")
    console.print(Panel(
        "[bold cyan]Complete TDD Workflow: RED → GREEN → REFACTOR[/bold cyan]",
        border_style="cyan"
    ))

    workflow_results = {
        "red_phase": {},
        "green_phase": {},
        "refactor_phase": {},
        "summary": {}
    }

    # ========================================
    # PHASE 4.5: TDD RED - Generate Tests
    # ========================================

    console.print("\n[bold yellow]Step 1/3: Phase 4.5 (RED) - Generating Tests...[/bold yellow]\n")

    await _generate_tests(golden_data_path, test_dir_path, "unit,integration,edge_case", False)

    workflow_results["red_phase"]["status"] = "complete"
    workflow_results["red_phase"]["test_dir"] = test_dir_path

    # ========================================
    # PHASE 5: GREEN - Run Tests
    # ========================================

    if run_tests:
        console.print("\n[bold yellow]Step 2/3: Phase 5 (GREEN) - Running Tests...[/bold yellow]\n")

        import subprocess
        try:
            result = subprocess.run(
                ["pytest", test_dir_path, "-v", "--tb=short"],
                capture_output=True,
                text=True,
                timeout=60
            )

            console.print(result.stdout)
            if result.returncode != 0:
                console.print("[yellow]⚠️  Some tests failed (expected in RED phase)[/yellow]")
                workflow_results["green_phase"]["status"] = "tests_failing"
            else:
                console.print("[green]✅ All tests passed![/green]")
                workflow_results["green_phase"]["status"] = "tests_passing"

        except subprocess.TimeoutExpired:
            console.print("[red]❌ Test execution timed out[/red]")
            workflow_results["green_phase"]["status"] = "timeout"
        except FileNotFoundError:
            console.print("[yellow]⚠️  pytest not found. Skipping test execution.[/yellow]")
            workflow_results["green_phase"]["status"] = "skipped"
    else:
        console.print("\n[yellow]Step 2/3: Skipped (--skip-tests)[/yellow]\n")
        workflow_results["green_phase"]["status"] = "skipped"

    # ========================================
    # PHASE 5.5: REFACTOR - Analyze Code
    # ========================================

    console.print("\n[bold yellow]Step 3/3: Phase 5.5 (REFACTOR) - Analyzing Code...[/bold yellow]\n")

    import glob
    code_files = glob.glob(f"{code_dir_path}/**/*.py", recursive=True)

    if not code_files:
        console.print(f"[yellow]⚠️  No Python files found in {code_dir_path}[/yellow]")
        workflow_results["refactor_phase"]["status"] = "no_files"
    else:
        console.print(f"Found {len(code_files)} Python files to analyze\n")

        all_reports = []
        total_smells = 0
        total_suggestions = 0
        avg_quality = 0.0

        for code_file in code_files[:10]:  # Analyze first 10 files
            try:
                with open(code_file, 'r') as f:
                    code = f.read()

                engine = TDDRefactorEngine()
                report = engine.analyze_code(code, code_file)

                all_reports.append(report.to_dict())
                total_smells += len(report.code_smells)
                total_suggestions += len(report.refactoring_suggestions)
                avg_quality += report.code_quality_score

                console.print(f"  ✓ {code_file}: {report.code_quality_score:.1f}/10.0 "
                             f"({len(report.code_smells)} smells)")

            except Exception as e:
                console.print(f"  ✗ {code_file}: Error - {e}")

        avg_quality = avg_quality / len(all_reports) if all_reports else 0.0

        workflow_results["refactor_phase"]["status"] = "complete"
        workflow_results["refactor_phase"]["files_analyzed"] = len(all_reports)
        workflow_results["refactor_phase"]["total_smells"] = total_smells
        workflow_results["refactor_phase"]["total_suggestions"] = total_suggestions
        workflow_results["refactor_phase"]["average_quality_score"] = round(avg_quality, 2)
        workflow_results["refactor_phase"]["reports"] = all_reports

    # ========================================
    # Generate Summary Report
    # ========================================

    console.print("\n[bold]📊 TDD Workflow Summary:[/bold]\n")

    summary_table = Table(show_header=True, header_style="bold cyan")
    summary_table.add_column("Phase", style="cyan")
    summary_table.add_column("Status", style="green")
    summary_table.add_column("Details", style="white")

    summary_table.add_row(
        "Phase 4.5 (RED)",
        workflow_results["red_phase"].get("status", "N/A"),
        f"Tests generated in {test_dir_path}"
    )

    summary_table.add_row(
        "Phase 5 (GREEN)",
        workflow_results["green_phase"].get("status", "N/A"),
        "Run tests and implement features"
    )

    if workflow_results["refactor_phase"].get("status") == "complete":
        summary_table.add_row(
            "Phase 5.5 (REFACTOR)",
            "complete",
            f"{workflow_results['refactor_phase']['files_analyzed']} files analyzed, "
            f"avg quality: {workflow_results['refactor_phase']['average_quality_score']}/10.0"
        )
    else:
        summary_table.add_row(
            "Phase 5.5 (REFACTOR)",
            workflow_results["refactor_phase"].get("status", "N/A"),
            "No files analyzed"
        )

    console.print(summary_table)

    # Save workflow report
    workflow_results["summary"]["timestamp"] = str(__import__("datetime").datetime.now())
    workflow_results["summary"]["golden_data"] = golden_data_path
    workflow_results["summary"]["code_dir"] = code_dir_path
    workflow_results["summary"]["test_dir"] = test_dir_path

    with open(output_report_path, 'w') as f:
        json.dump(workflow_results, f, indent=2)

    console.print(f"\n[green]✅ Workflow report saved to: {output_report_path}[/green]")

    console.print("\n[bold yellow]Next Steps:[/bold yellow]")
    console.print("  1. Review test failures and implement features (GREEN phase)")
    console.print("  2. Run tests until all pass: [cyan]pytest[/cyan]")
    console.print("  3. Review refactoring suggestions in the report")
    console.print("  4. Apply refactorings while keeping tests green (REFACTOR phase)")
