"""
Session Command

Manage workflow sessions
"""

import click

from caas_cli.utils import (
    echo_error,
    echo_info,
    echo_success,
    get_or_create_session_manager,
    handle_keyboard_interrupt,
    print_table,
)


@click.group()
def session():
    """Manage workflow sessions"""
    pass


@session.command()
@click.option("--name", "-n", required=True, help="Session name")
@click.option("--description", "-d", type=str, help="Session description")
@handle_keyboard_interrupt
def create(name, description):
    """
    Create new session

    \b
    USAGE EXAMPLES:
    ═══════════════════════════════════════════════════════════════════════════

    \b
    1️⃣  Create simple session:
       $ caas session create --name "project-alpha"

    \b
    2️⃣  Create with description:
       $ caas session create --name "e-commerce" \\
           --description "E-commerce platform development"
    """
    try:
        manager = get_or_create_session_manager()

        new_session = manager.create_session(
            name=name, metadata={"description": description} if description else None
        )

        echo_success(f"Session created: {new_session.session_id}")
        echo_info(f"Name: {name}")
        if description:
            echo_info(f"Description: {description}")

    except Exception as e:
        echo_error(f"Failed to create session: {e}")
        return 1


@session.command(name="list")
@click.option("--active-only", is_flag=True, help="Show only active sessions")
@handle_keyboard_interrupt
def list_sessions(active_only):
    """
    List all sessions

    \b
    USAGE:
       $ caas session list
       $ caas session list --active-only
    """
    try:
        manager = get_or_create_session_manager()
        sessions = manager.list_sessions()

        if active_only:
            sessions = [s for s in sessions if s.status == "active"]

        if not sessions:
            echo_info("No sessions found")
            return

        # Prepare table data
        headers = ["ID", "Name", "Status", "Created", "Phase"]
        rows = []

        for sess in sessions:
            session_id = sess.session_id[:8] + "..."
            name = sess.metadata.get("name", "N/A") if sess.metadata else "N/A"
            status = sess.status
            created = sess.created_at.strftime("%Y-%m-%d %H:%M")
            phase = sess.metadata.get("current_phase", "N/A") if sess.metadata else "N/A"

            rows.append([session_id, name, status, created, phase])

        print_table(headers, rows)
        echo_info(f"Total sessions: {len(sessions)}")

    except Exception as e:
        echo_error(f"Failed to list sessions: {e}")
        return 1


@session.command()
@click.argument("session_id")
@handle_keyboard_interrupt
def switch(session_id):
    """
    Switch active session

    \b
    USAGE:
       $ caas session switch abc123def456
    """
    try:
        manager = get_or_create_session_manager()

        manager.switch_to(session_id)

        echo_success(f"Switched to session: {session_id}")

    except Exception as e:
        echo_error(f"Failed to switch session: {e}")
        return 1


@session.command()
@click.argument("session_id")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed session info")
@handle_keyboard_interrupt
def show(session_id, verbose):
    """
    Show session details

    \b
    USAGE:
       $ caas session show abc123def456
       $ caas session show abc123def456 --verbose
    """
    try:
        manager = get_or_create_session_manager()

        sess = manager.get_session(session_id)

        if not sess:
            echo_error(f"Session not found: {session_id}")
            return 1

        # Show basic info
        click.echo(click.style("Session Details:", bold=True))
        click.echo(f"  ID:       {sess.session_id}")
        click.echo(f"  Status:   {sess.status}")
        click.echo(f"  Created:  {sess.created_at}")

        if sess.metadata:
            click.echo(f"  Name:     {sess.metadata.get('name', 'N/A')}")
            if "description" in sess.metadata:
                click.echo(f"  Description: {sess.metadata['description']}")

        # Show verbose info
        if verbose and sess.metadata:
            click.echo()
            click.echo(click.style("Metadata:", bold=True))
            for key, value in sess.metadata.items():
                click.echo(f"  {key}: {value}")

    except Exception as e:
        echo_error(f"Failed to show session: {e}")
        return 1


@session.command()
@click.argument("session_id")
@click.option("--force", "-f", is_flag=True, help="Force delete without confirmation")
@handle_keyboard_interrupt
def delete(session_id, force):
    """
    Delete session

    \b
    USAGE:
       $ caas session delete abc123def456
       $ caas session delete abc123def456 --force
    """
    try:
        manager = get_or_create_session_manager()

        # Confirm deletion
        if not force:
            if not click.confirm(f"Delete session {session_id}?"):
                echo_info("Cancelled")
                return

        manager.delete_session(session_id)

        echo_success(f"Session deleted: {session_id}")

    except Exception as e:
        echo_error(f"Failed to delete session: {e}")
        return 1


@session.command()
@click.argument("session_id")
@handle_keyboard_interrupt
def pause(session_id):
    """
    Pause session

    \b
    USAGE:
       $ caas session pause abc123def456
    """
    try:
        manager = get_or_create_session_manager()

        manager.pause_session(session_id)

        echo_success(f"Session paused: {session_id}")

    except Exception as e:
        echo_error(f"Failed to pause session: {e}")
        return 1


@session.command()
@click.argument("session_id")
@handle_keyboard_interrupt
def resume(session_id):
    """
    Resume paused session

    \b
    USAGE:
       $ caas session resume abc123def456
    """
    try:
        manager = get_or_create_session_manager()

        manager.resume_session(session_id)

        echo_success(f"Session resumed: {session_id}")

    except Exception as e:
        echo_error(f"Failed to resume session: {e}")
        return 1
