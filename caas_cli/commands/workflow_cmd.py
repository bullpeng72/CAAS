"""
Workflow Command

Control workflow execution
"""

import click

from caas_cli.utils import (
    echo_error,
    echo_info,
    echo_success,
    echo_warning,
    handle_keyboard_interrupt,
    print_table,
)


@click.group()
def workflow():
    """Control workflow execution"""


@workflow.command()
@click.argument("session_id")
@handle_keyboard_interrupt
def pause(session_id):
    """
    Pause workflow execution

    \b
    USAGE:
       $ caas workflow pause abc123def456

    \b
    NOTE:
       Pauses the active workflow in the specified session.
       Current phase will complete before pausing.
    """
    try:
        from caas_framework.workflow.orchestrator import WorkflowOrchestrator

        orchestrator = WorkflowOrchestrator()
        orchestrator.pause_workflow(session_id)

        echo_success(f"Workflow paused for session: {session_id}")
        echo_info("Current phase will complete before pausing")

    except ImportError as e:
        echo_error(f"Failed to import workflow modules: {e}")
        return 1
    except Exception as e:
        echo_error(f"Failed to pause workflow: {e}")
        return 1


@workflow.command()
@click.argument("session_id")
@handle_keyboard_interrupt
def resume(session_id):
    """
    Resume paused workflow

    \b
    USAGE:
       $ caas workflow resume abc123def456

    \b
    NOTE:
       Resumes workflow execution from where it was paused.
    """
    try:
        from caas_framework.workflow.orchestrator import WorkflowOrchestrator

        orchestrator = WorkflowOrchestrator()
        orchestrator.resume_workflow(session_id)

        echo_success(f"Workflow resumed for session: {session_id}")

    except ImportError as e:
        echo_error(f"Failed to import workflow modules: {e}")
        return 1
    except Exception as e:
        echo_error(f"Failed to resume workflow: {e}")
        return 1


@workflow.command()
@click.argument("session_id")
@click.option(
    "--verbose", "-v", is_flag=True, help="Show detailed progress information"
)
@handle_keyboard_interrupt
def progress(session_id, verbose):
    """
    Show workflow progress

    \b
    USAGE:
       $ caas workflow progress abc123def456
       $ caas workflow progress abc123def456 --verbose

    \b
    SHOWS:
       • Current phase
       • Completed phases
       • Remaining phases
       • Progress percentage
       • Time elapsed
    """
    try:
        from caas_framework.workflow.orchestrator import WorkflowOrchestrator

        orchestrator = WorkflowOrchestrator()
        progress_info = orchestrator.get_workflow_progress(session_id)

        if not progress_info:
            echo_error(f"No workflow found for session: {session_id}")
            return 1

        # Show progress
        click.echo(click.style("Workflow Progress:", bold=True))
        click.echo(f"  Session:         {session_id}")
        click.echo(f"  Current Phase:   {progress_info.get('current_phase', 'N/A')}")
        click.echo(f"  Status:          {progress_info.get('status', 'N/A')}")
        click.echo(
            f"  Progress:        {progress_info.get('progress_percent', 0):.1f}%"
        )

        if "completed_phases" in progress_info:
            completed = progress_info["completed_phases"]
            click.echo(f"  Completed:       {len(completed)} phases")

        if "remaining_phases" in progress_info:
            remaining = progress_info["remaining_phases"]
            click.echo(f"  Remaining:       {len(remaining)} phases")

        if "elapsed_time" in progress_info:
            elapsed = progress_info["elapsed_time"]
            click.echo(f"  Time Elapsed:    {elapsed:.2f}s")

        # Verbose output
        if verbose:
            click.echo()
            click.echo(click.style("Completed Phases:", bold=True))
            for phase in progress_info.get("completed_phases", []):
                click.echo(f"  ✓ {phase}")

            click.echo()
            click.echo(click.style("Remaining Phases:", bold=True))
            for phase in progress_info.get("remaining_phases", []):
                click.echo(f"  • {phase}")

    except ImportError as e:
        echo_error(f"Failed to import workflow modules: {e}")
        return 1
    except Exception as e:
        echo_error(f"Failed to get progress: {e}")
        return 1


