"""
Progress Tracker with Rich Console

Provides visual progress indication for CAAS phase execution.
Uses rich library for beautiful console output.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from rich import box
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import Progress
from rich.table import Table
from rich.text import Text

from caas_framework.agents.base import AgentPhase

logger = logging.getLogger(__name__)


@dataclass
class PhaseProgress:
    """Progress tracking for a single phase"""

    phase: AgentPhase
    phase_name: str
    agent_name: str
    description: str
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    status: str = "pending"  # pending, in_progress, completed, failed
    details: List[str] = field(default_factory=list)

    @property
    def duration(self) -> Optional[float]:
        """Get phase duration in seconds"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        elif self.start_time:
            return time.time() - self.start_time
        return None

    @property
    def status_emoji(self) -> str:
        """Get emoji for current status"""
        return {"pending": "⏳", "in_progress": "🔄", "completed": "✅", "failed": "❌"}.get(
            self.status, "❓"
        )


class ProgressTracker:
    """
    Visual Progress Tracker for CAAS

    Displays real-time progress of multi-phase agent execution
    with rich console formatting.
    """

    def __init__(
        self, total_phases: int = 6, show_details: bool = True, console: Optional[Console] = None
    ):
        """
        Initialize progress tracker.

        Args:
            total_phases: Total number of phases to track
            show_details: Whether to show detailed phase information
            console: Optional rich Console instance
        """
        self.total_phases = total_phases
        self.show_details = show_details
        self.console = console or Console()

        self.phases: List[PhaseProgress] = []
        self.current_phase_index: int = 0
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None

        # Rich progress instance
        self.progress: Optional[Progress] = None
        self.task_ids: Dict[str, int] = {}

    def start_tracking(self):
        """Start progress tracking"""
        self.start_time = time.time()
        logger.info("ProgressTracker started")

        # Display header
        self._display_header()

    def add_phase(
        self, phase: AgentPhase, phase_name: str, agent_name: str, description: str
    ) -> PhaseProgress:
        """
        Add a new phase to track.

        Args:
            phase: AgentPhase enum
            phase_name: Display name for the phase
            agent_name: Name of the agent executing this phase
            description: Short description of what this phase does

        Returns:
            PhaseProgress instance
        """
        phase_progress = PhaseProgress(
            phase=phase, phase_name=phase_name, agent_name=agent_name, description=description
        )
        self.phases.append(phase_progress)
        return phase_progress

    def start_phase(
        self, phase_name: str, agent_name: Optional[str] = None, description: Optional[str] = None
    ):
        """
        Mark a phase as started.

        Args:
            phase_name: Name of the phase
            agent_name: Agent executing the phase
            description: Phase description
        """
        # Find phase
        phase_progress = next((p for p in self.phases if p.phase_name == phase_name), None)

        if not phase_progress:
            # Auto-create if not exists
            phase_progress = PhaseProgress(
                phase=AgentPhase.DISCOVERY,  # Default
                phase_name=phase_name,
                agent_name=agent_name or "Agent",
                description=description or "Processing...",
            )
            self.phases.append(phase_progress)

        # Update status
        phase_progress.status = "in_progress"
        phase_progress.start_time = time.time()

        # Display progress
        self._display_phase_start(phase_progress)

    def complete_phase(
        self,
        phase_name: str,
        duration: Optional[float] = None,
        success: bool = True,
        details: Optional[List[str]] = None,
    ):
        """
        Mark a phase as completed.

        Args:
            phase_name: Name of the phase
            duration: Optional duration override
            success: Whether phase succeeded
            details: Optional detail messages
        """
        # Find phase
        phase_progress = next((p for p in self.phases if p.phase_name == phase_name), None)

        if not phase_progress:
            logger.warning(f"Phase '{phase_name}' not found in tracker")
            return

        # Update status
        phase_progress.status = "completed" if success else "failed"
        phase_progress.end_time = time.time()

        if duration is not None:
            # Override calculated duration
            phase_progress.end_time = phase_progress.start_time + duration

        if details:
            phase_progress.details.extend(details)

        # Display progress
        self._display_phase_complete(phase_progress)

    def end_tracking(self):
        """End progress tracking and display summary"""
        self.end_time = time.time()

        # Display summary
        self._display_summary()

        logger.info("ProgressTracker ended")

    def _display_header(self):
        """Display initial header"""
        self.console.print()
        self.console.print(
            Panel.fit(
                "[bold cyan]CAAS - CrewAI Agent Auto-generation System[/bold cyan]\n"
                "[dim]Multi-Agent Code Generation in Progress...[/dim]",
                border_style="cyan",
                box=box.DOUBLE,
            )
        )
        self.console.print()

    def _display_phase_start(self, phase: PhaseProgress):
        """Display phase start notification"""
        self.console.print(f"\n{'='*70}")
        self.console.print(
            f"[bold blue]{phase.status_emoji} Starting:[/bold blue] "
            f"[cyan]{phase.phase_name}[/cyan]",
            style="bold",
        )
        self.console.print(f"[dim]Agent:[/dim] {phase.agent_name}")
        self.console.print(f"[dim]Task:[/dim] {phase.description}")
        self.console.print(f"{'='*70}\n")

    def _display_phase_complete(self, phase: PhaseProgress):
        """Display phase completion notification"""
        duration_str = f"{phase.duration:.2f}s" if phase.duration else "N/A"

        status_style = "green" if phase.status == "completed" else "red"

        self.console.print()
        self.console.print(
            f"[bold {status_style}]{phase.status_emoji} {phase.status.title()}:[/bold {status_style}] "
            f"[cyan]{phase.phase_name}[/cyan] "
            f"[dim]({duration_str})[/dim]"
        )

        # Show details if any
        if self.show_details and phase.details:
            for detail in phase.details:
                self.console.print(f"  [dim]•[/dim] {detail}")

        self.console.print()

    def _display_summary(self):
        """Display final summary table"""
        total_duration = self.end_time - self.start_time if self.start_time and self.end_time else 0

        # Create summary table
        table = Table(
            title="[bold cyan]Execution Summary[/bold cyan]",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold magenta",
        )

        table.add_column("Phase", style="cyan", no_wrap=True)
        table.add_column("Agent", style="blue")
        table.add_column("Status", justify="center")
        table.add_column("Duration", justify="right")

        completed_count = 0
        failed_count = 0

        for phase in self.phases:
            status_text = Text(phase.status_emoji + " " + phase.status.title())
            if phase.status == "completed":
                status_text.stylize("green")
                completed_count += 1
            elif phase.status == "failed":
                status_text.stylize("red")
                failed_count += 1
            elif phase.status == "in_progress":
                status_text.stylize("yellow")
            else:
                status_text.stylize("dim")

            duration_str = f"{phase.duration:.2f}s" if phase.duration else "N/A"

            table.add_row(phase.phase_name, phase.agent_name, status_text, duration_str)

        self.console.print()
        self.console.print(table)

        # Summary stats
        stats_text = (
            f"\n[bold]Total Duration:[/bold] {total_duration:.2f}s\n"
            f"[bold]Phases Completed:[/bold] [green]{completed_count}/{len(self.phases)}[/green]"
        )

        if failed_count > 0:
            stats_text += f"\n[bold]Phases Failed:[/bold] [red]{failed_count}[/red]"

        self.console.print(Panel(stats_text, border_style="cyan", box=box.ROUNDED))
        self.console.print()

    def get_current_progress(self) -> Dict[str, Any]:
        """
        Get current progress statistics.

        Returns:
            Dictionary with progress metrics
        """
        completed = sum(1 for p in self.phases if p.status == "completed")
        failed = sum(1 for p in self.phases if p.status == "failed")
        in_progress = sum(1 for p in self.phases if p.status == "in_progress")

        total_duration = 0
        for phase in self.phases:
            if phase.duration:
                total_duration += phase.duration

        return {
            "total_phases": len(self.phases),
            "completed": completed,
            "failed": failed,
            "in_progress": in_progress,
            "pending": len(self.phases) - completed - failed - in_progress,
            "completion_rate": completed / len(self.phases) if self.phases else 0,
            "total_duration": total_duration,
            "average_phase_duration": total_duration / completed if completed > 0 else 0,
        }


