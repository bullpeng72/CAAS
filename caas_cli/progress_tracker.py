"""
CLI Progress Tracker

Real-time progress display for BMAD phases using Rich library.
Provides visual feedback to users during code generation.
"""

import time
from typing import Optional

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table


class CLIProgressTracker:
    """
    Progress Tracker for CLI

    Displays real-time progress for each BMAD phase with:
    - Phase name and status
    - Spinner during execution
    - Completion time
    - Success/failure indicators
    """

    def __init__(self, console: Optional[Console] = None):
        """
        Initialize progress tracker.

        Args:
            console: Rich console instance (creates new if None)
        """
        self.console = console or Console()
        self.progress: Optional[Progress] = None
        self.phase_tasks = {}
        self.phase_times = {}
        self.current_phase = None

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
        return False

    def start(self):
        """Start progress tracking."""
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=self.console,
        )
        self.progress.start()

    def stop(self):
        """Stop progress tracking."""
        if self.progress:
            self.progress.stop()
            self.progress = None

    def start_phase(self, phase_name: str, description: str = ""):
        """
        Start a new phase.

        Args:
            phase_name: Name of the phase (e.g., "Phase 0: Concretization")
            description: Optional description
        """
        if not self.progress:
            return

        display_text = f"{phase_name}"
        if description:
            display_text += f" - {description}"

        task_id = self.progress.add_task(
            display_text, total=None
        )  # Indeterminate progress

        self.phase_tasks[phase_name] = task_id
        self.phase_times[phase_name] = time.time()
        self.current_phase = phase_name

    def update_phase(self, phase_name: str, message: str):
        """
        Update phase with a message.

        Args:
            phase_name: Name of the phase
            message: Status message
        """
        if not self.progress or phase_name not in self.phase_tasks:
            return

        task_id = self.phase_tasks[phase_name]
        self.progress.update(
            task_id, description=f"[bold blue]{phase_name}[/bold blue] - {message}"
        )

    def complete_phase(self, phase_name: str, success: bool = True, message: str = ""):
        """
        Mark phase as completed.

        Args:
            phase_name: Name of the phase
            success: Whether phase succeeded
            message: Optional completion message
        """
        if not self.progress or phase_name not in self.phase_tasks:
            return

        task_id = self.phase_tasks[phase_name]
        duration = time.time() - self.phase_times[phase_name]

        if success:
            status = "✅"
            style = "green"
        else:
            status = "❌"
            style = "red"

        display_text = f"{status} {phase_name}"
        if message:
            display_text += f" - {message}"
        display_text += f" ({duration:.1f}s)"

        self.progress.update(
            task_id,
            description=f"[{style}]{display_text}[/{style}]",
            completed=100,
            total=100,
        )

    def debug(self, message: str):
        """
        Display debug message.

        Args:
            message: Debug message
        """
        if self.progress:
            self.console.print(f"[dim]🐛 {message}[/dim]")

    def info(self, message: str):
        """
        Display info message.

        Args:
            message: Info message
        """
        if self.progress:
            self.console.print(f"[cyan]ℹ️  {message}[/cyan]")

    def warning(self, message: str):
        """
        Display warning message.

        Args:
            message: Warning message
        """
        if self.progress:
            self.console.print(f"[yellow]⚠️  {message}[/yellow]")

    def error(self, message: str):
        """
        Display error message.

        Args:
            message: Error message
        """
        if self.progress:
            self.console.print(f"[red]❌ {message}[/red]")

    def success(self, message: str):
        """
        Display success message.

        Args:
            message: Success message
        """
        if self.progress:
            self.console.print(f"[green]✅ {message}[/green]")

    def log_message(self, message: str, level: str = "info"):
        """
        Display log message with specified level.

        Args:
            message: Log message
            level: Log level (debug, info, warning, error)
        """
        level_map = {
            "debug": self.debug,
            "info": self.info,
            "warning": self.warning,
            "error": self.error,
        }
        log_func = level_map.get(level, self.info)
        log_func(message)

    def agent_working(self, agent_name: str, message: str):
        """
        Display agent working message.

        Args:
            agent_name: Name of the agent
            message: Status message
        """
        if self.progress:
            self.console.print(f"[blue]🤖 [{agent_name}] {message}[/blue]")

    def agent_completed(self, agent_name: str, duration: float, iterations: int = 1):
        """
        Display agent completion message.

        Args:
            agent_name: Name of the agent
            duration: Time taken in seconds
            iterations: Number of iterations
        """
        if self.progress:
            iter_text = f" ({iterations} iterations)" if iterations > 1 else ""
            self.console.print(
                f"[green]✅ [{agent_name}] Completed in {duration:.1f}s{iter_text}[/green]"
            )

    def validation_start(self, validator_name: str, items_count: int):
        """
        Display validation start message.

        Args:
            validator_name: Name of the validator
            items_count: Number of items to validate
        """
        if self.progress:
            self.console.print(
                f"[cyan]🔍 {validator_name}: Validating {items_count} items...[/cyan]"
            )

    def validation_result(
        self, validator_name: str, passed: bool, issues_count: int = 0
    ):
        """
        Display validation result message.

        Args:
            validator_name: Name of the validator
            passed: Whether validation passed
            issues_count: Number of issues found
        """
        if self.progress:
            if passed:
                self.console.print(f"[green]✅ {validator_name}: Passed[/green]")
            else:
                self.console.print(
                    f"[yellow]⚠️  {validator_name}: Found {issues_count} issues[/yellow]"
                )

    def display_summary(
        self,
        phases_completed: list,
        total_duration: float,
        success: bool,
        errors: list = None,
    ):
        """
        Display final summary.

        Args:
            phases_completed: List of completed phase names
            total_duration: Total execution time in seconds
            success: Overall success status
            errors: List of error messages (if any)
        """
        # Create summary table
        table = Table(
            title="🎯 BMAD Execution Summary",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan",
        )

        table.add_column("Phase", style="cyan", no_wrap=True)
        table.add_column("Status", justify="center", style="green")
        table.add_column("Duration", justify="right")

        # Add phase rows
        for phase_name in phases_completed:
            duration = self.phase_times.get(phase_name, 0)
            if duration > 0:
                duration = time.time() - duration

            table.add_row(phase_name, "✅ Complete", f"{duration:.1f}s")

        # Display table
        self.console.print()
        self.console.print(table)

        # Display overall status
        self.console.print()
        if success:
            self.console.print(
                Panel(
                    f"[green bold]✅ Generation Successful![/green bold]\n"
                    f"Total time: {total_duration:.1f}s\n"
                    f"Phases completed: {len(phases_completed)}",
                    box=box.DOUBLE,
                    border_style="green",
                )
            )
        else:
            error_text = "\n".join(errors) if errors else "Unknown error"
            self.console.print(
                Panel(
                    f"[red bold]❌ Generation Failed[/red bold]\n"
                    f"Total time: {total_duration:.1f}s\n"
                    f"Errors:\n{error_text}",
                    box=box.DOUBLE,
                    border_style="red",
                )
            )