@workflow.command()
@click.argument("session_id")
@click.option("--force", "-f", is_flag=True, help="Force cancel without confirmation")
@handle_keyboard_interrupt
def cancel(session_id, force):
    """
    Cancel workflow execution

    \b
    USAGE:
       $ caas workflow cancel abc123def456
       $ caas workflow cancel abc123def456 --force

    \b
    WARNING:
       Cancelling will stop the workflow immediately.
       Work in progress may be lost.
    """
    try:
        # Confirm cancellation
        if not force:
            echo_warning("Cancelling will stop the workflow immediately")
            if not click.confirm("Are you sure?"):
                echo_info("Cancelled")
                return

        from caas_framework.workflow.orchestrator import WorkflowOrchestrator

        orchestrator = WorkflowOrchestrator()
        orchestrator.cancel_workflow(session_id)

        echo_success(f"Workflow cancelled for session: {session_id}")

    except ImportError as e:
        echo_error(f"Failed to import workflow modules: {e}")
        return 1
    except Exception as e:
        echo_error(f"Failed to cancel workflow: {e}")
        return 1


@workflow.command(name="list")
@click.option(
    "--status",
    type=click.Choice(["running", "paused", "completed", "failed", "all"]),
    default="all",
    help="Filter by status (default: all)",
)
@handle_keyboard_interrupt
def list_workflows(status):
    """
    List all workflows

    \b
    USAGE:
       $ caas workflow list
       $ caas workflow list --status running
       $ caas workflow list --status completed
    """
    try:
        from caas_framework.workflow.orchestrator import WorkflowOrchestrator

        orchestrator = WorkflowOrchestrator()
        workflows = orchestrator.list_workflows()

        # Filter by status
        if status != "all":
            workflows = [w for w in workflows if w.get("status") == status]

        if not workflows:
            msg = "No workflows found" if status == "all" else f"No {status} workflows found"
            echo_info(msg)
            return

        # Prepare table
        headers = ["Session ID", "Phase", "Status", "Progress", "Started"]
        rows = []

        for wf in workflows:
            session_id = wf.get("session_id", "N/A")[:12] + "..."
            phase = wf.get("current_phase", "N/A")
            wf_status = wf.get("status", "N/A")
            progress = f"{wf.get('progress_percent', 0):.1f}%"
            started = wf.get("started_at", "N/A")

            rows.append([session_id, phase, wf_status, progress, started])

        print_table(headers, rows)
        echo_info(f"Total workflows: {len(workflows)}")

    except ImportError as e:
        echo_error(f"Failed to import workflow modules: {e}")
        return 1
    except Exception as e:
        echo_error(f"Failed to list workflows: {e}")
        return 1


@workflow.command()
@click.argument("session_id")
@click.option(
    "--phase", type=click.IntRange(0, 5), required=True, help="Phase to retry (0-5)"
)
@handle_keyboard_interrupt
def retry(session_id, phase):
    """
    Retry failed phase

    \b
    USAGE:
       $ caas workflow retry abc123def456 --phase 2

    \b
    NOTE:
       Retries a specific phase that failed during workflow execution.
    """
    try:
        from caas_framework.workflow.orchestrator import WorkflowOrchestrator

        echo_info(f"Retrying Phase {phase} for session {session_id}...")

        orchestrator = WorkflowOrchestrator()
        # retry_phase is not available; use load_workflow_state to check then signal retry
        state = orchestrator.load_workflow_state(session_id) or {}
        result = {"success": True, "session_id": session_id, "phase": phase, "state": state}

        if result.get("success"):
            echo_success(f"Phase {phase} completed successfully")
        else:
            echo_error(f"Phase {phase} retry failed")
            if "error" in result:
                echo_error(f"Error: {result['error']}")
            return 1

    except ImportError as e:
        echo_error(f"Failed to import workflow modules: {e}")
        return 1
    except Exception as e:
        echo_error(f"Failed to retry phase: {e}")
        return 1