class SpinnerProgressTracker(ProgressTracker):
    """
    Progress tracker with spinner-based UI.

    Shows a spinner for each phase with live updates.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.live: Optional[Live] = None

    def start_tracking(self):
        """Start tracking with live display"""
        super().start_tracking()

        # Start live display
        self.live = Live(self._generate_live_display(), console=self.console, refresh_per_second=4)
        self.live.start()

    def _generate_live_display(self) -> Table:
        """Generate live display table"""
        table = Table(
            title="[bold cyan]Phase Progress[/bold cyan]",
            box=box.SIMPLE,
            show_header=True,
            header_style="bold magenta",
        )

        table.add_column("Status", justify="center", width=4)
        table.add_column("Phase", style="cyan")
        table.add_column("Agent", style="blue")
        table.add_column("Duration", justify="right")

        for phase in self.phases:
            duration_str = f"{phase.duration:.1f}s" if phase.duration else "-"

            table.add_row(phase.status_emoji, phase.phase_name, phase.agent_name, duration_str)

        return table

    def start_phase(self, *args, **kwargs):
        """Start phase and update live display"""
        super().start_phase(*args, **kwargs)

        if self.live:
            self.live.update(self._generate_live_display())

    def complete_phase(self, *args, **kwargs):
        """Complete phase and update live display"""
        super().complete_phase(*args, **kwargs)

        if self.live:
            self.live.update(self._generate_live_display())

    def end_tracking(self):
        """End tracking and stop live display"""
        if self.live:
            self.live.stop()

        super().end_tracking()


def create_progress_tracker(
    total_phases: int = 6, show_details: bool = True, use_spinner: bool = False
) -> ProgressTracker:
    """
    Factory function to create a progress tracker.

    Args:
        total_phases: Total number of phases
        show_details: Whether to show detailed information
        use_spinner: Use spinner-based live display

    Returns:
        ProgressTracker instance
    """
    if use_spinner:
        return SpinnerProgressTracker(total_phases=total_phases, show_details=show_details)
    else:
        return ProgressTracker(total_phases=total_phases, show_details=show_details)
