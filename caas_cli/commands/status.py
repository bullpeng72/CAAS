"""
Status Command

Check project status.
"""

import time

import click

from caas_cli.config import get_config
from caas_cli.utils import echo_error, echo_info, echo_progress, echo_success
from caas_sdk import CAAS
from caas_sdk.exceptions import CAASError


@click.command()
@click.argument("project_id")
@click.option(
    "--watch",
    "-w",
    is_flag=True,
    help="Watch status updates in real-time (auto-refresh)",
)
@click.option(
    "--interval",
    "-i",
    type=int,
    default=2,
    help="Watch interval in seconds (default: 2)",
)
@click.option(
    "--api-key", type=str, envvar="CAAS_API_KEY", help="API key for authentication"
)
@click.option("--api-url", type=str, help="API URL (overrides config)")
def status(project_id, watch, interval, api_key, api_url):
    """
    \b
    Check real-time project generation status

    \b
    📊 STATUS INFORMATION:
    ═══════════════════════════════════════════════════════════════════════════
    • Project ID & status (generating, completed, failed)
    • Current BMAD phase (Phase 0-4)
    • Progress percentage (0-100%)
    • Current step description
    • Estimated time remaining
    • Error messages (if failed)
    • Created/completed timestamps

    \b
    🔄 BMAD PHASES TRACKED:
    ═══════════════════════════════════════════════════════════════════════════
    Phase 0: Requirements Analysis  (5-10%)
    Phase 1: Modeling               (10-30%)
    Phase 2: Architecture           (30-50%)
    Phase 3: Development            (50-90%)
    Phase 4: Deployment             (90-100%)

    \b
    💡 USAGE EXAMPLES:
    ═══════════════════════════════════════════════════════════════════════════

    \b
    1️⃣  Check status once:
       $ caas status abc123

    \b
    2️⃣  Watch in real-time (recommended):
       $ caas status abc123 --watch

    \b
    3️⃣  Custom refresh interval:
       $ caas status abc123 --watch --interval 5

    \b
    4️⃣  With API authentication:
       $ caas status abc123 --api-key your_key --api-url https://api.example.com

    \b
    ⌨️  WATCH MODE CONTROLS:
    ═══════════════════════════════════════════════════════════════════════════
    • Ctrl+C: Stop watching and exit
    • Auto-exits when generation completes or fails

    \b
    📋 STATUS VALUES:
    ═══════════════════════════════════════════════════════════════════════════
    • generating: In progress (use --watch to monitor)
    • completed: Success (ready to download)
    • failed: Error occurred (check error message)

    \b
    📚 See also:
       caas download --help    (Download completed project)
       caas list --help        (List all projects)
    """
    # Load config
    config = get_config()
    api_key = api_key or config.get("api_key")
    api_url = api_url or config.get("api_url", "http://localhost:8000")

    # Create client
    try:
        client = CAAS(api_key=api_key, base_url=api_url)
    except Exception as e:
        echo_error(f"Failed to create client: {e}")
        return

    def display_status():
        """Display project status"""
        try:
            project = client.get_project(project_id)

            click.echo(f"\n{'='*60}")
            click.echo(f"Project: {project.project_id}")
            click.echo(f"{'='*60}")
            click.echo(f"Status:       {project.status}")
            click.echo(f"Progress:     {project.progress*100:.1f}%")

            if project.current_phase:
                click.echo(f"Phase:        {project.current_phase}")

            if project.created_at:
                click.echo(f"Created:      {project.created_at}")

            if project.updated_at:
                click.echo(f"Updated:      {project.updated_at}")

            if project.domain:
                click.echo(f"Domain:       {project.domain}")

            if project.error_message:
                click.echo()
                echo_error(f"Error: {project.error_message}")

            # Status indicator
            click.echo()
            if project.status == "completed":
                echo_success("✅ Generation completed!")
            elif project.status == "failed":
                echo_error("❌ Generation failed")
            elif project.status == "generating":
                echo_progress("⏳ Generating...")
            else:
                echo_info(f"Status: {project.status}")

            return project.status

        except CAASError as e:
            echo_error(f"Error: {e}")
            return None

    if watch:
        # Watch mode
        echo_info("Watching status (press Ctrl+C to stop)...")

        try:
            while True:
                status_value = display_status()

                if status_value in ["completed", "failed"]:
                    break

                time.sleep(interval)

        except KeyboardInterrupt:
            echo_info("\nStopped watching")

    else:
        # Single check
        display_status()