class SimpleProgressReporter:
    """
    Simple progress reporter compatible with ProgressReporterProtocol.

    This is a lightweight adapter that wraps CLIProgressTracker
    and implements the protocol expected by BMADEngine.
    """

    def __init__(self, tracker: Optional[CLIProgressTracker] = None):
        """
        Initialize reporter.

        Args:
            tracker: CLI progress tracker (creates new if None)
        """
        self.tracker = tracker or CLIProgressTracker()
        self._is_running = False

    def start(self):
        """Start progress reporting."""
        if not self._is_running:
            self.tracker.start()
            self._is_running = True

    def stop(self):
        """Stop progress reporting."""
        if self._is_running:
            self.tracker.stop()
            self._is_running = False

    def start_workflow(self, workflow_name: str, total_phases: int):
        """
        Start a workflow execution.

        Args:
            workflow_name: Name of the workflow being executed
            total_phases: Total number of phases in the workflow
        """
        if not self._is_running:
            self.start()

        # Display workflow start message
        from rich import box
        from rich.panel import Panel

        self.tracker.console.print()
        self.tracker.console.print(
            Panel(
                f"[bold cyan]🚀 Starting Workflow[/bold cyan]\n"
                f"Workflow: {workflow_name}\n"
                f"Total Phases: {total_phases}",
                box=box.ROUNDED,
                border_style="cyan",
            )
        )
        self.tracker.console.print()

    def complete_workflow(self, success: bool, summary: dict = None):
        """
        Complete a workflow execution.

        Args:
            success: Whether the workflow completed successfully
            summary: Optional summary dictionary with workflow results
        """
        from rich import box
        from rich.panel import Panel

        self.tracker.console.print()

        if success:
            # Build success message
            msg = "[bold green]✅ Workflow Completed Successfully![/bold green]\n"
            if summary:
                if "total_duration" in summary:
                    msg += f"\nTotal Duration: {summary['total_duration']:.1f}s"
                if "phases_completed" in summary:
                    msg += f"\nPhases Completed: {summary['phases_completed']}"
                if "implementation_rate" in summary:
                    msg += (
                        f"\nImplementation Rate: {summary['implementation_rate']:.1f}%"
                    )
                if "agents_count" in summary:
                    msg += f"\nAgents Created: {summary['agents_count']}"

            self.tracker.console.print(
                Panel(
                    msg, box=box.DOUBLE, border_style="green", title="Workflow Complete"
                )
            )
        else:
            # Build failure message
            msg = "[bold red]❌ Workflow Failed[/bold red]\n"
            if summary:
                if "total_duration" in summary:
                    msg += f"\nDuration: {summary['total_duration']:.1f}s"
                if "phases_completed" in summary:
                    msg += f"\nPhases Completed: {summary['phases_completed']}"
                if "error" in summary:
                    msg += f"\nError: {summary['error']}"

            self.tracker.console.print(
                Panel(msg, box=box.DOUBLE, border_style="red", title="Workflow Failed")
            )

        self.tracker.console.print()

    def start_phase(self, phase_name: str, agent_name: str = "", description: str = ""):
        """Start a new phase."""
        if not self._is_running:
            self.start()
        self.tracker.start_phase(phase_name, description)

    def update_phase(self, phase_name: str, message: str):
        """Update phase progress."""
        self.tracker.update_phase(phase_name, message)

    def complete_phase(self, phase_name: str, duration: float, success: bool = True):
        """Complete a phase."""
        self.tracker.complete_phase(phase_name, success)

    def debug(self, message: str):
        """Display debug message."""
        self.tracker.debug(message)

    def info(self, message: str):
        """Display info message."""
        self.tracker.info(message)

    def warning(self, message: str):
        """Display warning message."""
        self.tracker.warning(message)

    def error(self, message: str):
        """Display error message."""
        self.tracker.error(message)

    def success(self, message: str):
        """Display success message."""
        self.tracker.success(message)

    def log_message(self, message: str, level: str = "info"):
        """Display log message with specified level."""
        self.tracker.log_message(message, level)

    def agent_working(self, agent_name: str, message: str):
        """Display agent working message."""
        self.tracker.agent_working(agent_name, message)

    def agent_completed(self, agent_name: str, duration: float, iterations: int = 1):
        """Display agent completion message."""
        self.tracker.agent_completed(agent_name, duration, iterations)

    def validation_start(self, validator_name: str, items_count: int):
        """Display validation start message."""
        self.tracker.validation_start(validator_name, items_count)

    def validation_result(
        self, validator_name: str, passed: bool, issues_count: int = 0
    ):
        """Display validation result message."""
        self.tracker.validation_result(validator_name, passed, issues_count)

    def display_summary(self, **kwargs):
        """Display execution summary."""
        self.tracker.display_summary(**kwargs)

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
        return False
