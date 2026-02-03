"""
Download Command

Download generated code.
"""

from pathlib import Path

import click

from caas_cli.config import get_config
from caas_cli.utils import echo_error, echo_progress, echo_success
from caas_sdk import CAAS
from caas_sdk.exceptions import CAASError


@click.command()
@click.argument("project_id")
@click.argument("output_dir", type=click.Path(), default="./generated")
@click.option("--api-key", type=str, envvar="CAAS_API_KEY", help="API key for authentication")
@click.option("--api-url", type=str, help="API URL (overrides config)")
@click.option("--force", "-f", is_flag=True, help="Overwrite existing files without confirmation")
def download(project_id, output_dir, api_key, api_url, force):
    """
    \b
    Download generated code & artifacts from completed project

    \b
    📦 DOWNLOADED ARTIFACTS:
    ═══════════════════════════════════════════════════════════════════════════
    Source Code:
      • src/agents.py          - CrewAI agent definitions
      • src/tasks.py           - CrewAI task definitions
      • src/crew.py            - Crew configuration
      • src/tools.py           - Custom tool implementations
      • src/api.py             - FastAPI endpoints (if CRUD strategy)
      • src/database.py        - Database models (if CRUD strategy)
      • main.py                - Application entry point

    Configuration:
      • requirements.txt       - Python dependencies
      • .env.example           - Environment variables template
      • pyproject.toml         - Project metadata

    Deployment:
      • Dockerfile             - Container definition
      • docker-compose.yml     - Multi-service orchestration
      • kubernetes/            - K8s manifests (if deployment=kubernetes)

    Documentation:
      • README.md              - Project documentation
      • golden_data.json       - Structured requirements (Phase 0)
      • agents.json            - Agent specifications (Phase 1)
      • tasks.json             - Task specifications (Phase 1)
      • architecture.json      - Architecture design (Phase 2)

    Tests:
      • tests/                 - Unit & integration tests
      • pytest.ini             - Test configuration

    \b
    💡 USAGE EXAMPLES:
    ═══════════════════════════════════════════════════════════════════════════

    \b
    1️⃣  Download to default directory (./generated):
       $ caas download abc123

    \b
    2️⃣  Download to specific directory:
       $ caas download abc123 ./my-project

    \b
    3️⃣  Force overwrite existing files:
       $ caas download abc123 ./output --force

    \b
    4️⃣  With API authentication:
       $ caas download abc123 ./project \\
           --api-key your_key \\
           --api-url https://api.example.com

    \b
    🚀 NEXT STEPS AFTER DOWNLOAD:
    ═══════════════════════════════════════════════════════════════════════════

    \b
    1️⃣  Navigate to project:
       $ cd ./my-project

    \b
    2️⃣  Set up environment:
       $ cp .env.example .env
       $ vim .env  # Add your OPENAI_API_KEY

    \b
    3️⃣  Install dependencies:
       $ pip install -r requirements.txt

    \b
    4️⃣  Run the crew:
       $ python main.py

    \b
    5️⃣  Or use Docker:
       $ docker-compose up --build

    \b
    6️⃣  Run tests:
       $ pytest tests/

    \b
    ⚠️  PREREQUISITES:
    ═══════════════════════════════════════════════════════════════════════════
    • Project must be in 'completed' status
    • Use 'caas status <project-id>' to check completion
    • If status is 'generating', wait or use --watch mode

    \b
    📁 DIRECTORY STRUCTURE:
    ═══════════════════════════════════════════════════════════════════════════
    output_dir/
    ├── src/
    │   ├── agents.py
    │   ├── tasks.py
    │   ├── crew.py
    │   └── tools.py
    ├── tests/
    ├── main.py
    ├── requirements.txt
    ├── Dockerfile
    ├── docker-compose.yml
    └── README.md

    \b
    📚 See also:
       caas status --help      (Check project status first)
       caas generate --help    (Generate new project)
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
        # Check if directory exists
        output_path = Path(output_dir)
        if output_path.exists() and list(output_path.iterdir()) and not force:
            if not click.confirm(f"Directory {output_dir} exists. Overwrite?", default=False):
                echo_error("Download cancelled")
                return

        # Download
        echo_progress(f"Downloading code for project {project_id}...")

        client.download_code(project_id, output_dir)

        echo_success(f"Code downloaded to: {output_dir}")

        # Show next steps
        click.echo()
        click.echo(click.style("Next steps:", bold=True))
        click.echo(f"  1. cd {output_dir}")
        click.echo("  2. Review generated code")
        click.echo("  3. Install dependencies: pip install -r requirements.txt")
        click.echo("  4. Run: python main.py")

    except CAASError as e:
        echo_error(f"Error: {e}")

    except Exception as e:
        echo_error(f"Unexpected error: {e}")
