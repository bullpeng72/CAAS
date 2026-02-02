"""
List Command

List projects.
"""

import click
from caas_cli.config import get_config
from caas_cli.utils import echo_error, print_table
from caas_sdk import CAAS
from caas_sdk.exceptions import CAASError


@click.command("list")
@click.option(
    "--limit", "-n", type=int, default=10, help="Number of projects to show (default: 10)"
)
@click.option("--status", type=str, help="Filter by status: generating, completed, failed")
@click.option("--api-key", type=str, envvar="CAAS_API_KEY", help="API key for authentication")
@click.option("--api-url", type=str, help="API URL (overrides config)")
def list_cmd(limit, status, api_key, api_url):
    """
    \b
    List all projects with their current status

    \b
    📋 DISPLAYED INFORMATION:
    ═══════════════════════════════════════════════════════════════════════════
    • Project ID (unique identifier)
    • Requirement (truncated preview)
    • Status with emoji:
      ⏳ generating - In progress
      ✅ completed - Ready to download
      ❌ failed - Error occurred
      ⏸️  paused - Paused (if supported)
    • Progress percentage (0-100%)
    • Created date (YYYY-MM-DD)

    \b
    💡 USAGE EXAMPLES:
    ═══════════════════════════════════════════════════════════════════════════

    \b
    1️⃣  List recent 10 projects (default):
       $ caas list

    \b
    2️⃣  List more projects:
       $ caas list --limit 20
       $ caas list -n 50

    \b
    3️⃣  Filter by status:
       $ caas list --status completed
       $ caas list --status generating
       $ caas list --status failed

    \b
    4️⃣  Completed projects only, show 20:
       $ caas list --status completed --limit 20

    \b
    5️⃣  With API authentication:
       $ caas list \\
           --api-key your_key \\
           --api-url https://api.example.com

    \b
    🔍 COMMON WORKFLOWS:
    ═══════════════════════════════════════════════════════════════════════════

    \b
    1️⃣  Find recent completed projects to download:
       $ caas list --status completed
       $ caas download <project-id>

    \b
    2️⃣  Check for failed projects to retry:
       $ caas list --status failed
       # Review error and regenerate with fixes

    \b
    3️⃣  Monitor in-progress generations:
       $ caas list --status generating
       $ caas status <project-id> --watch

    \b
    📊 STATUS FILTERS:
    ═══════════════════════════════════════════════════════════════════════════
    • generating: Projects currently being generated
    • completed: Successfully generated, ready to download
    • failed: Generation failed, check error details
    • (no filter): Show all projects regardless of status

    \b
    💾 STORAGE:
    ═══════════════════════════════════════════════════════════════════════════
    • Projects are stored in API server database
    • Use 'caas download' to save code locally
    • Completed projects remain accessible for download

    \b
    📚 See also:
       caas status --help      (Check specific project status)
       caas download --help    (Download project code)
       caas generate --help    (Create new project)
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

    try:
        # List projects via API
        projects = client.list_projects(status=status, limit=limit)

        if not projects:
            click.echo("No projects found.")
            return

        # Display header
        click.echo(
            """
╔══════════════════════════════════════════════════════════════╗
║                     Project List                             ║
╚══════════════════════════════════════════════════════════════╝
"""
        )

        # Prepare table data
        headers = ["ID", "Requirement", "Status", "Progress", "Created"]
        rows = []

        for project in projects:
            project_id = project.get("project_id", "N/A")[:12]  # Truncate
            requirement = project.get("requirement", "")[:30]  # Truncate
            if len(project.get("requirement", "")) > 30:
                requirement += "..."

            status_val = project.get("status", "unknown")
            progress = f"{project.get('progress', 0)*100:.0f}%"
            created = project.get("created_at", "")[:10]  # Date only

            # Status emoji
            status_emoji = {
                "generating": "⏳",
                "completed": "✅",
                "failed": "❌",
                "paused": "⏸️",
            }.get(status_val, "❓")

            rows.append(
                [project_id, requirement, f"{status_emoji} {status_val}", progress, created]
            )

        # Print table
        print_table(headers, rows)

        click.echo()
        click.echo(f"Total: {len(projects)} project(s)")

        if status:
            click.echo(f"Filter: status={status}")

    except CAASError as e:
        echo_error(f"Error: {e}")
