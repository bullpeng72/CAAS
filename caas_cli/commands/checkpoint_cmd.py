"""
Checkpoint CLI Commands

CLI commands for human checkpoint workflow.

Part of CAAS-E Week 5 implementation (Task 5.3).
"""

import click
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from caas_framework.checkpoint.manager import CheckpointManager
from caas_framework.models.checkpoint import CheckpointPhase, ApprovalStatus

console = Console()


@click.group("checkpoint")
def checkpoint_group():
    """
    Human checkpoint workflow commands.

    Manage review checkpoints for CAAS-E methodology (7 checkpoints).
    """
    pass


@checkpoint_group.command("status")
@click.option(
    "--project",
    "-p",
    type=str,
    required=True,
    help="Project name",
)
@click.option(
    "--checkpoint-dir",
    type=click.Path(),
    default="./checkpoints",
    help="Checkpoint directory (default: ./checkpoints)",
)
def status_cmd(project: str, checkpoint_dir: str):
    """Show checkpoint status for project."""
    manager = CheckpointManager(project, checkpoint_dir=Path(checkpoint_dir))

    console.print(f"\n[bold cyan]Checkpoint Status: {project}[/bold cyan]\n")

    # Summary
    summary = manager.get_checkpoint_summary()

    summary_table = Table(title="Summary")
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", style="green")

    summary_table.add_row("Total Checkpoints", str(summary["total"]))
    summary_table.add_row("Approved", f"[green]{summary['approved']}[/green]")
    summary_table.add_row("Pending", f"[yellow]{summary['pending']}[/yellow]")
    summary_table.add_row("Rejected", f"[red]{summary['rejected']}[/red]")
    summary_table.add_row(
        "Completion Rate", f"{summary['completion_rate']*100:.1f}%"
    )

    console.print(summary_table)

    # Details
    if manager.session.checkpoints:
        console.print("\n[bold]Checkpoint Details:[/bold]\n")

        details_table = Table()
        details_table.add_column("ID", style="cyan")
        details_table.add_column("Phase", style="magenta")
        details_table.add_column("Status", justify="center")
        details_table.add_column("Reviewer")
        details_table.add_column("Score")

        for cp_id, result in manager.session.checkpoints.items():
            status_color = {
                ApprovalStatus.APPROVED: "green",
                ApprovalStatus.PENDING: "yellow",
                ApprovalStatus.REJECTED: "red",
                ApprovalStatus.CHANGES_REQUESTED: "yellow",
            }.get(result.status, "white")

            details_table.add_row(
                cp_id,
                result.phase.value,
                f"[{status_color}]{result.status.value}[/{status_color}]",
                result.reviewer or "-",
                f"{result.overall_score:.2f}" if result.overall_score else "-",
            )

        console.print(details_table)


@checkpoint_group.command("approve")
@click.option("--project", "-p", type=str, required=True, help="Project name")
@click.option(
    "--checkpoint-id", "-c", type=str, required=True, help="Checkpoint ID"
)
@click.option("--reviewer", "-r", type=str, required=True, help="Reviewer name")
@click.option(
    "--comment", "-m", type=str, multiple=True, help="Review comment (repeatable)"
)
@click.option(
    "--checkpoint-dir",
    type=click.Path(),
    default="./checkpoints",
    help="Checkpoint directory",
)
def approve_cmd(
    project: str, checkpoint_id: str, reviewer: str, comment: tuple, checkpoint_dir: str
):
    """Approve a checkpoint."""
    manager = CheckpointManager(project, checkpoint_dir=Path(checkpoint_dir))

    comments_list = list(comment) if comment else None

    try:
        result = manager.approve(checkpoint_id, reviewer, comments=comments_list)

        console.print(
            f"\n✅ [bold green]Checkpoint Approved![/bold green]"
            f"\n  Checkpoint: {checkpoint_id}"
            f"\n  Reviewer: {reviewer}"
            f"\n  Status: {result.status.value}\n"
        )

    except ValueError as e:
        console.print(f"\n❌ [bold red]Error:[/bold red] {e}\n")
        raise click.Abort()


@checkpoint_group.command("reject")
@click.option("--project", "-p", type=str, required=True, help="Project name")
@click.option(
    "--checkpoint-id", "-c", type=str, required=True, help="Checkpoint ID"
)
@click.option("--reviewer", "-r", type=str, required=True, help="Reviewer name")
@click.option(
    "--change",
    type=str,
    multiple=True,
    required=True,
    help="Required change (repeatable)",
)
@click.option(
    "--comment", "-m", type=str, multiple=True, help="Review comment (repeatable)"
)
@click.option(
    "--checkpoint-dir",
    type=click.Path(),
    default="./checkpoints",
    help="Checkpoint directory",
)
def reject_cmd(
    project: str,
    checkpoint_id: str,
    reviewer: str,
    change: tuple,
    comment: tuple,
    checkpoint_dir: str,
):
    """Reject a checkpoint and request changes."""
    manager = CheckpointManager(project, checkpoint_dir=Path(checkpoint_dir))

    required_changes = list(change)
    comments_list = list(comment) if comment else None

    try:
        result = manager.reject(checkpoint_id, reviewer, required_changes, comments_list)

        console.print(
            f"\n⚠️ [bold yellow]Checkpoint Rejected[/bold yellow]"
            f"\n  Checkpoint: {checkpoint_id}"
            f"\n  Reviewer: {reviewer}"
            f"\n  Status: {result.status.value}"
            f"\n  Required Changes: {len(required_changes)}\n"
        )

        for i, change_item in enumerate(required_changes, 1):
            console.print(f"  {i}. {change_item}")

        console.print()

    except ValueError as e:
        console.print(f"\n❌ [bold red]Error:[/bold red] {e}\n")
        raise click.Abort()


@checkpoint_group.command("list")
def list_checkpoints_cmd():
    """List all 7 CAAS-E checkpoints."""
    from caas_framework.models.checkpoint import SEVEN_CHECKPOINTS

    console.print("\n[bold cyan]CAAS-E 7 Checkpoints[/bold cyan]\n")

    table = Table()
    table.add_column("ID", style="cyan")
    table.add_column("Phase", style="magenta")
    table.add_column("Name", style="green")
    table.add_column("Criteria", justify="center")
    table.add_column("Auto-Approve", justify="center")

    for cp in SEVEN_CHECKPOINTS:
        table.add_row(
            cp.id,
            cp.phase.value,
            cp.name,
            str(len(cp.criteria)),
            f"{cp.auto_approve_threshold:.1f}" if cp.auto_approve_threshold else "-",
        )

    console.print(table)
    console.print()
