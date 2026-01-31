"""
Init Command

Initialize CAAS configuration.
"""

import click
from caas_cli.config import get_config
from caas_cli.utils import echo_success, echo_info, prompt_text, prompt_choice


@click.command()
def init():
    """
    \b
    Initialize CAAS CLI configuration

    \b
    🔧 CONFIGURATION SETUP:
    ═══════════════════════════════════════════════════════════════════════════
    This command will guide you through setting up:

    • API URL (for remote API mode - optional)
    • API Key (for authentication - optional)
    • Default domain (FINANCE, HEALTHCARE, etc.)
    • Default deployment target (docker, kubernetes, serverless)
    • Output directory for generated code
    • Validation & auto-fix settings
    • Test generation preferences

    \b
    💡 USAGE:
    ═══════════════════════════════════════════════════════════════════════════
       $ caas init

    \b
    ℹ️  NOTE:
    ═══════════════════════════════════════════════════════════════════════════
    • Configuration is stored in ~/.caas/config.json
    • All settings can be overridden via command-line options
    • CLI works directly with caas_framework (no API server needed by default)

    \b
    📚 Next steps after init:
       $ caas generate "Build a task management system"
    """
    click.echo("""
╔══════════════════════════════════════════════════════════════╗
║              CAAS CLI Configuration Setup                     ║
╚══════════════════════════════════════════════════════════════╝
""")

    config = get_config()

    # API URL
    api_url = prompt_text(
        "API URL",
        default=config.get("api_url", "http://localhost:8000")
    )
    config.set("api_url", api_url)

    # API Key
    api_key = prompt_text(
        "API Key (optional, press Enter to skip)",
        default=""
    )
    if api_key:
        config.set("api_key", api_key)

    # Default domain
    domains = [
        "NONE",
        "TASK_MANAGEMENT",
        "DATA_ANALYSIS",
        "CONVERSATIONAL_AI",
        "FINANCE",
        "HEALTHCARE",
        "E_COMMERCE",
        "EDUCATION",
        "CONTENT_CREATION"
    ]

    default_domain = prompt_choice(
        "Default domain (optional)",
        choices=domains,
        default="NONE"
    )
    if default_domain != "NONE":
        config.set("default_domain", default_domain)

    # Deployment target
    deployment = prompt_choice(
        "Default deployment target",
        choices=["docker", "kubernetes", "serverless"],
        default=config.get("default_deployment", "docker")
    )
    config.set("default_deployment", deployment)

    # Output directory
    output_dir = prompt_text(
        "Output directory for generated code",
        default=config.get("output_dir", "./generated")
    )
    config.set("output_dir", output_dir)

    # Advanced options
    if click.confirm("Configure advanced options?", default=False):
        enable_validation = click.confirm(
            "Enable validation?",
            default=config.get("enable_validation", True)
        )
        config.set("enable_validation", enable_validation)

        enable_auto_fix = click.confirm(
            "Enable auto-fix?",
            default=config.get("enable_auto_fix", True)
        )
        config.set("enable_auto_fix", enable_auto_fix)

        enable_tests = click.confirm(
            "Generate tests?",
            default=config.get("enable_tests", True)
        )
        config.set("enable_tests", enable_tests)

        use_expert_agents = click.confirm(
            "Use expert agent collaboration?",
            default=config.get("use_expert_agents", True)
        )
        config.set("use_expert_agents", use_expert_agents)

    click.echo()
    echo_success("Configuration saved successfully!")
    echo_info(f"Config file: {config.config_path}")

    click.echo("""
Next steps:
  1. Generate your first project:
     $ caas generate "Build a task management system"

  2. Check project status:
     $ caas status <project-id>

  3. Download generated code:
     $ caas download <project-id>

Happy coding! 🚀
""")
