"""
Rich-based Progress Reporter for CLI

Implements ProgressReporter protocol using Rich library for beautiful console output.
"""

from typing import Optional, Dict, Any, List
import time

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from caas_framework.reporting.interfaces import (
    ProgressReporter,
    VerbosityLevel
)


class RichProgressReporter:
    """
    Rich-based implementation of ProgressReporter protocol.

    Provides colorful, formatted console output for CLI using Rich library.
    """

    def __init__(
        self,
        verbosity: VerbosityLevel = VerbosityLevel.NORMAL,
        console: Optional[Console] = None
    ):
        """
        Initialize Rich progress reporter.

        Args:
            verbosity: Verbosity level
            console: Optional Rich Console instance
        """
        self.verbosity = verbosity
        self.console = console or Console()

        # Tracking
        self.workflow_start_time: Optional[float] = None
        self.phase_start_times: Dict[str, float] = {}
        self.phases_completed: List[Dict[str, Any]] = []

    def start_workflow(self, description: str) -> None:
        """Start workflow with header."""
        self.workflow_start_time = time.time()

        if self.verbosity.value >= VerbosityLevel.MINIMAL.value:
            self.console.print()
            self.console.print(
                Panel.fit(
                    f"[bold cyan]{description}[/bold cyan]\n"
                    "[dim]CAAS - CrewAI Agent Auto-generation System[/dim]",
                    border_style="cyan",
                    box=box.DOUBLE
                )
            )
            self.console.print()

    def start_phase(
        self,
        phase_name: str,
        agent_name: str,
        description: str
    ) -> None:
        """Report phase start with Rich formatting."""
        self.phase_start_times[phase_name] = time.time()

        if self.verbosity.value >= VerbosityLevel.NORMAL.value:
            self.console.print(f"{'='*70}")
            self.console.print(
                f"[bold blue]🔄 Starting:[/bold blue] [cyan]{phase_name}[/cyan]"
            )
            self.console.print(f"[dim]Agent:[/dim] {agent_name}")
            self.console.print(f"[dim]Task:[/dim] {description}")
            self.console.print(f"{'='*70}\n")

    def update_phase_progress(
        self,
        phase_name: str,
        message: str,
        progress: Optional[float] = None
    ) -> None:
        """Update phase progress (optional)."""
        if self.verbosity.value >= VerbosityLevel.VERBOSE.value:
            progress_str = f" ({progress:.0%})" if progress is not None else ""
            self.console.print(f"  [dim]•[/dim] {message}{progress_str}")

    def complete_phase(
        self,
        phase_name: str,
        duration: float,
        success: bool
    ) -> None:
        """Report phase completion."""
        # Store result
        self.phases_completed.append({
            'phase_name': phase_name,
            'duration': duration,
            'success': success
        })

        if self.verbosity.value >= VerbosityLevel.MINIMAL.value:
            status_emoji = "✅" if success else "❌"
            status_text = "Completed" if success else "Failed"
            status_color = "green" if success else "red"

            self.console.print(
                f"[bold {status_color}]{status_emoji} {status_text}:[/bold {status_color}] "
                f"[cyan]{phase_name}[/cyan] "
                f"[dim]({duration:.1f}s)[/dim]"
            )
            self.console.print()

    def log_message(
        self,
        message: str,
        level: str = "info"
    ) -> None:
        """Log a message with appropriate styling."""
        if level == "debug" and self.verbosity.value < VerbosityLevel.DEBUG.value:
            return

        if level == "error":
            self.console.print(f"[bold red]❌ {message}[/bold red]")
        elif level == "warning":
            self.console.print(f"[yellow]⚠️  {message}[/yellow]")
        elif level == "success":
            self.console.print(f"[green]✅ {message}[/green]")
        elif level == "debug":
            self.console.print(f"[dim]🔍 {message}[/dim]")
        else:  # info
            if self.verbosity.value >= VerbosityLevel.NORMAL.value:
                self.console.print(f"[blue]ℹ️  {message}[/blue]")

    def log_validation(
        self,
        phase_name: str,
        passed: bool,
        issues: Optional[List[str]] = None
    ) -> None:
        """Log validation result."""
        if self.verbosity.value >= VerbosityLevel.VERBOSE.value:
            if passed:
                self.console.print(f"  [green]✓ Validation passed for {phase_name}[/green]")
            else:
                self.console.print(f"  [red]✗ Validation failed for {phase_name}[/red]")
                if issues:
                    for issue in issues[:5]:  # Show first 5
                        self.console.print(f"    [dim]• {issue}[/dim]")

    def log_feedback_iteration(
        self,
        phase_name: str,
        iteration: int,
        total_iterations: int
    ) -> None:
        """Log feedback loop iteration."""
        if self.verbosity.value >= VerbosityLevel.VERBOSE.value:
            self.console.print(
                f"  [yellow]🔄 Feedback iteration {iteration}/{total_iterations} "
                f"for {phase_name}[/yellow]"
            )

    def end_workflow(
        self,
        success: bool,
        duration: float,
        summary: Optional[Dict[str, Any]] = None
    ) -> None:
        """End workflow with summary table."""
        if self.verbosity.value >= VerbosityLevel.MINIMAL.value:
            # Summary table
            table = Table(
                title="[bold cyan]Workflow Summary[/bold cyan]",
                box=box.ROUNDED,
                show_header=True,
                header_style="bold magenta"
            )

            table.add_column("Phase", style="cyan")
            table.add_column("Status", justify="center")
            table.add_column("Duration", justify="right")

            for phase_info in self.phases_completed:
                status_emoji = "✅" if phase_info['success'] else "❌"
                status = f"{status_emoji} {'OK' if phase_info['success'] else 'Failed'}"

                table.add_row(
                    phase_info['phase_name'],
                    status,
                    f"{phase_info['duration']:.1f}s"
                )

            self.console.print()
            self.console.print(table)

            # Overall status
            completed_count = sum(1 for p in self.phases_completed if p['success'])
            total_count = len(self.phases_completed)

            status_text = (
                f"\n[bold]Total Duration:[/bold] {duration:.1f}s\n"
                f"[bold]Phases Completed:[/bold] "
                f"[{'green' if completed_count == total_count else 'yellow'}]"
                f"{completed_count}/{total_count}"
                f"[/{'green' if completed_count == total_count else 'yellow'}]"
            )

            if success:
                overall_status = "[bold green]✅ Workflow completed successfully![/bold green]"
            else:
                overall_status = "[bold red]❌ Workflow failed[/bold red]"

            self.console.print(
                Panel(
                    status_text + f"\n\n{overall_status}",
                    border_style="cyan",
                    box=box.ROUNDED
                )
            )
            self.console.print()


def create_rich_progress_reporter(
    verbosity: VerbosityLevel = VerbosityLevel.NORMAL
) -> RichProgressReporter:
    """
    Factory function to create Rich progress reporter.

    Args:
        verbosity: Verbosity level

    Returns:
        RichProgressReporter instance
    """
    return RichProgressReporter(verbosity=verbosity)
