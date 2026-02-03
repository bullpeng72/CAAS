"""
Progress Reporter

Real-time progress reporting for BMAD 6-Phase workflow execution.
Provides configurable verbosity levels and rich console output.
"""

import sys
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from caas_framework.reporting.interfaces import VerbosityLevel

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


class PhaseStatus(Enum):
    """Phase execution status"""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class PhaseProgress:
    """Progress information for a single phase"""

    phase_name: str
    status: PhaseStatus = PhaseStatus.PENDING
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    agent_name: Optional[str] = None
    iterations: int = 0
    validation_score: Optional[float] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration(self) -> Optional[float]:
        """Calculate phase duration"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        elif self.start_time:
            return time.time() - self.start_time
        return None

    @property
    def status_icon(self) -> str:
        """Get status icon"""
        return {
            PhaseStatus.PENDING: "⏳",
            PhaseStatus.IN_PROGRESS: "🔄",
            PhaseStatus.COMPLETED: "✅",
            PhaseStatus.FAILED: "❌",
            PhaseStatus.SKIPPED: "⏭️",
        }.get(self.status, "❓")


class ProgressReporter:
    """
    Progress Reporter for BMAD Workflow

    Provides real-time progress reporting with configurable verbosity levels.
    Supports both Rich (colorful) and plain console output.

    Usage:
        reporter = ProgressReporter(verbosity=VerbosityLevel.NORMAL)

        reporter.start_workflow("Building CrewAI Bot")
        reporter.start_phase("Phase 1: Discovery", "RequirementAnalyst")
        reporter.agent_working("RequirementAnalyst", "Analyzing requirements...")
        reporter.complete_phase("Phase 1: Discovery", duration=12.5)
        reporter.complete_workflow(success=True)
    """

    def __init__(
        self,
        verbosity: VerbosityLevel = VerbosityLevel.NORMAL,
        use_rich: bool = True,
        file=None,
    ):
        """
        Initialize progress reporter

        Args:
            verbosity: Verbosity level for output
            use_rich: Use Rich library for colorful output (if available)
            file: Output file (default: sys.stdout)
        """
        self.verbosity = verbosity
        self.use_rich = use_rich and RICH_AVAILABLE
        self.file = file or sys.stdout

        if self.use_rich:
            self.console = Console(file=self.file)
        else:
            self.console = None

        # State tracking
        self.workflow_name: Optional[str] = None
        self.workflow_start_time: Optional[float] = None
        self.phases: Dict[str, PhaseProgress] = {}
        self.current_phase: Optional[str] = None
        self.total_phases: int = 6  # BMAD has 6 phases

    # ===========================================
    # Workflow-level reporting
    # ===========================================

    def start_workflow(self, workflow_name: str, total_phases: Optional[int] = None):
        """
        Start workflow execution

        Args:
            workflow_name: Name of the workflow
            total_phases: Total number of phases (default: 6 for BMAD)
        """
        self.workflow_name = workflow_name
        self.workflow_start_time = time.time()
        if total_phases:
            self.total_phases = total_phases

        if self.verbosity == VerbosityLevel.QUIET:
            return

        if self.use_rich:
            self.console.rule(f"[bold cyan]{workflow_name}[/bold cyan]", style="cyan")
            self.console.print()
        else:
            header = "=" * 70
            print(header, file=self.file)
            print(f"{workflow_name}", file=self.file)
            print(header, file=self.file)
            print(file=self.file)

    def end_workflow(
        self, success: bool, duration: float, summary: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        End workflow reporting (Protocol-compatible method).

        Args:
            success: Whether workflow succeeded
            duration: Total workflow duration in seconds
            summary: Optional summary data
        """
        self.complete_workflow(success=success, summary=summary)

    def complete_workflow(
        self, success: bool = True, summary: Optional[Dict[str, Any]] = None
    ):
        """
        Complete workflow execution

        Args:
            success: Whether workflow succeeded
            summary: Optional summary information
        """
        if self.verbosity == VerbosityLevel.QUIET:
            return

        duration = (
            time.time() - self.workflow_start_time if self.workflow_start_time else 0
        )

        # Count phase statuses
        completed = sum(
            1 for p in self.phases.values() if p.status == PhaseStatus.COMPLETED
        )
        failed = sum(1 for p in self.phases.values() if p.status == PhaseStatus.FAILED)
        total_errors = sum(len(p.errors) for p in self.phases.values())
        total_warnings = sum(len(p.warnings) for p in self.phases.values())

        if self.use_rich:
            self.console.print()
            self.console.rule("[bold]Workflow Summary[/bold]")

            # Status table
            table = Table(title="Phase Summary", show_header=True)
            table.add_column("Phase", style="cyan")
            table.add_column("Status", style="bold")
            table.add_column("Duration", justify="right")
            table.add_column("Agent")
            table.add_column("Issues", justify="right")

            for phase_name, phase in self.phases.items():
                duration_str = f"{phase.duration:.2f}s" if phase.duration else "N/A"
                issues = len(phase.errors) + len(phase.warnings)
                issues_str = f"{issues}" if issues > 0 else "-"

                status_color = {
                    PhaseStatus.COMPLETED: "green",
                    PhaseStatus.FAILED: "red",
                    PhaseStatus.IN_PROGRESS: "yellow",
                    PhaseStatus.PENDING: "dim",
                    PhaseStatus.SKIPPED: "dim",
                }.get(phase.status, "white")

                table.add_row(
                    phase_name,
                    f"[{status_color}]{phase.status_icon} {phase.status.value}[/{status_color}]",
                    duration_str,
                    phase.agent_name or "-",
                    issues_str,
                )

            self.console.print(table)

            # Overall result
            if success:
                result_panel = Panel(
                    f"[bold green]✅ Workflow Completed Successfully[/bold green]\n\n"
                    f"Duration: {duration:.2f}s\n"
                    f"Phases: {completed}/{len(self.phases)} completed\n"
                    f"Errors: {total_errors}, Warnings: {total_warnings}",
                    border_style="green",
                )
            else:
                result_panel = Panel(
                    f"[bold red]❌ Workflow Failed[/bold red]\n\n"
                    f"Duration: {duration:.2f}s\n"
                    f"Phases: {completed}/{len(self.phases)} completed, {failed} failed\n"
                    f"Errors: {total_errors}, Warnings: {total_warnings}",
                    border_style="red",
                )

            self.console.print(result_panel)

        else:
            # Plain text output
            print("\n" + "=" * 70, file=self.file)
            print("Workflow Summary", file=self.file)
            print("=" * 70, file=self.file)

            for phase_name, phase in self.phases.items():
                duration_str = f"{phase.duration:.2f}s" if phase.duration else "N/A"
                print(
                    f"{phase.status_icon} {phase_name}: {phase.status.value} ({duration_str})",
                    file=self.file,
                )

            print("=" * 70, file=self.file)
            icon = "✅" if success else "❌"
            status = "Completed Successfully" if success else "Failed"
            print(f"{icon} {status} (Duration: {duration:.2f}s)", file=self.file)
            print(
                f"Phases: {completed}/{len(self.phases)}, Errors: {total_errors}, Warnings: {total_warnings}",
                file=self.file,
            )
            print("=" * 70, file=self.file)

    # ===========================================
    # Phase-level reporting
    # ===========================================

    def start_phase(
        self,
        phase_name: str,
        agent_name: Optional[str] = None,
        description: Optional[str] = None,
    ):
        """
        Start a phase

        Args:
            phase_name: Name of the phase
            agent_name: Name of the agent executing this phase
            description: Optional phase description
        """
        if phase_name not in self.phases:
            self.phases[phase_name] = PhaseProgress(phase_name=phase_name)

        phase = self.phases[phase_name]
        phase.status = PhaseStatus.IN_PROGRESS
        phase.start_time = time.time()
        phase.agent_name = agent_name

        self.current_phase = phase_name

        if self.verbosity.value < VerbosityLevel.MINIMAL.value:
            return

        if self.use_rich:
            self.console.rule(f"[bold blue]{phase_name}[/bold blue]", style="blue")
            if agent_name:
                self.console.print(f"  [dim]Agent:[/dim] [cyan]{agent_name}[/cyan]")
            if description:
                self.console.print(f"  [dim]{description}[/dim]")
            self.console.print()
        else:
            print("\n" + "=" * 60, file=self.file)
            print(f"{phase_name}", file=self.file)
            if agent_name:
                print(f"  Agent: {agent_name}", file=self.file)
            if description:
                print(f"  {description}", file=self.file)
            print("=" * 60, file=self.file)

    def complete_phase(
        self,
        phase_name: str,
        success: bool = True,
        duration: Optional[float] = None,
        validation_score: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Complete a phase

        Args:
            phase_name: Name of the phase
            success: Whether phase succeeded
            duration: Override duration (otherwise calculated)
            validation_score: Validation/quality score (0-1)
            metadata: Additional metadata
        """
        if phase_name not in self.phases:
            self.phases[phase_name] = PhaseProgress(phase_name=phase_name)

        phase = self.phases[phase_name]
        phase.status = PhaseStatus.COMPLETED if success else PhaseStatus.FAILED
        phase.end_time = time.time()
        if validation_score is not None:
            phase.validation_score = validation_score
        if metadata:
            phase.metadata.update(metadata)

        if self.verbosity.value < VerbosityLevel.MINIMAL.value:
            return

        actual_duration = duration or phase.duration or 0

        if self.use_rich:
            status_color = "green" if success else "red"
            icon = "✅" if success else "❌"

            message = f"[{status_color}]{icon} Phase completed in {actual_duration:.2f}s[/{status_color}]"

            if validation_score is not None:
                score_color = (
                    "green"
                    if validation_score >= 0.9
                    else "yellow"
                    if validation_score >= 0.7
                    else "red"
                )
                message += f" | Validation: [{score_color}]{validation_score:.1%}[/{score_color}]"

            self.console.print(f"  {message}")

        else:
            icon = "✅" if success else "❌"
            message = f"  {icon} Phase completed in {actual_duration:.2f}s"
            if validation_score is not None:
                message += f" | Validation: {validation_score:.1%}"
            print(message, file=self.file)

    def skip_phase(self, phase_name: str, reason: str):
        """
        Skip a phase

        Args:
            phase_name: Name of the phase
            reason: Reason for skipping
        """
        if phase_name not in self.phases:
            self.phases[phase_name] = PhaseProgress(phase_name=phase_name)

        self.phases[phase_name].status = PhaseStatus.SKIPPED

        if self.verbosity.value >= VerbosityLevel.NORMAL.value:
            if self.use_rich:
                self.console.print(f"  [dim]⏭️  Skipped: {reason}[/dim]")
            else:
                print(f"  ⏭️ Skipped: {reason}", file=self.file)

    # ===========================================
    # Agent-level reporting
    # ===========================================

    def agent_working(self, agent_name: str, message: str):
        """
        Report agent working status

        Args:
            agent_name: Name of the agent
            message: Status message
        """
        if self.verbosity.value < VerbosityLevel.NORMAL.value:
            return

        if self.use_rich:
            self.console.print(f"  [cyan][{agent_name}][/cyan] {message}")
        else:
            print(f"  [{agent_name}] {message}", file=self.file)

    def agent_completed(self, agent_name: str, duration: float, iterations: int = 1):
        """
        Report agent completion

        Args:
            agent_name: Name of the agent
            duration: Execution duration
            iterations: Number of iterations (for refinement loops)
        """
        if self.verbosity.value < VerbosityLevel.NORMAL.value:
            return

        if self.current_phase and self.current_phase in self.phases:
            self.phases[self.current_phase].iterations = iterations

        iteration_str = f" ({iterations} iterations)" if iterations > 1 else ""

        if self.use_rich:
            self.console.print(
                f"  [green][{agent_name}] ✅ Completed in {duration:.2f}s{iteration_str}[/green]"
            )
        else:
            print(
                f"  [{agent_name}] ✅ Completed in {duration:.2f}s{iteration_str}",
                file=self.file,
            )

    def agent_output(self, agent_name: str, output: Dict[str, Any]):
        """
        Report agent output (DEBUG level only)

        Args:
            agent_name: Name of the agent
            output: Agent output data
        """
        if self.verbosity != VerbosityLevel.DEBUG:
            return

        if self.use_rich:
            self.console.print(f"  [dim][{agent_name}] Output:[/dim]")
            # Print summary of output
            for key, value in output.items():
                if isinstance(value, (list, dict)):
                    count = len(value)
                    self.console.print(f"    [dim]{key}: {count} items[/dim]")
                else:
                    self.console.print(f"    [dim]{key}: {value}[/dim]")
        else:
            print(f"  [{agent_name}] Output:", file=self.file)
            for key, value in output.items():
                if isinstance(value, (list, dict)):
                    print(f"    {key}: {len(value)} items", file=self.file)
                else:
                    print(f"    {key}: {value}", file=self.file)

    # ===========================================
    # Validation & Feedback reporting
    # ===========================================

    def validation_start(self, validator_name: str, item_count: int):
        """
        Report validation start

        Args:
            validator_name: Name of the validator
            item_count: Number of items being validated
        """
        if self.verbosity.value < VerbosityLevel.VERBOSE.value:
            return

        if self.use_rich:
            self.console.print(
                f"  [yellow][{validator_name}] Validating {item_count} items...[/yellow]"
            )
        else:
            print(
                f"  [{validator_name}] Validating {item_count} items...", file=self.file
            )

    def validation_result(
        self,
        validator_name: str,
        passed: bool,
        issues_count: int,
        score: Optional[float] = None,
    ):
        """
        Report validation result

        Args:
            validator_name: Name of the validator
            passed: Whether validation passed
            issues_count: Number of issues found
            score: Validation score (0-1)
        """
        if self.verbosity.value < VerbosityLevel.VERBOSE.value:
            return

        if passed:
            icon = "✅"
            color = "green"
            message = "Validation passed"
        else:
            icon = "⚠️"
            color = "yellow"
            message = f"{issues_count} issues found"

        if score is not None:
            message += f" (score: {score:.1%})"

        if self.use_rich:
            self.console.print(
                f"  [{color}][{validator_name}] {icon} {message}[/{color}]"
            )
        else:
            print(f"  [{validator_name}] {icon} {message}", file=self.file)

    def feedback_iteration(
        self, agent_name: str, iteration: int, max_iterations: int, issues_count: int
    ):
        """
        Report feedback loop iteration

        Args:
            agent_name: Name of the agent
            iteration: Current iteration (1-indexed)
            max_iterations: Maximum iterations
            issues_count: Number of issues being addressed
        """
        if self.verbosity.value < VerbosityLevel.VERBOSE.value:
            return

        if self.use_rich:
            self.console.print(
                f"  [yellow][{agent_name}] Feedback iteration {iteration}/{max_iterations}: "
                f"Addressing {issues_count} issues[/yellow]"
            )
        else:
            print(
                f"  [{agent_name}] Feedback iteration {iteration}/{max_iterations}: "
                f"Addressing {issues_count} issues",
                file=self.file,
            )

    # ===========================================
    # Error & Warning reporting
    # ===========================================

    def error(self, message: str, phase: Optional[str] = None):
        """
        Report an error

        Args:
            message: Error message
            phase: Optional phase name
        """
        target_phase = phase or self.current_phase
        if target_phase and target_phase in self.phases:
            self.phases[target_phase].errors.append(message)

        if self.use_rich:
            self.console.print(f"  [bold red]❌ Error:[/bold red] {message}")
        else:
            print(f"  ❌ Error: {message}", file=self.file)

    def warning(self, message: str, phase: Optional[str] = None):
        """
        Report a warning

        Args:
            message: Warning message
            phase: Optional phase name
        """
        target_phase = phase or self.current_phase
        if target_phase and target_phase in self.phases:
            self.phases[target_phase].warnings.append(message)

        if self.verbosity.value >= VerbosityLevel.NORMAL.value:
            if self.use_rich:
                self.console.print(f"  [yellow]⚠️  Warning:[/yellow] {message}")
            else:
                print(f"  ⚠️ Warning: {message}", file=self.file)

    def info(self, message: str):
        """
        Report an informational message

        Args:
            message: Info message
        """
        if self.verbosity.value >= VerbosityLevel.VERBOSE.value:
            if self.use_rich:
                self.console.print(f"  [dim]ℹ️  {message}[/dim]")
            else:
                print(f"  ℹ️ {message}", file=self.file)

    def debug(self, message: str):
        """
        Report a debug message

        Args:
            message: Debug message
        """
        if self.verbosity == VerbosityLevel.DEBUG:
            if self.use_rich:
                self.console.print(f"  [dim cyan]🐛 DEBUG: {message}[/dim cyan]")
            else:
                print(f"  🐛 DEBUG: {message}", file=self.file)

    # ===========================================
    # Protocol-compatible methods
    # ===========================================

    def log_message(self, message: str, level: str = "info") -> None:
        """
        Log a message with appropriate styling (Protocol-compatible method).

        Args:
            message: Message text
            level: Log level ("debug", "info", "warning", "error", "success")
        """
        if level == "error":
            self.error(message)
        elif level == "warning":
            self.warning(message)
        elif level == "debug":
            self.debug(message)
        elif level == "success":
            if self.verbosity.value >= VerbosityLevel.NORMAL.value:
                if self.use_rich:
                    self.console.print(f"  [green]✅ {message}[/green]")
                else:
                    print(f"  ✅ {message}", file=self.file)
        else:  # info
            self.info(message)

    def update_phase_progress(
        self, phase_name: str, message: str, progress: Optional[float] = None
    ) -> None:
        """
        Update phase progress (Protocol-compatible method).

        Args:
            phase_name: Phase name
            message: Progress message
            progress: Progress percentage (0.0-1.0), None if indeterminate
        """
        if self.verbosity.value >= VerbosityLevel.VERBOSE.value:
            progress_str = f" ({progress:.0%})" if progress is not None else ""
            if self.use_rich:
                self.console.print(f"  [dim]•[/dim] {message}{progress_str}")
            else:
                print(f"  • {message}{progress_str}", file=self.file)

    def log_validation(
        self, phase_name: str, passed: bool, issues: Optional[List[str]] = None
    ) -> None:
        """
        Log validation result (Protocol-compatible method).

        Args:
            phase_name: Phase name
            passed: Whether validation passed
            issues: List of validation issues
        """
        if self.verbosity.value >= VerbosityLevel.VERBOSE.value:
            if passed:
                if self.use_rich:
                    self.console.print(
                        f"  [green]✓ Validation passed for {phase_name}[/green]"
                    )
                else:
                    print(f"  ✓ Validation passed for {phase_name}", file=self.file)
            else:
                if self.use_rich:
                    self.console.print(
                        f"  [red]✗ Validation failed for {phase_name}[/red]"
                    )
                else:
                    print(f"  ✗ Validation failed for {phase_name}", file=self.file)

                if issues:
                    for issue in issues[:5]:  # Show first 5
                        if self.use_rich:
                            self.console.print(f"    [dim]• {issue}[/dim]")
                        else:
                            print(f"    • {issue}", file=self.file)

    def log_feedback_iteration(
        self, phase_name: str, iteration: int, total_iterations: int
    ) -> None:
        """
        Log feedback loop iteration (Protocol-compatible method).

        Args:
            phase_name: Phase name
            iteration: Current iteration
            total_iterations: Total iterations
        """
        if self.verbosity.value >= VerbosityLevel.VERBOSE.value:
            if self.use_rich:
                self.console.print(
                    f"  [yellow]🔄 Feedback iteration {iteration}/{total_iterations} "
                    f"for {phase_name}[/yellow]"
                )
            else:
                print(
                    f"  🔄 Feedback iteration {iteration}/{total_iterations} "
                    f"for {phase_name}",
                    file=self.file,
                )

    # ===========================================
    # Utility methods
    # ===========================================

    def get_progress_percentage(self) -> float:
        """Get overall progress percentage (0-100)"""
        if not self.phases:
            return 0.0

        completed = sum(
            1 for p in self.phases.values() if p.status == PhaseStatus.COMPLETED
        )
        return (completed / self.total_phases) * 100.0

    def get_current_phase_name(self) -> Optional[str]:
        """Get current phase name"""
        return self.current_phase

    def get_phase_progress(self, phase_name: str) -> Optional[PhaseProgress]:
        """Get progress for a specific phase"""
        return self.phases.get(phase_name)
